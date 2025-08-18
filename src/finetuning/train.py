import os
# ---- 안정화/메모리/포크 이슈 가드 ----
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True,max_split_size_mb:64"
os.environ["HF_DATASETS_DISABLE_MULTIPROCESSING"] = "1"  # 우선 안정화용

import torch, torch.multiprocessing as mp
mp.set_start_method("spawn", force=True)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

import json, math
from typing import Dict, List, Any
from datasets import load_dataset, load_from_disk
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
)
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# ----------------- 설정 -----------------
MODEL_NAME = "google/gemma-3-4b-it"
DATA_PATH  = "../data/finetuning_data.jsonl"
OUT_DIR    = "../out/gemma3-4b-it-sft-qlora"

MAX_LEN    = 65536          # 학습 시 전체 시퀀스 상한
OUTPUT_MAX = 8192           # 모델 출력 한도 맞춤
TEMPLATE_OVERHEAD = 64
PACKING    = False          # 초장문 위주면 False 권장

PROCESSED_DIR = os.environ.get("PROCESSED_DIR", "../data/gemma3_sft_processed")   # text만
TOKENIZED_DIR = os.environ.get("TOKENIZED_DIR", "../data/gemma3_sft_tokenized")   # input_ids/attention_mask

# 1) Tokenizer & template
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
tokenizer.padding_side = "right"
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# 2) Load Gemma3 with FA2 (bf16, 4bit)
bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",
    quantization_config=bnb,
    device_map="auto",
)
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

# 3) QLoRA config
target_modules = ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]
peft_cfg = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    bias="none", task_type="CAUSAL_LM",
    target_modules=target_modules,
)
model = get_peft_model(model, peft_cfg)

# 학습 안정화 옵션
model.config.use_cache = False
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

# 4) 전처리: input/output → 템플릿 적용 텍스트, 좌측 트리밍
def build_row(ex):
    inp = ex["input"]; out = ex["output"]

    # 길이 체크/트리밍은 기존 로직 유지
    in_ids  = tokenizer(inp, add_special_tokens=False)["input_ids"]
    out_ids = tokenizer(out, add_special_tokens=False)["input_ids"]
    if len(out_ids) > OUTPUT_MAX:
        return {"prompt": None, "completion": None}

    budget = MAX_LEN - len(out_ids) - TEMPLATE_OVERHEAD
    if budget <= 0:
        return {"prompt": None, "completion": None}
    if len(in_ids) > budget:
        inp = tokenizer.decode(in_ids[-budget:], skip_special_tokens=True)

    # ✨ 분리해서 저장 (chat template은 학습 때 자동 적용)
    return {
        "prompt": [{"role": "user", "content": inp}],
        "completion": [{"role": "assistant", "content": out}],
    }


# 4.5) 토큰화 함수: EOS를 우리가 붙이고, text 컬럼 제거
def tok_fn(ex):
    enc = tokenizer(
        ex["text"],
        add_special_tokens=False,          # 템플릿으로 이미 구성됨
        truncation=False,                  # 길이 컷은 build_text에서 처리
        return_attention_mask=True,
    )
    input_ids = enc["input_ids"]
    attn_mask = enc["attention_mask"]

    # EOS 보장(TRL의 "Adding EOS..." 단계 스킵)
    if len(input_ids) == 0 or input_ids[-1] != tokenizer.eos_token_id:
        input_ids = input_ids + [tokenizer.eos_token_id]
        attn_mask = attn_mask + [1]

    return {"input_ids": input_ids, "attention_mask": attn_mask}


# ===== 데이터 준비: 토큰화 완료본 우선 사용 =====
if os.path.isdir(TOKENIZED_DIR):
    print(f"▶ Loading tokenized dataset from {TOKENIZED_DIR}")
    dataset = load_from_disk(TOKENIZED_DIR)
else:
    # 텍스트 전처리본이 없으면 생성
    if not os.path.isdir(PROCESSED_DIR):
        print("▶ Building preprocessed TEXT dataset...")
        raw = load_dataset("json", data_files={"train": DATA_PATH})["train"]
        ds_text = raw.map(build_row, remove_columns=raw.column_names,
                          desc="apply_template_trim")
        ds_text = ds_text.filter(lambda ex: ex["text"] is not None,
                                 desc="filter_too_long")
        # text만 남김
        ds_text = ds_text.remove_columns([c for c in ds_text.column_names if c != "text"])
        ds_text.save_to_disk(PROCESSED_DIR)
        print(f"▶ Saved TEXT to {PROCESSED_DIR}")
    else:
        print(f"▶ Loading preprocessed TEXT dataset from {PROCESSED_DIR}")
        ds_text = load_from_disk(PROCESSED_DIR)

    # 텍스트 → 토큰화 완료본 생성 & 저장
    print("▶ Tokenizing TEXT dataset → TOKENIZED...")
    tok_ds = ds_text.map(tok_fn, desc="tokenize_text")
    tok_ds = tok_ds.remove_columns([c for c in tok_ds.column_names if c not in ["input_ids","attention_mask"]])
    tok_ds.save_to_disk(TOKENIZED_DIR)
    print(f"▶ Saved TOKENIZED to {TOKENIZED_DIR}")
    dataset = tok_ds

# 5) 어시스턴트 구간만 Loss 마스킹
# collator = DataCollatorForCompletionOnlyLM(
#     response_template="<start_of_turn>model",
#     instruction_template="<start_of_turn>user",
#     tokenizer=tokenizer,
# )

lr = 1e-4
training_args = SFTConfig(
    output_dir=OUT_DIR,
    num_train_epochs=2,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=1e-4,
    bf16=True,
    gradient_checkpointing=True,
    packing=False,
    completion_only_loss=True,
    logging_steps=100,                 # I/O 줄이기
    save_strategy="epoch",             # ← 에포크마다 저장
    save_total_limit=2,
    dataloader_num_workers=0,
    dataloader_persistent_workers=False,
    torch_empty_cache_steps=100,
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,            # ← tokenized dataset
    #data_collator=collator,
    processing_class=tokenizer,       # 최신 TRL: tokenizer 인자 대신
)

trainer.train()
trainer.save_model(OUT_DIR)
tokenizer.save_pretrained(OUT_DIR)