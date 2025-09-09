# -*- coding: utf-8 -*-
import json
import pandas as pd
from pathlib import Path
import logging
import ast
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple
from tqdm import tqdm

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
INPUT_PARQUET_PATH = DATA_DIR / '02_processed' / 'parquet' / 'weekly_streak_dataset.parquet'
EXERCISE_CATALOG_PATH = DATA_DIR / '02_processed' / 'processed_query_result.json'
OUTPUT_PATH = DATA_DIR / 'finetuning_data_v2.jsonl'

# --- Logic from calculation_prompt.py (Constants and Prompt Template) ---
L = {
  "M": {"BP": {"B":0.6, "N":1.0, "I":1.3, "A":1.6, "E":2.0}, "SQ": {"B":0.8, "N":1.2, "I":1.6, "A":2.0, "E":2.5}, "DL": {"B":1.0,"N":1.5, "I":2.0, "A":2.5, "E":3.0}, "OHP":{"B":0.4, "N":0.7, "I":0.9, "A":1.1, "E":1.4}},
  "F": {"BP": {"B":0.39,"N":0.65,"I":0.845,"A":1.04,"E":1.3}, "SQ": {"B":0.52,"N":0.78,"I":1.04,"A":1.3,"E":1.625}, "DL": {"B":0.65,"N":0.975,"I":1.3,"A":1.625,"E":1.95}, "OHP":{"B":0.26,"N":0.455,"I":0.585,"A":0.715,"E":0.91}}
}
LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}
INT_BASE_SETS = {"Low":12, "Normal":16, "High":20}
ANCHOR_PERCENTS = [0.55, 0.60, 0.65, 0.70]

PROMPT_TEMPLATE = '''## [Task]
Return a weekly bodybuilding routine as strict JSON only. Output exactly one JSON object and nothing else.

## [User Info]
- Gender: {gender}
- Weight: {weight}kg
- Training Level: {level}
- Weekly Workout Frequency: {freq}
- Workout Duration: {duration} minutes
- Workout Intensity: {intensity}

## [Split]
- Name: {split_name}; Days: {split_days}.

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
'''

# --- Helper Functions ---

@dataclass
class User:
    gender: str; weight: float; level: str; freq: int; duration: int; intensity: str

def parse_duration_bucket(bucket: str) -> int:
    if not isinstance(bucket, str): return 60
    numbers = re.findall(r'\d+', bucket)
    return int(numbers[-1]) if numbers else 60

def round_to_step(x: float, step: int = 5) -> int: return int(round(x / step) * step)

def pick_split(freq: int) -> Tuple[str, List[str]]:
    if freq == 2: return ("Upper-Lower", ["UPPER","LOWER"])
    if freq == 3: return ("Push-Pull-Legs", ["PUSH","PULL","LEGS"])
    if freq == 4: return ("ULUL", ["UPPER","LOWER","UPPER","LOWER"])
    if freq == 5: return ("Bro", ["CHEST","BACK","LEGS","SHOULDERS","ARMS"])
    return ("Full Body", ["FULL_BODY"] * freq)

def set_budget(freq: int, intensity: str) -> int:
    base = INT_BASE_SETS.get(intensity, 16)
    if freq == 2: base += 2
    if freq == 5: base -= 2
    return base

def compute_tm(user: User) -> Dict[str, int]:
    code = LEVEL_CODE.get(user.level)
    if not code or not user.gender: return {"BP": 0, "SQ": 0, "DL": 0, "OHP": 0}
    coeffs = L[user.gender]
    tm = {}
    for lift in ("BP", "SQ", "DL", "OHP"): tm[lift] = round_to_step(0.9 * (user.weight * coeffs[lift][code]), 5)
    return tm

def build_load_table(tm: Dict[str, int]) -> Dict[str, Dict[int, int]]:
    return {lift: {int(p * 100): round_to_step(tm_kg * p, 5) for p in ANCHOR_PERCENTS} for lift, tm_kg in tm.items()}

def accessory_ranges(tm: Dict[str, int]) -> Dict[str, Dict[str, Tuple[int, int]]]:
    out = {}
    for lift, tm_kg in tm.items():
        out[lift] = {
            "compound_45_60": (round_to_step(tm_kg * 0.45, 5), round_to_step(tm_kg * 0.60, 5)),
            "isolation_30_50": (round_to_step(tm_kg * 0.30, 5), round_to_step(tm_kg * 0.50, 5))
        }
    return out

def build_prompt(user: User, catalog: list) -> str:
    split_name, split_days = pick_split(user.freq)
    sets = set_budget(user.freq, user.intensity)
    tm = compute_tm(user)
    loads = build_load_table(tm)
    acc = accessory_ranges(tm)["BP"]
    def row_str(lift): return ", ".join(f'{pct}%:{kg}' for pct, kg in loads[lift].items())
    catalog_str = json.dumps([[item.get(k) for k in ['bName', 'eTextId', 'eName', 'movement_type', 'eInfoType']] for item in catalog], ensure_ascii=False, separators=(',', ':'))
    return PROMPT_TEMPLATE.format(
        gender="male" if user.gender == "M" else "female", weight=int(round(user.weight)), level=user.level, freq=user.freq, duration=user.duration, intensity=user.intensity,
        split_name=split_name, split_days=" / ".join(split_days), sets_budget=sets,
        TM_BP=tm["BP"], TM_SQ=tm["SQ"], TM_DL=tm["DL"], TM_OHP=tm["OHP"],
        BP_loads=row_str("BP"), SQ_loads=row_str("SQ"), DL_loads=row_str("DL"), OHP_loads=row_str("OHP"),
        ACC_COMP_MIN=acc["compound_45_60"][0], ACC_COMP_MAX=acc["compound_45_60"][1],
        ACC_ISO_MIN=acc["isolation_30_50"][0], ACC_ISO_MAX=acc["isolation_30_50"][1],
        catalog_json=catalog_str
    )

def transform_output_schema(weekly_exercises_str: str, id_to_bname_map: dict) -> dict:
    try:
        source_list = ast.literal_eval(weekly_exercises_str)
    except (ValueError, SyntaxError):
        return {"days": []}

    days = []
    current_day_exercises = []
    for item in source_list:
        if item.get("_type") == "session_header":
            if current_day_exercises:
                days.append(current_day_exercises)
            current_day_exercises = []
        else:
            try:
                e_text_id = item.get("eTextId", "")
                b_name = id_to_bname_map.get(e_text_id, "etc")

                sets_str = item.get("sets", "[]")
                sets_list = ast.literal_eval(sets_str)
                
                transformed_sets = []
                for s in sets_list:
                    weight = s.get('weight', 0)
                    if isinstance(weight, float) and weight.is_integer():
                        weight = int(weight)
                    transformed_sets.append([s.get('reps', 0), weight, s.get('time', 0)])
                
                transformed_exercise = [b_name, e_text_id, transformed_sets]
                current_day_exercises.append(transformed_exercise)
            except (ValueError, SyntaxError):
                continue
    
    if current_day_exercises:
        days.append(current_day_exercises)
        
    return {"days": days}

# --- Main Generation Logic ---

def main():
    """Main function to generate the complete finetuning dataset."""
    logging.info("Starting finetuning data generation...")
    try:
        df = pd.read_parquet(INPUT_PARQUET_PATH)
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f: 
            exercise_catalog = json.load(f)
        id_to_bname_map = {item['eTextId']: item['bName'] for item in exercise_catalog}
    except FileNotFoundError as e: 
        logging.error(f"Failed to load data: {e}")
        return

    valid_rows = df[(df['week_level'] != 'Unknown') & (df['gender'].isin(['male', 'female'])) & (df['weekly_exercises'].notna())]
    logging.info(f"Found {len(valid_rows)} valid records to process.")

    processed_count = 0
    error_count = 0
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as out_file:
        for _, row in tqdm(valid_rows.iterrows(), total=valid_rows.shape[0], desc="Generating Finetuning Data"):
            try:
                user_for_prompt = User(
                    gender='M' if row.get('gender') == 'male' else 'F',
                    weight=float(row.get('weight', 70)),
                    level=row.get('week_level'),
                    freq=int(row.get('freq', 3)),
                    duration=parse_duration_bucket(row.get('duration_bucket')),
                    intensity="Normal"
                )
                final_prompt = build_prompt(user_for_prompt, exercise_catalog)
                output_data = transform_output_schema(row.get('weekly_exercises'), id_to_bname_map)

                output_json_string = json.dumps(output_data, ensure_ascii=False, separators=(',', ':'))

                finetuning_record = {"input": final_prompt, "output": output_json_string}
                out_file.write(json.dumps(finetuning_record, ensure_ascii=False) + '\n')
                processed_count += 1
            except Exception as e:
                error_count += 1
                continue

    logging.info("--- Processing Complete ---")
    logging.info(f"Successfully processed: {processed_count} records.")
    logging.info(f"Skipped due to errors: {error_count} records.")
    logging.info(f"Output saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
