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
- Choose 4–8 different exercises for every day, adjusting the count naturally based on Workout Duration (shorter sessions = fewer exercises, longer sessions = more exercises).
- All exercises in the same day must be different. Do not repeat any exercise_id inside the same day.

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

def set_budget(freq: int, intensity: str) -> int:
    base = INT_BASE_SETS.get(intensity, 16)
    if freq == 2: base += 2
    if freq == 5: base -= 2
    return base

def build_prompt(user: User, catalog: list, duration_str: str) -> str:
    split_name, split_days = pick_split(user.freq)
    sets = set_budget(user.freq, user.intensity)
    # 대략 세트 예산을 종목 수로 환산: 한 종목당 평균 3~4세트 가정
    ex_per_day = max(3, min(8, round(sets / 3)))

    # Filter catalog based on the user's weekly frequency and split type
    filtered_catalog = []
    split_days_upper = [s.upper() for s in split_days]

    if user.freq == 2:
        # Upper/Lower split: filter by body_region
        filtered_catalog = [
            item for item in catalog
            if item.get('body_region', '').upper() in split_days_upper
        ]
    elif user.freq == 3:
        # Push/Pull/Legs split: filter by movement_type
        filtered_catalog = [
            item for item in catalog
            if item.get('movement_type', '').upper() in split_days_upper
        ]
    elif user.freq in [4, 5]:
        # 4 and 5-day splits: filter by bName (body part)
        filtered_catalog = [
            item for item in catalog
            if item.get('bName', '').upper() in split_days_upper
        ]
    else:
        # Fallback to the full catalog if frequency is not 2-5
        filtered_catalog = catalog

    processed_catalog = []
    for item in filtered_catalog: # Use the filtered catalog
        bName = item.get('bName')
        eTextId = item.get('eTextId')
        eName = item.get('eName')
        movement_type = item.get('movement_type')
        body_region = item.get('body_region')
        
        micro_raw = item.get('MG', "")
        parts = []
        if isinstance(micro_raw, str) and micro_raw.strip():
            parts = [p.strip().upper() for p in micro_raw.split('/')]
        elif isinstance(micro_raw, list):
            parts = [str(p).strip().upper() for p in micro_raw]
        muscle_group = {"micro": parts}

        processed_catalog.append([
            bName.upper() if isinstance(bName, str) else bName,
            eTextId,
            eName,
            movement_type.upper() if isinstance(movement_type, str) else movement_type,
            body_region.upper() if isinstance(body_region, str) else body_region,
            muscle_group,
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
        duration=duration_str,
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
            exercise_info = exercise_name_map.get(e_text_id, {}) # Use the passed map
            e_name = exercise_info.get("eName", e_text_id) # This should now be the Korean name
            b_name = exercise_info.get("bName", bodypart)
            lines.append(f"{b_name} - {e_name}")
        if len(lines) > 1:
            out.append("\n".join(lines))
    return "\n\n".join(out)
