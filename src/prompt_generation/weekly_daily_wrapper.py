from __future__ import annotations
from typing import Annotated, List, Optional, Literal
from pydantic import BaseModel, Field, RootModel, model_validator
import json
import os

# ── 기본 제약형 (daily_wrapper.py 참고) ────────────────────────
PosInt   = Annotated[int,   Field(ge=0)]
PosFloat = Annotated[float, Field(ge=0)]

# ── Set(Rep) 단위 (daily_wrapper.py 참고) ─────────────────────
class SetData(BaseModel):
    sReps  : PosInt
    sTime  : PosInt
    sWeight: PosFloat

# ── 운동 1종목 (daily_wrapper.py 참고) ─────────────────────────
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

# ── 하루치 운동 (weekly_wrapper.py의 DailyRoutine 구조 참고) ──
class DailyWorkoutEntry(BaseModel):
    """
    하루치 운동 루틴을 나타냅니다.
    weekly_wrapper.py의 DailyRoutine 구조를 기반으로,
    exercises는 daily_wrapper.py의 상세 ExerciseEntry를 사용합니다.
    """
    dayNum: PosInt = Field(..., description="주간 루틴 내 운동일자 (1~N)")
    exercises: List[ExerciseEntry] = Field(..., description="해당일의 상세 운동 목록")

# ── 주간 래퍼 (weekly_wrapper.py의 WeeklyRoutine 구조 참고) ────────
class WeeklyDailyWorkout(RootModel[List[DailyWorkoutEntry]]):
    """
    전체 주간 상세 운동 루틴을 나타냅니다.
    weekly_wrapper.py의 WeeklyRoutine 구조를 따릅니다.
    """
    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def save_to_json(self, file_path: str):
        """루틴을 JSON 파일로 저장합니다."""
        dumped_data = self.model_dump(mode='json')
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dumped_data, f, ensure_ascii=False, indent=4)
        print(f"성공적으로 루틴을 {file_path} 에 저장했습니다.")