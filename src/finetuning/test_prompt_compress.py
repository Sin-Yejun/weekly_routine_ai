# -*- coding: utf-8 -*-
import json
import os
import random
import pandas as pd
from pathlib import Path
import logging
from tqdm import tqdm

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions (from test_prompt.py) ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent # weekly_routine_ai is the root
DATA_DIR = BASE_DIR / 'data'
USER_HISTORY_DIR = DATA_DIR / '01_raw' / 'user_workout_history'
PARQUET_USER_PATH = DATA_DIR / '02_processed' / 'parquet' / 'user_v2.parquet'
BODYPART_MAP_PATH = DATA_DIR / '03_core_assets' / 'multilingual-pack' / 'bodypart_name_multi.json'
EXERCISE_MAP_PATH = DATA_DIR / '03_core_assets' / 'multilingual-pack' / 'exercise_list_multi.json'
EXERCISE_CATALOG_PATH = DATA_DIR / '02_processed' / 'processed_query_result.json'
OUTPUT_PATH = DATA_DIR / 'finetuning_data_compressed.jsonl' # Changed output path

# --- Helper Functions (from test_prompt.py) ---

def load_shared_data():
    """Loads dataframes and maps needed for processing."""
    logging.info("Loading shared data...")
    try:
        user_df = pd.read_parquet(PARQUET_USER_PATH)
        with open(BODYPART_MAP_PATH, "r", encoding="utf-8") as f:
            bodypart_map = {item["code"]: item["en"] for item in json.load(f)}
        with open(EXERCISE_MAP_PATH, "r", encoding="utf-8") as f:
            exercise_map = {item["code"]: item["en"] for item in json.load(f)}
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f:
            exercise_catalog = json.load(f)
        logging.info("Shared data loaded successfully.")
        return user_df, bodypart_map, exercise_map, exercise_catalog
    except FileNotFoundError as e:
        logging.error(f"Error loading shared data: {e}")
        raise

def get_user_info(user_df, user_id):
    """Gets profile text, frequency, and data dict for a specific user."""
    user_series = user_df[user_df["id"] == user_id]
    if user_series.empty:
        return None, None, None
    
    user_data = user_series.iloc[0]
    frequency = int(user_data.get('frequency', 3))
    
    profile_text = (
        f"- Gender: {user_data.get('gender', 'N/A')}\n"
        f"- Weight: {user_data.get('weight', 'N/A')}kg\n"
        f"- Workout Type: {user_data.get('type', 'N/A')}\n"
        f"- Training Level: {user_data.get('level', 'N/A')}\n"
        f"- Weekly Workout Frequency: {frequency}"
    )
    return profile_text, frequency, user_data.to_dict()

# --- Compact Prompt Functions ---

def _pick_workset(sets, e_info_type):
    if e_info_type == 1:  # time-based
        cand = [s for s in sets if (s or {}).get("time", 0) > 0]
        if not cand: return {"w":0.0, "r":0, "t":0}
        last = cand[-1]
        return {"w":0.0, "r":0, "t":int(last["time"])}
    elif e_info_type == 2:  # reps-only
        cand = [s for s in sets if (s or {}).get("reps", 0) > 0]
        if not cand: return {"w":0.0, "r":0, "t":0}
        best = max(cand[-3:], key=lambda s: (s.get("reps",0),))
        return {"w":0.0, "r":int(best["reps"]), "t":0}
    else:  # e_info_type == 6: weight-based
        cand = [s for s in sets if (s or {}).get("reps",0)>0 and (s or {}).get("weight",0)>=0]
        if not cand: return {"w":0.0, "r":0, "t":0}
        best = max(cand[-4:], key=lambda s: (float(s["weight"]), int(s["reps"])))
        return {"w":float(best["weight"]), "r":int(best["reps"]), "t":0}

def summarize_user_history_compact(workout_days, exercise_catalog):
    """운동별 최근 워킹셋(가중치/반복/시간)만 남기는 초소형 요약"""
    meta = {e["eTextId"]: (e["eInfoType"], e["bTextId"], e["eName"]) for e in exercise_catalog if "eTextId" in e}
    last = {}  # eTextId -> {"w":..,"r":..,"t":..}
    seen_order = []  # 최근 등장 순서 보존(충돌 시 최신으로 갱신)

    for day in workout_days:
        for ex in (day.get("session_data") or []):
            eid = ex.get("eTextId")
            sets = ex.get("sets") or []
            if eid not in meta:  # 카탈로그 밖은 스킵
                continue
            e_info, _, _ = meta[eid]
            work = _pick_workset(sets, e_info)
            if work["w"]==0.0 and work["r"]==0 and work["t"]==0:
                continue
            last[eid] = work
            if eid in seen_order:
                seen_order.remove(eid)
            seen_order.append(eid)

    # 최신 등장 순서대로 압축 배열 구성: [eTextId, w, r, t]
    baselines = [[eid, last[eid]["w"], last[eid]["r"], last[eid]["t"]] for eid in reversed(seen_order)]
    return baselines

def build_compact_catalog(exercise_catalog):
    # [[eTextId, bTextId, eInfoType, eName]]  (eName은 출력 생성에 필요하므로 유지)
    return [[e.get("eTextId"), e.get("bTextId"), e.get("eInfoType"), e.get("eName")] for e in exercise_catalog]

def create_final_prompt_compact(user_data, baselines, compact_catalog, frequency):
    """
    초소형 JSON 프롬프트. 공백 미포함(minified)으로 직렬화.
    - u: 사용자(성별, 체중, 타입, 레벨, 주빈도)
    - hist: 운동별 최근 워킹셋 요약 [[eTextId,w,r,t], ...]
    - cat: 카탈로그 [[eTextId,bTextId,eInfoType,eName], ...]
    - rules: 짧은 제약/스키마/훈련원칙
    """
    prompt_obj = {
        "task":"weekly-routine",
        "u":{"gender":user_data.get("gender"),"wt":float(user_data.get("weight",0)),
             "type":user_data.get("type"),"level":user_data.get("level"),"freq":int(frequency)},
        "hist": baselines,  # 최근 워킹셋 요약
        "cat": compact_catalog,
        "rules":{
            # 출력 형식/검증
            "out":f"JSON array only; len={frequency}",
            "schema":{"session":{"session_data":"array","duration":"minutes:int"},
                      "ex":{"sets":"array","bName":"Leg|Chest|Back|Shoulder|Arm|Lifting|Abs|etc|Cardio",
                            "eName":"from cat","bTextId":"CAT_*","eTextId":"from cat"},
                      "set":{"w":"kg>=0","r":"int>=0","t":"sec>=0"},
                      "eInfo":{"1":"t>0,r=0,w=0","2":"r>0,t=0,w=0","6":"r>0,t=0"}},
            # 레벨/프로그래션/균형
            "level_gate":"Elite+Strength=heavy compounds allowed",
            "progress":"+2.5-5% or +1-2 reps vs last workset; may use 2-for-2",
            "balance":"avoid consecutive heavy leg days; include push/pull balance"
        }
    }
    # 공백 제거해 토큰 최소화
    return json.dumps(prompt_obj, ensure_ascii=False, separators=(',',':'))

def main():
    """Main function to generate and print a single compressed finetuning prompt."""
    user_df, bodypart_map, exercise_map, exercise_catalog = load_shared_data()

    user_files = [f for f in USER_HISTORY_DIR.glob('*.json')]

    for user_file in tqdm(user_files, desc="Finding valid user"):
        try:
            user_id = int(user_file.stem)
        except (ValueError, IndexError):
            continue

        _, frequency, user_data_dict = get_user_info(user_df, user_id)
        if not user_data_dict:
            continue

        with user_file.open('r', encoding='utf-8') as f:
            user_history = json.load(f)
        
        required_records = frequency + 10
        if len(user_history) < required_records:
            continue

        print(f"\n--- Found valid user for testing: {user_id} ---")

        output_sessions = user_history[:frequency]
        history_for_summary = user_history[frequency:required_records]

        output_exercise_ids = {ex.get("eTextId") for s in output_sessions if s.get("session_data") for ex in s["session_data"] if ex.get("eTextId")}
        history_exercise_ids = {ex.get("eTextId") for day in history_for_summary if day.get("session_data") for ex in day["session_data"] if ex.get("eTextId")}
        
        required_exercise_ids = output_exercise_ids.union(history_exercise_ids)
        
        required_catalog = [ex for ex in exercise_catalog if ex.get("eTextId") in required_exercise_ids]
        included_ids = {ex['eTextId'] for ex in required_catalog if 'eTextId' in ex}
        remaining_exercises = [ex for ex in exercise_catalog if ex.get("eTextId") not in included_ids]
        
        num_to_add = min(10, len(remaining_exercises))
        random.seed(user_id)
        random_exercises = random.sample(remaining_exercises, num_to_add)
        
        filtered_exercise_catalog = required_catalog + random_exercises

        baselines = summarize_user_history_compact(history_for_summary, filtered_exercise_catalog)
        compact_catalog = build_compact_catalog(filtered_exercise_catalog)

        final_prompt = create_final_prompt_compact(user_data_dict, baselines, compact_catalog, frequency)

        print("--- GENERATED COMPRESSED PROMPT ---")
        print(final_prompt)
        print("--- END OF COMPRESSED PROMPT ---")
        
        break
    else:
        print("Could not find any user with sufficient data to generate a test prompt.")


if __name__ == "__main__":
    main()