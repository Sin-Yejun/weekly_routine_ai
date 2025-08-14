import os, json, math
from typing import Dict, List, Any
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
)
from trl import SFTTrainer, SFTConfig, DataCollatorForCompletionOnlyLM
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

MODEL_NAME = os.environ.get("MODEL_NAME", "google/gemma-3-4b-it")
DATA_PATH  = os.environ.get("DATA_PATH",  "train.jsonl")     # {"messages":[{role,content},...]}
OUT_DIR    = os.environ.get("OUT_DIR",    "out/gemma3-4b-it-sft-qlora")
MAX_LEN    = int(os.environ.get("MAX_LEN","32768"))          # 32K 권장(47GB MIG 현실선)
PACKING    = os.environ.get("PACKING","false").lower()=="true"  # 긴 샘플이면 False 권장

# 1) Tokenizer & template
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
tokenizer.padding_side = "right"
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# 2) Load Gemma3 with FA2 (bf16)
bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",  # FA2
    quantization_config=bnb,
    device_map="auto",
)
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

# 3) QLoRA config (긴 문맥 안정화 위해 드롭아웃 소량)
target_modules = ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]
peft_cfg = LoraConfig(
    r=int(os.environ.get("LORA_R","16")),
    lora_alpha=int(os.environ.get("LORA_ALPHA","32")),
    lora_dropout=float(os.environ.get("LORA_DROPOUT","0.05")),
    bias="none", task_type="CAUSAL_LM",
    target_modules=target_modules,
)
model = get_peft_model(model, peft_cfg)

# 4) 긴 입력 전처리: supervision(assistant) 주변을 보존하며 좌측을 윈도잉
def build_text(ex: Dict[str, Any]) -> Dict[str, str]:
    msgs: List[Dict[str,str]] = ex["messages"]
    # 템플릿 적용(모델 자체 chat_template 사용)
    full = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)

    # 토크나이즈 후 길면 '끝쪽 MAX_LEN'만 유지(보통 supervision이 말미에 위치)
    ids = tokenizer(full, add_special_tokens=False)["input_ids"]
    if len(ids) > MAX_LEN:
        ids = ids[-MAX_LEN:]
        full = tokenizer.decode(ids, skip_special_tokens=False)

    return {"text": full}

raw = load_dataset("json", data_files={"train": DATA_PATH})["train"]
dataset = raw.map(build_text, remove_columns=raw.column_names)

# 5) Assistant-only loss 마스킹 (Gemma3 IT 템플릿: <start_of_turn>user / <start_of_turn>model)
collator = DataCollatorForCompletionOnlyLM(
    response_template="<start_of_turn>model",
    instruction_template="<start_of_turn>user",
    tokenizer=tokenizer,
)

# 6) SFT 설정: bf16, GC, 패킹(긴 샘플이면 비권장), 코사인 스케줄
lr = float(os.environ.get("LR","1e-4"))  # QLoRA 일반
sft_cfg = SFTConfig(
    output_dir=OUT_DIR,
    num_train_epochs=float(os.environ.get("EPOCHS","2")),
    per_device_train_batch_size=int(os.environ.get("BATCH_SIZE","1")),
    gradient_accumulation_steps=int(os.environ.get("GRAD_ACC","32")),
    learning_rate=lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
    logging_steps=10, save_steps=500,
    bf16=True, gradient_checkpointing=True,
    max_seq_length=MAX_LEN,
    packing=PACKING,
    dataset_text_field="text",
    optim="adamw_torch_fused",
    dataloader_num_workers=4,
)

trainer = SFTTrainer(
    model=model, tokenizer=tokenizer,
    train_dataset=dataset, args=sft_cfg,
    data_collator=collator,
)
trainer.train()
trainer.save_model(OUT_DIR)
tokenizer.save_pretrained(OUT_DIR)

# 7) (선택) vLLM 호환을 위해 LoRA 병합 체크포인트 생성
if os.environ.get("MERGE_LORA","true").lower()=="true":
    from peft import PeftModel
    merged_dir = OUT_DIR + "-merged"
    base = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2", device_map="cpu"
    )
    peft_model = PeftModel.from_pretrained(base, OUT_DIR)
    merged = peft_model.merge_and_unload()
    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    print("Merged to:", merged_dir)
