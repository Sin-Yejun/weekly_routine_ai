# -*- coding: utf-8 -*-
import json
import pandas as pd
from pathlib import Path
import logging
import ast
from dataclasses import dataclass
from typing import List, Dict
from tqdm import tqdm
import random

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = DATA_DIR = BASE_DIR / 'data'
INPUT_PARQUET_PATH = DATA_DIR / '02_processed' / 'hdbscan_clusters.parquet'
EXERCISE_CATALOG_PATH = DATA_DIR / '02_processed' / 'exercise_new.json'
OUTPUT_PATH = DATA_DIR / 'finetuning_data_v6.jsonl'

# --- Prompt Template ---
PROMPT_TEMPLATE = """Task: weekly routine JSON only.
Schema: [[day:int,[[ex_id:str,type:int,[[w,r,t]...] ]]...]]
type1:[0,0,t] type2:[0,r,0] type3:[w,0,t] type6:[w,r,0]
U:{{"g":{gender},"lv":{level},"d":{freq},"s":{split},"dur":{duration}}}
Catalog:{catalog_json}
Out:
"""

# --- Helper Types & Functions ---

@dataclass
class User:
    gender: int   # 0=female, 1=male
    level: int    # 1~4
    freq: int     # workout_days
    split: int    # 0=full-body, 1=split
    duration: int # minutes

def build_prompt(user: User, catalog_json: str) -> str:
    """PROMPT_TEMPLATE에 값 채워 넣기."""
    return PROMPT_TEMPLATE.format(
        gender=user.gender,
        level=user.level,
        freq=user.freq,
        split=user.split,
        duration=user.duration,
        catalog_json=catalog_json
    )

def to_int_safe(x, default: int = 0) -> int:
    try:
        return int(round(float(x)))
    except (TypeError, ValueError):
        return default

def build_catalog_json_from_w(
    w: List,
    name_to_type_map: Dict[str, int],
) -> str:
    """
    w에서 실제 사용된 운동 + 전체 exercise_new.json에서 랜덤 추가 운동 포함하여 Catalog 생성.
    total: used + extra_count (중복 없음)
    """
    used = set()
    for day, ex_list in w:
        for name, etype, sets in ex_list:
            used.add(name)

    # 전체 exercise 목록
    all_ex = list(name_to_type_map.keys())

    # 사용되지 않은 운동만 추출
    unused = [e for e in all_ex if e not in used]

    extra_count = random.randint(30, 60)
    # unused 중에서 랜덤 셈플 extra_count개
    extra = random.sample(unused, min(len(unused), extra_count)) if unused else []

    # 최종 카탈로그: used + extra
    final_catalog = {}
    for name in used:
        final_catalog[name] = int(name_to_type_map[name])

    for name in extra:
        final_catalog[name] = int(name_to_type_map[name])

    return json.dumps(final_catalog, ensure_ascii=False, separators=(',', ':'))

def workout_items_to_w(workout_data_raw) -> List:
    """
    hdbscan_clusters.workout_data 열 -> w 리스트로 변환.
    - 문자열이면 ast.literal_eval
    - 이미 리스트면 그대로 사용
    - 형식: [[day, [[name, type, [[w,r,t]...]], ...]], ...]
    """
    # 타입별 처리
    if isinstance(workout_data_raw, str):
        try:
            data = ast.literal_eval(workout_data_raw)
        except (ValueError, SyntaxError, TypeError):
            return []
    elif isinstance(workout_data_raw, list):
        data = workout_data_raw
    else:
        return []

    if not isinstance(data, list) or not data:
        return []

    w = []

    for day_entry in data:
        # day_entry가 [day, ex_list] 또는 [day, _, ex_list] 같은 형태일 수 있으니
        if not isinstance(day_entry, (list, tuple)) or len(day_entry) < 2:
            continue

        day = day_entry[0]
        ex_list = day_entry[-1]  # 마지막 요소를 운동 리스트로 본다 (중간에 session_id 등 있을 수 있음)

        try:
            day = int(day)
        except (TypeError, ValueError):
            continue

        if not isinstance(ex_list, list):
            continue

        new_ex_list = []
        for ex in ex_list:
            # ex는 최소 [name, type, sets] 형태
            if not isinstance(ex, (list, tuple)) or len(ex) < 3:
                continue
            name = ex[0]
            etype = ex[1]
            sets = ex[2]

            try:
                etype = int(etype)
            except (TypeError, ValueError):
                continue

            if not isinstance(sets, list):
                continue

            new_sets = []
            for s in sets:
                # s = [w,r,t]
                if not (isinstance(s, (list, tuple)) and len(s) == 3):
                    continue
                w_raw, r_raw, t_raw = s

                def to_int(x):
                    if isinstance(x, float) and x.is_integer():
                        return int(x)
                    return int(x) if isinstance(x, (int, float)) else 0

                new_sets.append([to_int(w_raw), to_int(r_raw), to_int(t_raw)])

            if new_sets:
                new_ex_list.append([name, etype, new_sets])

        if new_ex_list:
            w.append([day, new_ex_list])

    return w

# --- Main Generation Logic ---

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting finetuning data generation...")

    # 1) 데이터 로딩
    try:
        df = pd.read_parquet(INPUT_PARQUET_PATH)
        # exercise_new.json 로딩
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f:
            exercise_catalog = json.load(f)
        
        name_to_type_map = {item["name"]: int(item["infotype"]) for item in exercise_catalog}

    except FileNotFoundError as e:
        logging.error(f"Failed to load data: {e}")
        return

    # 2) 유효 row 필터링
    valid_rows = df[
        (df['gender'].isin(['male', 'female'])) &
        (df['workout_data'].notna()) &
        (df['workout_days'] > 0)
    ]
    logging.info(f"Found {len(valid_rows)} valid records to process.")

    processed_count = 0
    error_count = 0

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as out_file:
        for i, (_, row) in enumerate(tqdm(valid_rows.iterrows(),
                                          total=valid_rows.shape[0],
                                          desc="Generating Finetuning Data")):

            try:
                workout_data_raw = row.get('workout_data')

                w = workout_items_to_w(workout_data_raw)
                if not w:
                    error_count += 1
                    continue

                # Catalog: w에서 바로 추출
                catalog_json = build_catalog_json_from_w(w, name_to_type_map)

                # User 정보 구성
                gender_code = 1 if row.get('gender') == 'male' else 0
                level_code  = to_int_safe(row.get('level', 2), 2)
                freq        = to_int_safe(row.get('workout_days', 3), 3)
                split_raw   = row.get('is_split', 1)
                split_flag  = 1 if to_int_safe(split_raw, 1) != 0 else 0
                duration    = to_int_safe(row.get('daily_duration_min', 60), 60)

                user_for_prompt = User(
                    gender=gender_code,
                    level=level_code,
                    freq=freq,
                    split=split_flag,
                    duration=duration
                )
                final_prompt = build_prompt(user_for_prompt, catalog_json)

                # output은 w 리스트 그대로
                output_json_string = json.dumps(w, ensure_ascii=False, separators=(',', ':'))

                finetuning_record = {
                    "input": final_prompt,
                    "output": output_json_string
                }
                out_file.write(json.dumps(finetuning_record, ensure_ascii=False) + '\n')
                processed_count += 1

            except Exception as e:
                error_count += 1
                # 어디서 계속 터지는지 보려면 이 로그가 매우 중요함
                logging.exception(f"Error on row index={i}, user_id={row.get('user_id')}, week_start={row.get('week_start')}")
                continue

    logging.info("--- Processing Complete ---")
    logging.info(f"Successfully processed: {processed_count} records.")
    logging.info(f"Skipped due to errors: {error_count} records.")
    logging.info(f"Output saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
