from __future__ import annotations
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
    sStatus: Literal["waiting"]
    sTime  : PosInt
    sWeight: PosFloat

# ── 운동 1종목 ──────────────────────────────────────────────
class ExerciseEntry(BaseModel):
    # 메타
    eInfoType: Literal[1, 2, 6]
    eName    : str
    eTextId  : str
    tId      : int

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
    
# 과거 운동기록 요약TXT 불러오기 (최근 10회)
txt_list = get_latest_workout_texts()
history_summary_txt = "\n\n".join(txt_list)

# 사용자 기본 정보 불러오기
user_info_txt = get_user_profile_text()

prompt = {
    'content':
    f'''
## [사용자 정보] 
{user_info_txt}

## [과거 운동 기록] 
{history_summary_txt}

## 지시사항
- 너는 위의 정보를 가지고 하루의 루틴을 추천해주는 역할을 해.
- [사용자 정보]와 [과거 운동 기록]을 바탕으로 사용자에게 루틴을 제공해.
- 루틴의 구조는 Json형식이고 아래와 같은 양식을 지켜.    
    '''
}

print(prompt['content'])