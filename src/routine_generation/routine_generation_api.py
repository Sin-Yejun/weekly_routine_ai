import os
import google.generativeai as genai
from dotenv import load_dotenv
from weekly_daily_prompt import create_prompt
from weekly_daily_wrapper import WeeklyDailyWorkout 

load_dotenv()

def generate_routine():
    """
    Gemini API를 호출하여 운동 루틴을 생성하고 검증합니다.
    """
    try:
        # API 키 설정 (환경 변수 'GOOGLE_API_KEY'에서 가져오기)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수를 설정해주세요.")
        genai.configure(api_key=api_key)

        # 모델 초기화 (JSON 출력 모드 활성화)
        model = genai.GenerativeModel(
            'gemini-2.5-flash-lite',
            generation_config={"response_mime_type": "application/json"}
        )

        # 프롬프트 생성
        prompt_content = create_prompt()

        # AI에게 루틴 생성 요청
        print("AI가 운동 루틴을 생성 중입니다...")
        response = model.generate_content(prompt_content)

        # Pydantic 모델로 유효성 검사
        workout_routine = WeeklyDailyWorkout.model_validate_json(response.text)

        # 검증된 루틴을 JSON으로 예쁘게 출력
        print("생성된 운동 루틴:")
        print(workout_routine.model_dump_json(indent=4))

    except Exception as e:
        print(f"오류: AI 루틴을 생성하거나 검증하는 데 실패했습니다.")
        print(f"에러 내용: {e}")
        # 실패 시 원본 응답 출력 (디버깅용)
        if 'response' in locals():
            print("--AI 원본 응답--")
            print(response.text)

if __name__ == "__main__":
    generate_routine()