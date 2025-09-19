# -*- coding: utf-8 -*-
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Constants from calculation_prompt.py ---

LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}

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
- HARD RULE — Uniqueness per day: Each day’s exercises must be unique. The same exercise_name MUST NOT appear twice in the same day.
- Output must be a single minified JSON object: no line breaks and no extra spaces (use only commas and colons).
- Schema : {{"days":[[[bodypart,exercise_name],...],...]}}
- Reflect each day's split focus and cover major groups across the week.
- Choose between {min_ex} and {max_ex} different exercises for every day.
- Arrange each day in an effective order (compound → accessories) appropriate to the user’s level.
- FINAL CHECK: For every day, verify all exercise_name values are distinct before returning JSON.

## Output
Return exactly one JSON object only.
'''

## Catalog
# {catalog_json}
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


def build_prompt(user: User, catalog: list, duration_str: str, min_ex: int, max_ex: int) -> str:
    split_name, split_days = pick_split(user.freq)
    
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
        eName = item.get('eName')
        
        micro_raw = item.get('MG', "")
        parts = []
        if isinstance(micro_raw, str) and micro_raw.strip():
            parts = [p.strip().upper() for p in micro_raw.split('/')]
        elif isinstance(micro_raw, list):
            parts = [str(p).strip().upper() for p in micro_raw]
        muscle_group = {"micro": parts}

        processed_catalog.append([
            bName.upper() if isinstance(bName, str) else bName,
            eName,
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
        min_ex=min_ex,
        max_ex=max_ex,
        catalog_json=catalog_str
    )

def format_new_routine(plan_json: dict, name_map: dict, enable_sorting: bool = False) -> str:
    import logging
    logging.basicConfig(level=logging.INFO)
    # logging.info("--- DIAGNOSTIC LOG IN format_new_routine ---")
    # if name_map and 'Back Squat' in name_map:
    #     logging.info(f"MAP CHECK: Back Squat -> {name_map.get('Back Squat')}")
    # else:
    #     logging.info("MAP CHECK: name_map is empty or doesn't contain Back Squat!")
    # logging.info("--- END DIAGNOSTIC LOG ---")

    if not isinstance(plan_json, dict) or "days" not in plan_json:
        return "Invalid plan format."
    out = []
    for i, day in enumerate(plan_json["days"], 1):
        if not isinstance(day, list):
            continue

        if enable_sorting:
            def sort_key(entry):
                exercise_name = entry[1]
                exercise_info = name_map.get(exercise_name, {})
                mg_num = exercise_info.get('MG_num', 0)
                muscle_point_sum = exercise_info.get('musle_point_sum', 0)
                b_name = exercise_info.get('bName', '')
                try:
                    mg_num = int(mg_num)
                except (ValueError, TypeError):
                    mg_num = 0
                try:
                    muscle_point_sum = int(muscle_point_sum)
                except (ValueError, TypeError):
                    muscle_point_sum = 0
                return (mg_num, muscle_point_sum, b_name)
            day.sort(key=sort_key, reverse=True)

        lines = [f"## Day{i} (운동개수: {len(day)})"]
        for entry in day:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            bodypart, exercise_name = entry
            
            # name_map is now name_to_exercise_map, which contains full exercise objects
            exercise_full_info = name_map.get(exercise_name, {}) 
            
            korean_name = exercise_full_info.get("kName", exercise_name) # Get kName from full info
            b_name = exercise_full_info.get("bName", bodypart)
            mg_num = exercise_full_info.get("MG_num", "N/A") # Get MG_num from full info
            musle_point_sum = exercise_full_info.get("musle_point_sum", "N/A") # Get MG_num from full info
            lines.append(f"{b_name:<10} {korean_name:<15} ({mg_num}, {musle_point_sum})") # Add MG_num to the string
        if len(lines) > 1:
            out.append("\n".join(lines))
    return "\n\n".join(out)
