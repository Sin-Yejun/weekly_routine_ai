# -*- coding: utf-8 -*-
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- V3 Prompt Template ---
PROMPT_TEMPLATE = """## Task
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
    gender: str
    weight: float
    level: str
    freq: int
    duration: int
    intensity: str

def parse_duration_bucket(bucket: str) -> int:
    """Helper to parse duration from a string bucket."""
    if not isinstance(bucket, str): return 60
    numbers = re.findall(r'\d+', bucket)
    return int(numbers[-1]) if numbers else 60

def build_prompt(user: User, catalog: list) -> str:
    """Builds the simplified V3 prompt."""
    # V3 uses a simplified catalog format in the prompt.
    catalog_str = json.dumps([[item.get(k) for k in ['bName', 'eTextId', 'eName']] for item in catalog], ensure_ascii=False, separators=(',', ':'))
    
    return PROMPT_TEMPLATE.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        freq=user.freq,
        duration=user.duration,
        intensity=user.intensity,
        catalog_json=catalog_str
    )

def format_new_routine(routine_json: dict, exercise_name_map: dict) -> str:
    """Formats the new routine JSON into a human-readable summary."""
    if not isinstance(routine_json, dict) or "days" not in routine_json:
        return "Invalid routine format."

    days_data = routine_json.get("days", [])
    if not isinstance(days_data, list):
        return "Invalid 'days' format in routine."

    texts = []
    for idx, day_exercises in enumerate(days_data, 1):
        header = f"[Workout Day #{idx}]"
        lines = [header]
        
        if not isinstance(day_exercises, list):
            continue

        for exercise_details in day_exercises:
            if not isinstance(exercise_details, list) or len(exercise_details) != 3:
                continue
            
            bodypart, e_text_id, sets = exercise_details
            
            exercise_info = exercise_name_map.get(e_text_id, {})
            e_name = exercise_info.get('eName', e_text_id) # Default to e_text_id
            
            display_name = f"[{bodypart}] {e_name}"

            if not isinstance(sets, list):
                continue

            num_sets = len(sets)
            sets_str_parts = []
            for s in sets:
                if not isinstance(s, list) or len(s) != 3:
                    continue
                reps, weight, time = s
                if time > 0:
                    if weight > 0: # Weighted timed exercise (T=5)
                        sets_str_parts.append(f"{weight}kg for {time}s")
                    else: # Timed exercise (T=1)
                        sets_str_parts.append(f"{time}s")
                elif reps > 0:
                    if weight > 0: # Weighted reps (T=6)
                        sets_str_parts.append(f"{weight}kg x {reps}")
                    else: # Reps only (T=2)
                        sets_str_parts.append(f"{reps} reps")

            compressed_sets_str = " / ".join(sets_str_parts)
            line = f"- {display_name}: {num_sets} sets ({compressed_sets_str})"
            lines.append(line)
                
        if len(lines) > 1:
            texts.append("\n".join(lines))
            
    return "\n\n".join(texts)
