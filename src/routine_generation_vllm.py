# local_vllm_routine.py
import json
from vllm import LLM, SamplingParams
from data_preprocess import create_prompt, DailyWorkout


def generate_routine_vllm() -> None:
    """
    vLLM의 LLM 클래스를 직접 사용해 로컬 Gemma 모델로
    운동 루틴(JSON)을 생성하고 검증한다.
    """
    # ────────────────────────────────────────────────
    # 1. 모델 로드 (처음 실행 시 HuggingFace에서 다운로드)
    #    - 로컬 경로를 쓰고 싶으면 model="path/to/model" 로 변경
    # ────────────────────────────────────────────────
    model_name = "google/gemma3-4b-it"
    llm = LLM(model=model_name)  # dtype 자동 감지

    # ────────────────────────────────────────────────
    # 2. 샘플링 파라미터 설정
    # ────────────────────────────────────────────────
    sampling = SamplingParams(
        temperature=0.7,
        top_p=0.9,
        max_tokens=512,   # JSON이 길어질 수 있으니 충분히 확보
    )

    # ────────────────────────────────────────────────
    # 3. 프롬프트 생성 및 텍스트 생성
    # ────────────────────────────────────────────────
    prompt = create_prompt()
    print("로컬 vLLM이 운동 루틴을 생성 중입니다...")
    outputs = llm.generate([prompt], sampling)

    # vLLM은 리스트 형태로 반환 → 첫 번째 결과 가져오기
    response_text = outputs[0].outputs[0].text.strip()

    # ```json … ``` 마크다운 제거
    if response_text.startswith("```json"):
        response_text = response_text[7:-3].strip()

    # ────────────────────────────────────────────────
    # 4. Pydantic 모델 검증
    # ────────────────────────────────────────────────
    try:
        routine = DailyWorkout.model_validate_json(response_text)
        print("생성된 운동 루틴:")
        print(routine.model_dump_json(indent=4))
    except (json.JSONDecodeError, ValueError) as e:
        print("❗️ JSON 파싱/검증 실패")
        print(e)
        print("\n-- 원본 응답 --")
        print(response_text)


if __name__ == "__main__":
    generate_routine_vllm()