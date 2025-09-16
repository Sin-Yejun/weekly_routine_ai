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
OUTPUT_PATH = DATA_DIR / 'finetuning_data_v4.jsonl'

# --- Logic from calculation_prompt.py (Constants and Prompt Template) ---
PROMPT_TEMPLATE = """
## Task
Return a weekly bodybuilding routine as JSON.

## Schema
{{"days":[[[bodypart,exercise_id,[[reps,weight,time],...]],...],...]}}

## User Info
- Gender: {gender}
- Weight: {weight}kg
- Training Level: {level}
- Weekly Workout Frequency: {freq}
- Workout Duration: {duration} minutes
- Workout Intensity: {intensity}

## Available Exercise Catalog
{catalog_json}

## [Output]
"""

# --- Helper Functions ---

@dataclass
class User:
    gender: str; weight: float; level: str; freq: int; duration: int; intensity: str

def parse_duration_bucket(bucket: str) -> int:
    if not isinstance(bucket, str): return 60
    numbers = re.findall(r'\d+', bucket)
    return int(numbers[-1]) if numbers else 60

def build_prompt(user: User, catalog: list) -> str:
    catalog_structured = []
    for item in catalog:
        micro_raw = item.get("MG", "")
        micro_tags = []
        if isinstance(micro_raw, str) and micro_raw.strip():
            # "/"로 나눠 태그화, 공백 제거 + 대문자 + "_" 붙여서 enum 스타일로
            parts = [p.strip().upper() for p in micro_raw.split('/')]
            for p in parts:
                tag = p.replace(" ", "_")
                # 소근육 태그 앞에 대부위 접두사 붙여도 됨 (예: LEG_QUADS)
                # 여기서는 bName 기준으로 prefix
                prefix = item.get("bName", "").upper()
                micro_tags.append(f"{prefix}_{tag}")
        catalog_structured.append({
            "id": item.get("eTextId"),
            "bp": item.get("bName"),
            "name": item.get("eName"),
            "micro": micro_tags
        })
    catalog_str = json.dumps(catalog_structured, ensure_ascii=False, separators=(',', ':'))
    return PROMPT_TEMPLATE.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        freq=user.freq,
        duration=user.duration,
        intensity=user.intensity,
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
                b_name = id_to_bname_map.get(e_text_id, "Etc")

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