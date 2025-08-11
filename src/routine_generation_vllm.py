# local_vllm_routine.py
import json
from vllm import LLM, SamplingParams
from outlines_vllm.lib import JSONLogitsProcessor # outlines_vllm 라이브러리 사용
from weekly_daily_prompt import create_prompt
from weekly_daily_wrapper import WeeklyDailyWorkout

def generate_routine_vllm() -> None:
    """
    vLLM의 LLM 클래스를 직접 사용해 로컬 Gemma 모델로
    운동 루틴(JSON)을 생성하고 검증한다.
    (outlines-vllm을 사용한 Guided Generation 적용)
    """
    # ────────────────────────────────────────────────
    # 1. 모델 로드
    # ────────────────────────────────────────────────
    model_name = "RedHatAI/gemma-3-4b-it-quantized.w4a16"
    llm = LLM(
        model=model_name,
        trust_remote_code=True,
        dtype="bfloat16",
        max_model_len=8192,
    )

    # ────────────────────────────────────────────────
    # 2. Guided Generation을 위한 설정
    # ────────────────────────────────────────────────
    # Pydantic 모델에서 JSON 스키마 추출
    json_schema = WeeklyDailyWorkout.model_json_schema()
    
    # JSONLogitsProcessor 생성
    logits_processor = JSONLogitsProcessor(schema=json_schema, llm=llm.llm_engine)

    # ────────────────────────────────────────────────
    # 3. 샘플링 파라미터 설정
    # ────────────────────────────────────────────────
    # Guided Generation 사용 시에는 temperature=0.0 권장
    sampling = SamplingParams(
        temperature=0.0,
        max_tokens=4096,  # 충분한 길이 확보
        logits_processors=[logits_processor],
    )

    # ────────────────────────────────────────────────
    # 4. 프롬프트 생성 및 텍스트 생성
    # ────────────────────────────────────────────────
    prompt = create_prompt()
    print("로컬 vLLM이 운동 루틴을 생성 중입니다 (Guided Generation)...")
    outputs = llm.generate([prompt], sampling)

    response_text = outputs[0].outputs[0].text.strip()

    # Guided Generation을 사용하면 JSON 형식이 보장되므로
    # 복잡한 정규식 파싱이 필요 없어집니다.
    
    # ────────────────────────────────────────────────
    # 5. Pydantic 모델 검증
    # ────────────────────────────────────────────────
    try:
        # Guided Generation은 유효한 JSON을 보장하므로 바로 파싱
        routine = WeeklyDailyWorkout.model_validate_json(response_text)
        print("생성된 운동 루틴:")
        print(routine.model_dump_json(indent=4))
    except (json.JSONDecodeError, ValueError) as e:
        print("❗️ JSON 파싱/검증 실패 (Guided Generation 실패)")
        print(e)
        print("\n-- 원본 응답 --")
        print(response_text)


if __name__ == "__main__":
    generate_routine_vllm()
