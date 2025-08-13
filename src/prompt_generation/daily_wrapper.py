from __future__ import annotations
from typing import Annotated, List, Optional, Literal
from pydantic import BaseModel, Field, RootModel, model_validator

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