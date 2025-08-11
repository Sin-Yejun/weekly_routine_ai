import json
import os
from history_summary import get_latest_workout_texts_detail
from user_info import get_user_profile_text, get_user_frequency

def create_prompt():
    """
    AI 주간/일일 루틴 생성을 위한 프롬프트를 생성합니다.
    """
    # 과거 운동기록 요약TXT 불러오기 (최근 10회)
    txt_list = get_latest_workout_texts_detail(10)
    history_summary_txt = "\n\n".join(txt_list)

    # 사용자 기본 정보 불러오기
    user_info_txt = get_user_profile_text()
    frequency = get_user_frequency()

    # 사용 가능한 운동 목록 불러오기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    json_path = os.path.join(project_root, 'data', 'query_result.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        exercise_list = json.load(f)
    exercise_list_text = "\n".join([
        f'- bName: "{item["bName"]}", bTextId: "{item["bTextId"]}", eName: "{item["eName"]}", eTextId: "{item["eTextId"]}"'
        for item in exercise_list[:100]
    ])

    return f"""## [User Info]
{user_info_txt}

## [Recent Workout History]
{history_summary_txt}

## Instructions
- 당신은 위의 [User Info]와 [Recent Workout History]을 바탕으로 개인화된 **일주일치 상세 운동 루틴**을 추천하는 AI 헬스 트레이너입니다.
- 사용자의 운동 목표, 운동종목 수, 주간 운동 횟수({frequency}회), 최근 운동 부위, 빈도 등을 종합적으로 고려하여 가장 적합한 루틴을 생성해야 합니다.
- 루틴은 반드시 아래에 명시된 JSON 구조와 규칙을 따라야 합니다.

### JSON 출력 형식 및 규칙
- 전체 루틴은 각 **운동일(DailyWorkout)**을 요소로 가지는 리스트(배열) 형식이어야 합니다.
- 각 운동일(DailyWorkout)은 다음 규칙을 엄격히 준수해야 합니다.

1.  **`dayNum`**: 운동일의 순서를 나타내는 정수입니다. 사용자의 주간 운동 횟수에 따라 1부터 {frequency}까지 순차적으로 부여됩니다.
2.  **`exercises`**: 해당일에 수행할 운동 종목(ExerciseEntry)의 리스트입니다.

- 각 운동 종목(ExerciseEntry)은 다음 규칙을 엄격히 준수해야 합니다.

1.  **`data` (세트 정보)**: 해당 운동의 각 세트 정보를 담는 리스트입니다.
    - `sReps` : 반복 횟수 (0 이상)
    - `sTime` : 운동 시간 (초 단위, 0 이상)
    - `sWeight` : 중량 (kg 단위, 0 이상)

2.  **`eInfoType` (운동 타입)**: 운동의 종류를 나타내며, 이 값에 따라 다른 필드의 제약 조건이 결정됩니다.
    *   `1`: 시간 기반 유산소 운동 (예: 트레드밀)
        *   `sTime`은 0보다 커야 합니다.
        *   `sReps`와 `sWeight`는 반드시 0이어야 합니다.
    *   `2`: 횟수 기반 무중량 운동 (예: 맨몸 스쿼트, 딥스)
        *   `sReps`는 0보다 커야 합니다.
        *   `sTime`과 `sWeight`는 반드시 0이어야 합니다.
    *   `6`: 횟수 및 중량 기반 근력 운동 (예: 벤치프레스)
        *   `sReps`와 `sWeight`는 0보다 커야 합니다.
        *   `sTime`은 반드시 0이어야 합니다.

3.  **`eTextId` 및 `eName` (운동 ID 및 이름)**: 운동 종목을 식별하는 고유한 값입니다.
    *   **반드시 아래 목록에 존재하는 운동만 사용해야 합니다.**
```
{exercise_list_text}
```

### JSON 출력 예시
```json
[
    {{
        "dayNum": 1,
        "exercises": [
            {{
                "bName": "가슴",
                "bTextId": "CAT_CHEST",
                "data": [
                    {{"sReps": 12, "sTime": 0, "sWeight": 50}},
                    {{"sReps": 10, "sTime": 0, "sWeight": 60}},
                    {{"sReps": 8, "sTime": 0, "sWeight": 70}}
                ],
                "eInfoType": 6,
                "eName": "벤치프레스",
                "eTextId": "BB_BP"
            }},
            {{
                "bName": "가슴",
                "bTextId": "CAT_CHEST",
                "data": [
                    {{"sReps": 12, "sTime": 0, "sWeight": 20}},
                    {{"sReps": 12, "sTime": 0, "sWeight": 20}}
                ],
                "eInfoType": 6,
                "eName": "덤벨 플라이",
                "eTextId": "DB_FLY"
            }},
            {{
                "bName": "가슴",
                "bTextId": "CAT_CHEST",
                "data": [
                    {{"sReps": 15, "sTime": 0, "sWeight": 0}},
                    {{"sReps": 15, "sTime": 0, "sWeight": 0}}
                ],
                "eInfoType": 2,
                "eName": "푸시업",
                "eTextId": "PUSH_UP"
            }},
            {{
                "bName": "유산소",
                "bTextId": "CAT_CARDIO",
                "data": [
                    {{"sReps": 0, "sTime": 1200, "sWeight": 0}}
                ],
                "eInfoType": 1,
                "eName": "트레드밀",
                "eTextId": "TREADMIL"
            }}
        ]
    }},
    {{
        "dayNum": 2,
        "exercises": [
            {{
                "bName": "등",
                "bTextId": "CAT_BACK",
                "data": [
                    {{"sReps": 10, "sTime": 0, "sWeight": 40}},
                    {{"sReps": 10, "sTime": 0, "sWeight": 40}},
                    {{"sReps": 8, "sTime": 0, "sWeight": 45}}
                ],
                "eInfoType": 6,
                "eName": "랫풀다운",
                "eTextId": "LAT_PULL"
            }},
            {{
                "bName": "등",
                "bTextId": "CAT_BACK",
                "data": [
                    {{"sReps": 10, "sTime": 0, "sWeight": 50}},
                    {{"sReps": 10, "sTime": 0, "sWeight": 50}},
                    {{"sReps": 10, "sTime": 0, "sWeight": 50}}
                ],
                "eInfoType": 6,
                "eName": "바벨 로우",
                "eTextId": "BB_ROW"
            }},
            {{
                "bName": "이두",
                "bTextId": "CAT_BICEPS",
                "data": [
                    {{"sReps": 12, "sTime": 0, "sWeight": 10}},
                    {{"sReps": 12, "sTime": 0, "sWeight": 10}}
                ],
                "eInfoType": 6,
                "eName": "덤벨 컬",
                "eTextId": "DB_CURL"
            }}
        ]
    }},
    {{
        "dayNum": 3,
        "exercises": [
            {{
                "bName": "하체",
                "bTextId": "CAT_LEG",
                "data": [
                    {{"sReps": 10, "sTime": 0, "sWeight": 80}},
                    {{"sReps": 8, "sTime": 0, "sWeight": 90}},
                    {{"sReps": 6, "sTime": 0, "sWeight": 100}}
                ],
                "eInfoType": 6,
                "eName": "바벨 백스쿼트",
                "eTextId": "BB_BSQT"
            }},
            {{
                "bName": "하체",
                "bTextId": "CAT_LEG",
                "data": [
                    {{"sReps": 15, "sTime": 0, "sWeight": 120}},
                    {{"sReps": 15, "sTime": 0, "sWeight": 120}},
                    {{"sReps": 15, "sTime": 0, "sWeight": 120}}
                ],
                "eInfoType": 6,
                "eName": "레그 프레스",
                "eTextId": "LEG_PRESS"
            }},
            {{
                "bName": "어깨",
                "bTextId": "CAT_SHOULDER",
                "data": [
                    {{"sReps": 10, "sTime": 0, "sWeight": 40}},
                    {{"sReps": 10, "sTime": 0, "sWeight": 40}}
                ],
                "eInfoType": 6,
                "eName": "오버헤드 프레스",
                "eTextId": "BB_OHP"
            }}
        ]
    }}
]
**이제, 위 모든 규칙을 준수하여 JSON 형식의 운동 루틴을 생성하세요. 다른 설명 없이 JSON만 출력해야 합니다.** 
"""

if __name__ == "__main__":
    prompt = create_prompt()
    print(prompt)
