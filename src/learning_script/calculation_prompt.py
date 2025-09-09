from dataclasses import dataclass
import json
from typing import Dict, List, Tuple

# ---- 1) 설정: 레벨 계수표 (e1RM_target = body_weight * coeff)
L = {
  "M": {
    "BP": {"B":0.6, "N":1.0, "I":1.3, "A":1.6, "E":2.0},
    "SQ": {"B":0.8, "N":1.2, "I":1.6, "A":2.0, "E":2.5},
    "DL": {"B":1.0,"N":1.5, "I":2.0, "A":2.5, "E":3.0},
    "OHP":{"B":0.4, "N":0.7, "I":0.9, "A":1.1, "E":1.4}
  },
  "F": {
    "BP": {"B":0.39,"N":0.65,"I":0.845,"A":1.04,"E":1.3},
    "SQ": {"B":0.52,"N":0.78,"I":1.04,"A":1.3,"E":1.625},
    "DL": {"B":0.65,"N":0.975,"I":1.3,"A":1.625,"E":1.95},
    "OHP":{"B":0.26,"N":0.455,"I":0.585,"A":0.715,"E":0.91}
  }
}

exercise_list = []

with open('data/02_processed/processed_query_result.json', 'r', encoding='utf-8') as f:
    exercise_list = json.load(f)

LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}
INT_BASE_SETS = {"Low":12, "Normal":16, "High":20}
ANCHOR_PERCENTS = [0.55, 0.60, 0.65, 0.70]  # 메인/백오프 범위 커버

def round_to_step(x: float, step: int = 5) -> int:
    return int(round(x / step) * step)

def pick_split(freq: int) -> Tuple[str, List[str]]:
    if freq == 2:  return ("Upper-Lower", ["UPPER","LOWER"])
    if freq == 3:  return ("Push-Pull-Legs", ["PUSH","PULL","LEGS"])
    if freq == 4:  return ("ULUL", ["UPPER","LOWER","UPPER","LOWER"])
    if freq == 5:  return ("Bro", ["CHEST","BACK","LEGS","SHOULDERS","ARMS"])
    raise ValueError("freq must be 2..5")

def set_budget(freq: int, intensity: str) -> int:
    base = INT_BASE_SETS.get(intensity, 16)
    if freq == 2: base += 2
    if freq == 5: base -= 2
    return base  # ±2 허용은 프롬프트 규칙에서 안내

@dataclass
class User:
    gender: str      # "M" or "F"
    weight: float    # kg
    level: str       # "Beginner".."Elite"
    freq: int        # 2..5
    duration: int    # minutes
    intensity: str   # "Low"|"Normal"|"High"

def compute_tm(user: User) -> Dict[str, int]:
    """BP, SQ, DL, OHP의 TM(Training Max ≈ 0.9 * e1RM_target), 5단위 반올림."""
    code = LEVEL_CODE[user.level]
    coeffs = L[user.gender]
    tm = {}
    for lift in ("BP","SQ","DL","OHP"):
        e1rm_target = user.weight * coeffs[lift][code]
        tm[lift] = round_to_step(0.9 * e1rm_target, 5)
    return tm

def build_load_table(tm: Dict[str, int]) -> Dict[str, Dict[int,int]]:
    """각 리프트별 %→kg 테이블(55,60,65,70). 전부 5단위 반올림."""
    table = {}
    for lift, tm_kg in tm.items():
        table[lift] = { int(p*100): round_to_step(tm_kg * p, 5) for p in ANCHOR_PERCENTS }
    return table

def accessory_ranges(tm: Dict[str,int]) -> Dict[str, Dict[str, Tuple[int,int]]]:
    """액세서리/아이솔레이션 권장 범위를 kg로 제공(5단위 반올림)."""
    out = {}
    for lift, tm_kg in tm.items():
        comp_min = round_to_step(tm_kg * 0.45, 5)
        comp_max = round_to_step(tm_kg * 0.60, 5)
        iso_min  = round_to_step(tm_kg * 0.30, 5)
        iso_max  = round_to_step(tm_kg * 0.50, 5)
        out[lift] = {
            "compound_45_60": (comp_min, comp_max),
            "isolation_30_50": (iso_min, iso_max)
        }
    return out

PROMPT_TEMPLATE = """## [Task]
Return a weekly bodybuilding routine as strict JSON only. Output exactly one JSON object and nothing else.

## [User Info]
- Gender: {gender}
- Weight: {weight}kg
- Training Level: {level}
- Weekly Workout Frequency: {freq}
- Workout Duration: {duration} minutes
- Workout Intensity: {intensity}

## [Split]
- Name: Push-Pull-Legs; Days: PUSH / PULL / LEGS.

## [Sets/Reps Budget]
- Target working sets per day: ~{sets_budget} (±2), fit within ~{duration}min.
- Allocate: anchor 3-4 sets; accessories 2-3 sets; avoid per-muscle weekly sets > 12 for Beginners/Novices.
- Reps: anchor 6-10, accessory 8-12, isolation 12-15 (≤20).

## [Loads]
- Training Max (TM): BP={TM_BP}, SQ={TM_SQ}, DL={TM_DL}, OHP={TM_OHP} (kg).
- Rounding: all loads are integers in 5kg steps; round to nearest 5
- Anchor % of TM → weight(kg):
  BP: {BP_loads}
  SQ: {SQ_loads}
  DL: {DL_loads}
  OHP: {OHP_loads}
- Accessories guide from same-day anchor TM:
  compound 45-60% → ~{ACC_COMP_MIN}-{ACC_COMP_MAX}kg, isolation/machine 30-50% → ~{ACC_ISO_MIN}-{ACC_ISO_MAX}kg

## [Schema & Rules]
- JSON only. Minified: no spaces/newlines.
- Schema: {{"days":[[[bodypart,exercise_id,[[reps,weight,time],...]],...],...]}}
- bodypart ∈ {{Chest,Back,Shoulder,Leg,Arm,Abs,Cardio,Lifting,etc}}
- Use only ids from the provided catalog; do not invent new exercises.
- weight integer in 5kg steps; reps≥1; numbers only.

## [Catalog Type Code Rule]
- Each catalog item is [group, exercise_id, exercise_name, movement_type, T] where T∈{{1,2,5,6}}. The sets for that exercise must match T:
  - T=1 (time-only): every set MUST be [0,0,time_sec], with time_sec>0 (e.g., 600–1800). reps=0, weight=0.
  - T=2 (reps-only): every set MUST be [reps>0, 0, 0]. time=0, weight=0.
  - T=5 (weighted/timed): every set MUST be [0, weight≥5(step of 5), time_sec>0]. reps=0.
  - T=6 (weighted): every set MUST be [reps>0, weight≥5(step of 5), 0]. time=0.
- Do not violate the T pattern for any chosen exercise. Reject/replace exercises if the catalog T conflicts with intended usage.

## [Available Exercise Catalog]
{catalog_json}

## [Output]
Return only JSON.
"""

def build_prompt(user: User, catalog: List[List[str]]) -> str:
    split_name, split_days = pick_split(user.freq)
    sets = set_budget(user.freq, user.intensity)
    tm = compute_tm(user)
    loads = build_load_table(tm)
    # 액세서리 범위는 '당일 앵커'를 대표해 BP 기준으로 안내(간결성). 필요시 일자별로 바꿔도 됨.
    acc = accessory_ranges(tm)["BP"]
    # 사람-가독 → "55%:40, 60%:45, ..." 문자열로 직렬화
    def row(lift): return ", ".join(f"{pct}%:{kg}" for pct,kg in loads[lift].items())
    cat_json = str(catalog)
    return PROMPT_TEMPLATE.format(
        gender="male" if user.gender=="M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        freq=user.freq,
        duration=user.duration,
        intensity=user.intensity,
        split_name=split_name,
        split_days=" / ".join(split_days),
        sets_budget=sets,
        TM_BP=tm["BP"], TM_SQ=tm["SQ"], TM_DL=tm["DL"], TM_OHP=tm["OHP"],
        BP_loads=row("BP"), SQ_loads=row("SQ"), DL_loads=row("DL"), OHP_loads=row("OHP"),
        ACC_COMP_MIN=acc["compound_45_60"][0], ACC_COMP_MAX=acc["compound_45_60"][1],
        ACC_ISO_MIN=acc["isolation_30_50"][0], ACC_ISO_MAX=acc["isolation_30_50"][1],
        catalog_json=cat_json
    )
user = User(gender="M", weight=83.0, level="Beginner",
            freq=3, duration=60, intensity="Normal")

catalog = "\n".join(json.dumps([item['bName'], item['eTextId'], item['eName'], item['movement_type'],item['eInfoType']], ensure_ascii=False, separators=(',', ':')).replace('[', '{').replace(']', '}').replace('"', '\"') for item in sorted(exercise_list, key=lambda item: item['bName']))

prompt = build_prompt(user, catalog)
print(prompt) 


# 1단계 맨몸 위주
# 2단계 맨몸메인 + 머신보조
# 3단계 머신메인 + 프리웨이트 보조
# 4단계 프리웨이트 + 머신보조
# 5단계 프리웨이트 위주 

