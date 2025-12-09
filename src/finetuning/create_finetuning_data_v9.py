# -*- coding: utf-8 -*-
import json
import pandas as pd
from pathlib import Path
import logging
import ast
from tqdm import tqdm

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
INPUT_PARQUET_PATH = DATA_DIR / '02_processed' / 'data.parquet'
EXERCISE_RAW_PATH = DATA_DIR / 'exercise_names.json'
OUTPUT_PATH = DATA_DIR / 'finetuning_data_v9.jsonl'

# --- Prompt Template (Lite Version for Training) ---
PROMPT_TEMPLATE = """### Instruction
Create a weekly hypertrophy workout routine based on the User Profile and Exercise Catalog.

### User Profile
- Gender: {gender}
- Level: {level}
- Freq: {freq} days/week
- Split: {split}
- Time: {duration} min

### Exercise Catalog
{catalog_json}

### Response
"""

# --- Helper Functions ---

def parse_workout_data(workout_data_raw):
    """
    workout_data 컬럼을 파싱하여 (요일별 루틴 dict, 사용된 운동 이름 set) 반환
    Output Example:
      routine_dict: {"Day1": ["Squat", "Bench"], "Day2": ...}
      used_names: {"Squat", "Bench"}
    """
    if isinstance(workout_data_raw, str):
        try:
            data = json.loads(workout_data_raw)
        except Exception:
            try:
                data = ast.literal_eval(workout_data_raw)
            except Exception:
                return None, None
    else:
        data = workout_data_raw

    # Dictionary 구조 처리
    if isinstance(data, dict):
        routine_dict = {}
        used_names = set()
        
        for day, exercises in data.items():
            if not isinstance(exercises, list):
                continue
            
            # exercises가 ["Ex1", "Ex2"] 형태라고 가정
            routine_dict[day] = exercises
            for name in exercises:
                used_names.add(name)
                
        return routine_dict, used_names

    # 기존 List 구조 처리 (호환성 유지)
    if isinstance(data, list):
        routine_dict = {}
        used_names = set()
        
        # data 구조: [[day_int, [ [name, type, sets], ... ]], ...]
        for item in data:
            if len(item) < 2:
                continue
            day = item[0]
            exercises = item[-1]  # 마지막 요소가 운동 리스트라고 가정
            
            if not isinstance(exercises, list):
                continue
            
            day_key = f"Day{day}"
            day_routine = []
            
            for ex in exercises:
                # ex: [name, type, sets]
                if len(ex) >= 1:
                    name = ex[0]
                    day_routine.append(name)
                    used_names.add(name)
            
            if day_routine:
                routine_dict[day_key] = day_routine

        return routine_dict, used_names

    return None, None

# --- Main Logic ---

def main():
    logging.basicConfig(level=logging.INFO)

    # 1. Exercise Catalog JSON 그대로 로드 (문자열로)
    with open(EXERCISE_RAW_PATH, "r", encoding="utf-8") as f:
        catalog_obj = json.load(f)  # JSON 객체 로드
        catalog_json_str = json.dumps(catalog_obj, ensure_ascii=False, separators=(',', ':'))
    logging.info(f"Loaded Exercise Catalog from: {EXERCISE_RAW_PATH}")

    # 2. 데이터셋 로드
    df = pd.read_parquet(INPUT_PARQUET_PATH)
    valid_rows = df[df['data'].notna()]
    
    logging.info(f"Processing {len(valid_rows)} rows...")
    
    processed_count = 0
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f_out:
        for _, row in tqdm(valid_rows.iterrows(), total=len(valid_rows)):
            try:
                # 3. 정답 루틴 파싱
                routine_dict, used_names = parse_workout_data(row['data'])
                if not routine_dict or not used_names:
                    continue
                
                # 4. 프롬프트 구성 (카탈로그는 공통으로 그대로 사용)
                gender = row.get('gender', 'male')
                prompt_text = PROMPT_TEMPLATE.format(
                    gender=gender,
                    level=row.get('level', 2),
                    freq=row.get('workout_days', 3),
                    split="Split" if row.get('is_split', 1) else "Full Body",
                    duration=row.get('duration', 60),
                    catalog_json=catalog_json_str
                )
                
                # 5. 정답(Output) 구성 (JSON)
                output_text = json.dumps(
                    routine_dict,
                    ensure_ascii=False,
                    separators=(',', ':')
                )

                # 6. Gemma 3 호환 Chat Format 저장
                record = {
                    "messages": [
                        {"role": "user", "content": prompt_text},
                        {"role": "model", "content": output_text}
                    ]
                }
                
                f_out.write(json.dumps(record, ensure_ascii=False) + '\n')
                processed_count += 1
                
            except Exception as e:
                logging.error(f"Error: {e}") 
                continue

    logging.info(f"Done! Saved {processed_count} samples to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
