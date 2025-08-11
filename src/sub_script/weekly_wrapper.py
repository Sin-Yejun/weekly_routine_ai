from __future__ import annotations
from typing import Annotated, List
from pydantic import BaseModel, Field, RootModel
from user_info import get_user_frequency

# ── 기본 제약형 ──────────────────────────────────────────────
PosInt = Annotated[int, Field(gt=0)]

# ── 주간 루틴 내 운동 1종목 ───────────────────────────────────
class WeeklyExerciseEntry(BaseModel):
    """주간 루틴에 포함된 단일 운동 종목을 나타냅니다."""
    bName  : str = Field(..., description="운동 부위명")
    bTextId: str = Field(..., description="운동 부위 텍스트 ID")
    eName  : str = Field(..., description="운동명")
    eTextId: str = Field(..., description="운동 텍스트 ID")
    numSets: PosInt = Field(..., description="해당 운동의 세트 수")

# ── 하루치 운동 루틴 ──────────────────────────────────────────
class DailyRoutine(BaseModel):
    """하루치 운동 루틴을 나타냅니다."""
    dayNum   : Annotated[int, Field(gt=0, le=get_user_frequency())] = Field(..., description="주간 루틴 내 운동일자 (1~N)")
    exercises: List[WeeklyExerciseEntry] = Field(..., description="해당일의 운동 목록")

# ── 주간 루틴 래퍼 ───────────────────────────────────────────
class WeeklyRoutine(RootModel[List[DailyRoutine]]):
    """전체 주간 운동 루틴을 나타냅니다."""
    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]
