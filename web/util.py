# -*- coding: utf-8 -*-
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Constants from calculation_prompt.py ---

LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}
INT_BASE_SETS = {"Low":12, "Normal":16, "High":20}

PROMPT_TEMPLATE_EXERCISES = '''## [Task]
Return a weekly bodybuilding plan as strict JSON only.

## [User Info]
- Gender: {gender}
- Weight: {weight}kg
- Training Level: {level}
- Weekly Workout Frequency: {freq}
- Workout Duration: {duration} minutes
- Workout Intensity: {intensity}

## Split
- Name: {split_name}; Days: {split_days}.

## Content rules
- Schema : {{"days":[[[bodypart,exercise_id],...],...]}}
- Reflect each day's split focus and cover major groups across the week.
- Pick 3–8 exercises per day.
- **Crucially, all exercises within a single day's list MUST be unique. Do not repeat any exercise_id within the same day.**
- Use only ids from the provided catalog; do not invent new exercises.

## Catalog
{catalog_json}

## Output
Return exactly one JSON object only.
'''


# --- Helper Functions ---

@dataclass
class User:
    gender: str
    weight: float
    level: str
    freq: int
    duration: int
    intensity: str

def parse_duration_bucket(bucket: str) -> int:
    if not isinstance(bucket, str): return 60
    numbers = re.findall(r'\d+', bucket)
    return int(numbers[-1]) if numbers else 60

def round_to_step(x: float, step: int = 5) -> int:
    return int(round(x / step) * step)

def pick_split(freq: int) -> Tuple[str, List[str]]:
    if freq == 2: return ("Upper-Lower", ["UPPER","LOWER"])
    if freq == 3: return ("Push-Pull-Legs", ["PUSH","PULL","LEGS"])
    if freq == 4: return ("CBSL", ["CHEST","BACK","SHOULDERS","LEGS"])
    if freq == 5: return ("Bro", ["CHEST","BACK","LEGS","SHOULDERS","ARMS"])
    return ("Full Body", ["FULL_BODY"] * freq)

def set_budget(freq: int, intensity: str) -> int:
    base = INT_BASE_SETS.get(intensity, 16)
    if freq == 2: base += 2
    if freq == 5: base -= 2
    return base

def build_prompt(user: User, catalog: list) -> str:
    split_name, split_days = pick_split(user.freq)
    sets = set_budget(user.freq, user.intensity)
    # 대략 세트 예산을 종목 수로 환산: 한 종목당 평균 3~4세트 가정
    ex_per_day = max(3, min(8, round(sets / 3)))

    processed_catalog = []
    for item in catalog:
        bName = item.get('bName')
        eTextId = item.get('eTextId')
        eName = item.get('eName')
        movement_type = item.get('movement_type')
        body_region = item.get('body_region')

        processed_catalog.append([
            bName.upper() if isinstance(bName, str) else bName,
            eTextId,
            eName,
            movement_type.upper() if isinstance(movement_type, str) else movement_type,
            body_region.upper() if isinstance(body_region, str) else body_region,
        ])

    catalog_str = json.dumps(
        processed_catalog,
        ensure_ascii=False,
        separators=(',', ':')
    )

    return PROMPT_TEMPLATE_EXERCISES.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        freq=user.freq,
        duration=user.duration,
        intensity=user.intensity,
        split_name=split_name,
        split_days=" / ".join(split_days),
        ex_per_day=ex_per_day,
        catalog_json=catalog_str
    )

def format_new_routine(plan_json: dict, exercise_name_map: dict) -> str:
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info("--- DIAGNOSTIC LOG IN format_new_routine ---")
    if exercise_name_map and 'BB_BP' in exercise_name_map:
        # Check a known key ('BB_BP') to see if the value is Korean or English
        logging.info(f"MAP CHECK: BB_BP -> {exercise_name_map.get('BB_BP')}")
    else:
        logging.info("MAP CHECK: exercise_name_map is empty or doesn't contain BB_BP!")
    logging.info("--- END DIAGNOSTIC LOG ---")

    # --- Load Korean names for formatting ---
    korean_map = {}
    try:
        import os
        import json
        # Build absolute path to the data file relative to this util.py file
        # __file__ is the path to the current script (util.py)
        # os.path.dirname(__file__) is the directory of the current script (web/)
        # os.path.dirname(os.path.dirname(__file__)) is the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        korean_catalog_path = os.path.join(project_root, 'data', '02_processed', 'query_result.json')
        with open(korean_catalog_path, 'r', encoding='utf-8') as f:
            korean_catalog = json.load(f)
            for exercise in korean_catalog:
                e_text_id = exercise.get('eTextId')
                if e_text_id:
                    korean_map[e_text_id] = {
                        'bName': exercise.get('bName'),
                        'eName': exercise.get('eName')
                    }
    except Exception:
        # If loading the Korean map fails, fall back to the map that was passed in
        korean_map = exercise_name_map
    # --- End of loading ---

    if not isinstance(plan_json, dict) or "days" not in plan_json:
        return "Invalid plan format."
    out = []
    for i, day in enumerate(plan_json["days"], 1):
        if not isinstance(day, list):
            continue
        lines = [f"## Day{i} (운동개수: {len(day)})"]
        for entry in day:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            bodypart, e_text_id = entry
            exercise_info = korean_map.get(e_text_id, {}) # Use the new korean_map
            e_name = exercise_info.get("eName", e_text_id)
            b_name = exercise_info.get("bName", bodypart)
            lines.append(f"{b_name} - {e_name}")
        if len(lines) > 1:
            out.append("\n".join(lines))
    return "\n\n".join(out)
