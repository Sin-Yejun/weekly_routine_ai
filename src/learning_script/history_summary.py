# -*- coding: utf-8 -*-
"""
이 스크립트는 Parquet 파일에서 최근 운동 기록을 조회하여
가독성 좋은 텍스트 형식으로 요약합니다.

주요 기능:
- Parquet에서 최근 운동 데이터를 가져옵니다.
- 데이터를 가공하여 운동별, 세트별로 정리합니다.
- 각 운동 세션을 텍스트로 요약하여 리스트로 반환합니다.
"""
from typing import List, Dict, Any
import polars as pl
import pandas as pd
from pathlib import Path
import json

# Load mapping files for bName and eName translation
BODYPART_MAP_PATH = Path("data/multilingual-pack/bodypart_name_multi.json")
EXERCISE_MAP_PATH = Path("data/multilingual-pack/exercise_list_multi.json")

with BODYPART_MAP_PATH.open("r", encoding="utf-8") as f:
    bodypart_data = json.load(f)
bodypart_map = {item["code"]: item["en"] for item in bodypart_data}

with EXERCISE_MAP_PATH.open("r", encoding="utf-8") as f:
    exercise_data = json.load(f)
exercise_map = {item["code"]: item["en"] for item in exercise_data}

def parse_sets_field(x: Any) -> Any:
    """
    'sets' 필드가 문자열(JSON)로 들어있을 경우 리스트로 변환합니다.
    """
    if isinstance(x, str):
        x = x.strip()
        try:
            return json.loads(x)
        except Exception:
            return x
    return x

def _load_workout_data_from_parquet(cnt: int) -> list[dict]:
    """Helper function to load and parse workout data from Parquet."""
    PARQUET_PATH = Path("data/parquet/workout_session.parquet")
    
    lf = pl.scan_parquet(str(PARQUET_PATH))
    df_polar = lf.sort("date", descending=True).limit(cnt).collect()
    df = df_polar.to_pandas()

    workout_days = []
    for _, row in df.iterrows():
        try:
            session_data_str = row.get('session_data', '[]')
            session_data = json.loads(session_data_str) if isinstance(session_data_str, str) else session_data_str
            if not isinstance(session_data, list):
                session_data = []
            
            for exercise in session_data:
                if 'sets' in exercise:
                    exercise['sets'] = parse_sets_field(exercise['sets'])
                
                # Translate names to English
                if "bTextId" in exercise and exercise["bTextId"] in bodypart_map:
                    exercise["bName"] = bodypart_map[exercise["bTextId"]]
                if "eTextId" in exercise:
                    if exercise["eTextId"] in exercise_map:
                        exercise["eName"] = exercise_map[exercise["eTextId"]]
                    elif exercise["eTextId"].startswith("CUSTOM"):
                        # CUSTOM으로 시작하는 경우 사용자 정의 운동명 생성
                        custom_id = exercise["eTextId"].replace("CUSTOM_", "").replace("CUSTOM", "")
                        if custom_id:
                            exercise["eName"] = f"CUSTOM_WORKOUT_{custom_id}"
                        else:
                            exercise["eName"] = "CUSTOM_WORKOUT"

        except (json.JSONDecodeError, TypeError):
            session_data = []
            
        day = {
            "dId": row.get('id'),
            "date": row.get('date'),
            "duration": row.get('duration'),
            "exercises": session_data
        }
        workout_days.append(day)
    return workout_days

def get_latest_workout_texts(cnt: int) -> list[str]:
    """
    Parquet 파일에서 최근 운동 기록을 가져와 기본 정보만 포함하여 텍스트로 요약하여 반환합니다.
    """
    workout_days = _load_workout_data_from_parquet(cnt)
    
    texts = []
    for idx, day in enumerate(workout_days, 1):
        texts.append(text_summary(day, idx))
        
    return texts

def get_latest_workout_texts_detail(cnt: int) -> list[str]:
    """
    Parquet 파일에서 최근 운동 기록을 가져와 상세 정보를 포함하여 텍스트로 요약하여 반환합니다.
    """
    workout_days = _load_workout_data_from_parquet(cnt)

    texts = []
    for idx, day in enumerate(workout_days, 1):
        texts.append(_text_summary_detail(day, idx))
        
    return texts

def text_summary(day: Dict, order: int) -> str:
    """
    하루치 운동 데이터를 받아 기본 텍스트 요약을 생성합니다. (세트 상세 정보 제외)
    """
    duration = day.get('duration')
    duration_str = f" - Duration: {duration}min" if duration else ""
    header = f"Recent Workout #{order}{duration_str}"
    lines  = [header]
    if "exercises" in day and day["exercises"]:
        for ex in day["exercises"]:
            b_name = ex.get('bName', 'N/A')
            num_sets = len(ex.get('sets', []))
            line = (
                f"{b_name:<12}- {ex.get('eName', 'N/A')} ({ex.get('eTextId', 'N/A')}) "
                f"{num_sets}sets"
            )
            lines.append(line)
    return "\n".join(lines)

def _text_summary_detail(day: Dict, order: int) -> str:
    """
    하루치 운동 데이터를 받아 세부 세트 정보를 포함한 상세 텍스트 요약을 생성합니다.
    """
    duration = day.get('duration')
    duration_str = f" - Duration: {duration}min" if duration else ""
    header = f"Recent Workout #{order}{duration_str}"
    lines  = [header]
    if "exercises" in day and day["exercises"]:
        for ex in day["exercises"]:
            b_name = ex.get('bName', 'N/A')
            num_sets = len(ex.get('sets', []))
            sets_data = ex.get('sets', [])
            
            compressed_sets_str = compress_sets(sets_data)

            line = (
                f"{b_name:<12}- {ex.get('eName', 'N/A')} ({ex.get('eTextId', 'N/A')}) "
                f"{num_sets}sets: "
                f"{compressed_sets_str}"
            )
            lines.append(line)
    return "\n".join(lines)

def compress_sets(sets: List[Dict]) -> str:
    """
    세트 리스트를 '7x20 / 5x60 / 1800s'과 같은 압축된 문자열로 변환합니다.
    """
    out = []
    if not sets:
        return ""
        
    for s in sets:
        if not isinstance(s, dict):
            continue
        reps   = s.get("reps")
        weight = s.get("weight")
        time = s.get("time")

        if time and time > 0:
            out.append(f"{time}s")
            continue

        w_disp = int(weight) if weight is not None and isinstance(weight, (int, float)) and float(weight).is_integer() else weight
        
        base = f"{reps}"
        if w_disp is not None and w_disp != 0:
            base += f"x{w_disp}"
        
        out.append(base)

    return " / ".join(out)

# ───────────────────────────────────────────────────────────────
# 스크립트 직접 실행 시 결과 출력
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # print("--- Simple Summary ---")
    # workout_texts = get_latest_workout_texts(5)
    # for text in workout_texts:
    #     print(text)
    #     print()

    print("\n--- Detailed Summary ---")
    workout_texts_detail = get_latest_workout_texts_detail(10)
    for text in workout_texts_detail:
        print(text)
        print()