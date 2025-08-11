import json
import os
from history_summary import get_latest_workout_texts
from user_info import get_user_profile_text, get_user_frequency

def create_prompt():
    """
    AI 루틴 생성을 위한 프롬프트를 생성합니다.
    """
    # 과거 운동기록 요약TXT 불러오기 (최근 10회)
    txt_list = get_latest_workout_texts(10)
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

    return f"""## [사용자 정보]
{user_info_txt}

## [과거 운동 기록]
{history_summary_txt}

## 지시사항
- 당신은 위의 [사용자 정보]와 [과거 운동 기록]을 바탕으로 개인화된 일주일 운동 종목을 추천하는 AI 헬스 트레이너입니다.
- 사용자의 운동 목표, 주간 운동 횟수, 최근 운동 종목, 세트수 등을 종합적으로 고려하여 가장 적합한 루틴을 생성해야 합니다.
- 루틴은 반드시 아래에 명시된 JSON 구조와 규칙을 따라야 합니다.

### JSON 출력 형식 및 규칙
- 전체 루틴은 각 운동 종목(ExerciseEntry)을 요소로 가지는 리스트(배열) 형식이어야 합니다.
- 각 운동 종목(ExerciseEntry)은 다음 규칙을 엄격히 준수해야 합니다.

1. dayNum: 운동 종목이 속하는 날짜를 나타내는 정수입니다. 사용자의 주간 운동 횟수에 따라 1~{frequency}까지 순차적으로 부여됩니다.
2. main 및 sub 리스트의 각 운동 항목(딕셔너리) 안에 numSets가 위치해야 하며, 이는 해당 운동 종목의 세트 수를 나타내는 정수입니다.
2. numSets: 해당 운동 종목의 세트 수를 나타내는 정수입니다.
3. **`bTextId` 및 `bName` (부위 ID 및 이름)**: 각 루틴(ExerciseEntry)의 최상위에 위치하며, 해당 운동일의 주요 부위 정보를 나타냅니다.
4. **`eTextId` 및 `eName` (운동 ID 및 이름)**: main 및 sub 리스트 내 각 운동 항목에만 사용되며, 운동 종목을 식별하는 고유한 값입니다.
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
                "eName": "벤치프레스",
                "eTextId": "BB_BP",
                "numSets": 5
            }},
            {{
                "bName": "가슴",
                "bTextId": "CAT_CHEST",
                "eName": "덤벨 벤치프레스",
                "eTextId": "DB_BP",
                "numSets": 4
            }},
            {{
                "bName": "가슴",
                "bTextId": "CAT_CHEST",
                "eName": "인클라인 덤벨 벤치프레스",
                "eTextId": "DB_INC_BP",
                "numSets": 4
            }},
            {{
                "bName": "가슴",
                "bTextId": "CAT_CHEST",
                "eName": "케이블 플라이",
                "eTextId": "CB_FLY",
                "numSets": 3
            }},
            {{
                "bName": "유산소",
                "bTextId": "CAT_CARDIO",
                "eName": "트레드밀",
                "eTextId": "TREADMIL",
                "numSets": 1
            }}
        ]
    }},
    {{
        "dayNum": 2,
        "exercises": [
            {{
                "bName": "하체",
                "bTextId": "CAT_LEG",
                "eName": "바벨 백스쿼트",
                "eTextId": "BB_BSQT",
                "numSets": 4
            }},
            {{
                "bName": "하체",
                "bTextId": "CAT_LEG",
                "eName": "레그 프레스",
                "eTextId": "LEG_PRESS",
                "numSets": 4
            }},
            {{
                "bName": "하체",
                "bTextId": "CAT_LEG",
                "eName": "레그 익스텐션",
                "eTextId": "LGE_EXT",
                "numSets": 4
            }},
            {{
                "bName": "하체",
                "bTextId": "CAT_LEG",
                "eName": "레그 컬",
                "eTextId": "LEG_CURL",
                "numSets": 3
            }}
        ]
    }}
]
"""


if __name__ == "__main__":
    prompt = create_prompt()
    print(prompt)