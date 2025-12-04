# -*- coding: utf-8 -*-
import json
import pandas as pd
from pathlib import Path
import logging
import ast
import random
import re
from tqdm import tqdm

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
# 원본 데이터(exercise_micro.json)를 사용해야 메타데이터(부위, 점수 등)를 활용할 수 있습니다.
INPUT_PARQUET_PATH = DATA_DIR / '02_processed' / 'data.parquet'
EXERCISE_RAW_PATH = DATA_DIR / '02_processed' / 'exercise_micro.json' 
OUTPUT_PATH = DATA_DIR / 'finetuning_data_v9.jsonl'

# --- Prompt Template (Lite Version for Training) ---
# 학습용은 최대한 간결하게 핵심만 전달합니다.
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
def load_exercise_db(path):
    """운동 DB를 로드하고 검색하기 쉽게 딕셔너리로 변환합니다."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # name을 key로 하여 전체 정보를 빠르게 찾도록 매핑
    db_map = {}
    for item in data:
        # ename이 없으면 kname 사용, 둘 다 없으면 skip
        name = item.get('ename') or item.get('kname')
        if name:
            db_map[name] = item
    
    # 전체 리스트도 반환 (랜덤 샘플링용)
    return data, db_map

def format_exercise_string(item):
    """
    운동 정보를 LLM 학습용 압축 문자열로 변환
    Ex: "Back Squat"
    """
    # Catlog에 그냥 운동이름만 들어가게 수정
    return item.get('ename', item.get('kname', 'Unknown'))

def build_dynamic_catalog(used_exercises_names, full_db_list, full_db_map):
    """
    학습 효율을 위해 [정답 + 헷갈리는 오답 + 랜덤 오답]으로 구성된 작은 카탈로그 생성
    """
    # 1. 정답 리스트 (Positive)
    catalog_items = []
    used_body_parts = set()
    
    for name in used_exercises_names:
        if name in full_db_map:
            item = full_db_map[name]
            catalog_items.append(item)
            used_body_parts.add(item.get('ebody', 'Other'))

    # 2. 오답 샘플링 (Negative Sampling)
    # 2-1. Hard Negative: 정답과 같은 부위지만 선택되지 않은 운동 (헷갈리게 만들기)
    hard_negatives = [
        ex for ex in full_db_list 
        if ex.get('ebody') in used_body_parts 
        and (ex.get('ename') not in used_exercises_names)
    ]
    
    # 2-2. Random Negative: 전혀 다른 부위 운동
    random_negatives = [
        ex for ex in full_db_list 
        if ex.get('ebody') not in used_body_parts
    ]
    
    # 개수 조절 (총 50~80개 사이 유지)
    num_hard = min(len(hard_negatives), 25)
    num_rand = min(len(random_negatives), 15)
    
    catalog_items.extend(random.sample(hard_negatives, num_hard))
    catalog_items.extend(random.sample(random_negatives, num_rand))
    
    # 순서 섞기 (Bias 방지)
    random.shuffle(catalog_items)
    
    # 3. 부위별 Grouping 및 문자열 변환
    grouped_catalog = {}
    for item in catalog_items:
        ebody = item.get('ebody', 'Other')
        formatted_str = format_exercise_string(item)
        
        if ebody not in grouped_catalog:
            grouped_catalog[ebody] = []
        grouped_catalog[ebody].append(formatted_str)
        
    # JSON 문자열로 압축 (공백 제거)
    return json.dumps(grouped_catalog, ensure_ascii=False, separators=(',', ':'))

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
        except:
            try:
                data = ast.literal_eval(workout_data_raw)
            except:
                return None, None
    else:
        data = workout_data_raw

    # Dictionary 구조 처리
    if isinstance(data, dict):
        routine_dict = {}
        used_names = set()
        
        for day, exercises in data.items():
            if not isinstance(exercises, list): continue
            
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
            if len(item) < 2: continue
            day = item[0]
            exercises = item[-1] # 마지막 요소가 운동 리스트라고 가정
            
            if not isinstance(exercises, list): continue
            
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
    
    # 1. DB 로드
    full_db_list, full_db_map = load_exercise_db(EXERCISE_RAW_PATH)
    logging.info(f"Loaded Exercise DB: {len(full_db_list)} items")

    # 2. 데이터셋 로드
    df = pd.read_parquet(INPUT_PARQUET_PATH)
    valid_rows = df[df['data'].notna()]
    
    logging.info(f"Processing {len(valid_rows)} rows...")
    
    processed_count = 0
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for _, row in tqdm(valid_rows.iterrows(), total=len(valid_rows)):
            try:
                # 3. 정답 루틴 파싱
                routine_dict, used_names = parse_workout_data(row['data'])
                if not routine_dict or not used_names:
                    continue
                
                # 4. Dynamic Catalog 생성
                catalog_json_str = build_dynamic_catalog(used_names, full_db_list, full_db_map)
                
                # 5. 프롬프트 구성
                gender = row.get('gender', 'male')
                prompt_text = PROMPT_TEMPLATE.format(
                    gender=gender,
                    level=row.get('level', 2),
                    freq=row.get('workout_days', 3),
                    split="Split" if row.get('is_split', 1) else "Full Body",
                    duration=row.get('duration', 60),
                    catalog_json=catalog_json_str
                )
                
                # 6. 정답(Output) 구성
                # 모델이 뱉어야 할 이상적인 답변 포맷 (JSON)
                output_text = json.dumps(routine_dict, ensure_ascii=False, separators=(',', ':'))

                # 7. Gemma 3 호환 Chat Format 저장
                record = {
                    "messages": [
                        {"role": "user", "content": prompt_text},
                        {"role": "model", "content": output_text} # Gemma는 'model' role 권장
                    ]
                }
                
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                processed_count += 1
                
            except Exception as e:
                logging.error(f"Error: {e}") 
                continue

    logging.info(f"Done! Saved {processed_count} samples to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()