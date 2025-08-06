from __future__ import annotations
import json
import os
from typing import Annotated, List, Optional, Literal
from pydantic import BaseModel, Field, RootModel, model_validator
from history_summary import get_latest_workout_texts
from user_info import get_user_profile_text
# ── 기본 제약형 ──────────────────────────────────────────────
PosInt   = Annotated[int,   Field(ge=0)]
PosFloat = Annotated[float, Field(ge=0)]

# ── Set(Rep) 단위 ───────────────────────────────────────────
class SetData(BaseModel):
    sKind  : Optional[PosInt] = Field(None, description="1:웜업, 2:드롭, 3:실패")
    sReps  : PosInt
    sTime  : PosInt
    sWeight: PosFloat

# ── 운동 1종목 ──────────────────────────────────────────────
class ExerciseEntry(BaseModel):
    # 메타
    eInfoType: Literal[1, 2, 6]
    eName    : str
    eTextId  : str

    # 부위 & 세트
    bName   : str
    bTextId : str
    data    : List[SetData]

    # ── 조건별 검증 ──────────────────────────────────────
    @model_validator(mode="after")
    def check_sets_by_info_type(self):
        for idx, s in enumerate(self.data, start=1):
            if self.eInfoType == 1:        # 유산소/시간 기반
                assert s.sTime > 0,  f"set#{idx}: eInfoType=1 이면 sTime > 0"
                assert s.sReps == 0, f"set#{idx}: eInfoType=1 이면 sReps=0"
                assert s.sWeight == 0, f"set#{idx}: eInfoType=1 이면 sWeight=0"
            elif self.eInfoType == 2:      # 횟수 기반 체중·무게 0
                assert s.sReps > 0,  f"set#{idx}: eInfoType=2 이면 sReps > 0"
                assert s.sTime == 0, f"set#{idx}: eInfoType=2 이면 sTime=0"
                assert s.sWeight == 0, f"set#{idx}: eInfoType=2 이면 sWeight=0"
            elif self.eInfoType == 6:      # 중량 기반
                assert s.sReps > 0,  f"set#{idx}: eInfoType=6 이면 sReps > 0"
                assert s.sWeight > 0, f"set#{idx}: eInfoType=6 이면 sWeight > 0"
                assert s.sTime == 0, f"set#{idx}: eInfoType=6 이면 sTime=0"
        return self

# ── 하루치 래퍼 ──────────────────────────────────────────────
class DailyWorkout(RootModel[List[ExerciseEntry]]):
    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

def create_prompt():
    """
    AI 루틴 생성을 위한 프롬프트를 생성합니다.
    """
    # 과거 운동기록 요약TXT 불러오기 (최근 10회)
    txt_list = get_latest_workout_texts()
    history_summary_txt = "\n\n".join(txt_list)

    # 사용자 기본 정보 불러오기
    user_info_txt = get_user_profile_text()

    # 사용 가능한 운동 목록 불러오기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    json_path = os.path.join(project_root, 'data', 'query_result.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        exercise_list = json.load(f)
    exercise_list_text = "\n".join([
        f'- bName: "{item["bName"]}", bTextId: "{item["bTextId"]}", eName: "{item["eName"]}", eTextId: "{item["eTextId"]}"'
        for item in exercise_list[:20]
    ])

    return f"""## [사용자 정보]
{user_info_txt}

## [과거 운동 기록]
{history_summary_txt}

## 지시사항
- 당신은 위의 [사용자 정보]와 [과거 운동 기록]을 바탕으로 개인화된 하루치 운동 루틴을 추천하는 AI 헬스 트레이너입니다.
- 사용자의 운동 목표, 최근 운동 부위, 빈도 등을 종합적으로 고려하여 가장 적합한 루틴을 생성해야 합니다.
- 루틴은 반드시 아래에 명시된 JSON 구조와 규칙을 따라야 합니다.

### JSON 출력 형식 및 규칙
- 전체 루틴은 각 운동 종목(ExerciseEntry)을 요소로 가지는 리스트(배열) 형식이어야 합니다.
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

2.  **`eTextId` 및 `eName` (운동 ID 및 이름)**: 운동 종목을 식별하는 고유한 값입니다.
    *   **반드시 아래 목록에 존재하는 운동만 사용해야 합니다.**
```
{exercise_list_text}
```

### JSON 출력 예시
```json
[
    {{
        "bName": "가슴",
        "bTextId": "CAT_CHEST",
        "data": [
            {{
                "sReps": 10,
                "sRpe": null,
                "sTime": 0,
                "sWeight": 60
            }},
            {{
                "sReps": 10,
                "sRpe": null,
                "sTime": 0,
                "sWeight": 60
            }}
        ],
        "eInfoType": 6,
        "eName": "벤치프레스",
        "eTextId": "BB_BP"
    }},
    {{
        "bName": "가슴",
        "bTextId": "CAT_CHEST",
        "data": [
            {{
                "sReps": 20,
                "sRpe": null,
                "sTime": 0,
                "sWeight": 0
            }}
        ],
        "eInfoType": 2,
        "eName": "딥스",
        "eTextId": "DIPS"
    }},
    {{
        "bName": "유산소",
        "bTextId": "CAT_CARDIO",
        "data": [
            {{
                "sReps": 0,
                "sRpe": null,
                "sTime": 2400,
                "sWeight": 0
            }}
        ],
        "eInfoType": 1,
        "eName": "트레드밀",
        "eTextId": "TREADMIL"
    }}
]
"""

if __name__ == "__main__":
    prompt = create_prompt()
    print(prompt)
