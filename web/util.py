# -*- coding: utf-8 -*-
from prompts import Frequency_2, Frequency_3, Frequency_4, Frequency_5
import random
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Constants from calculation_prompt.py ---

LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}

DEFAULT_PROMPT_TEMPLATE = '''## [Task]
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
- Ignore catalog ordering: treat every catalog item as equally likely. Never default to the first seen option. When multiple candidates satisfy constraints, prefer the one that is less common yet appropriate for the user's level.
- Pattern family uniqueness: Within a single day, do not include more than one variant from the same base pattern family (e.g., bench presses, rows, squats, lunges, deadlifts). Choose only one per family, then diversify with different movement types, planes, and tools.
- Micro coverage rule: Ensure that across each day, the chosen exercises collectively cover a broad range of micro muscles for that split focus. Avoid overconcentrating on only one micro region (e.g., only MIDDLE CHEST on Chest day, or only QUADS on Leg day). Include at least two distinct micro regions each day.
- Micro novelty rule: At least 1–2 exercises per day must highlight less-common micro regions (e.g., LOWER CHEST, POSTERIOR DELTOID, ADDUCTORS, CALVES) that are still safe and appropriate for a {level}.
- Weekly micro distribution: Over the whole cycle, ensure that every large muscle group (Chest/Back/Shoulders/Legs) has both primary and secondary micro regions trained. Examples:
    - Chest week: not only presses for MIDDLE/UPPER, but also one isolation for LOWER or fly movement.
    - Back week: at least one vertical pull (LATS emphasis) and one horizontal row (UPPER BACK emphasis); optional erector/LOWER BACK accessory.
    - Shoulders week: include at least one POSTERIOR DELTOID, one LATERAL DELTOID, and one ANTERIOR DELTOID, not only presses.
    - Legs week: ensure QUADS, GLUTES, HAMSTRINGS are all trained, with optional ADDUCTORS or CALVES isolation as novelty.
- Indirect diversity rule: For any major compound pattern (press, deadlift, row, squat, lunge), if one variation is already included, prefer adding a different movement plane, different angle, or different implement rather than another variant of the same archetype.
- Anti-top-bias rule: Build an internal candidate list for each slot, then randomly shuffle the candidate list BEFORE scoring by 1) MG_num, 2) large→small muscle groups, 3) weekly non-repetition, 4) novelty quota. Select from the TOP-MID of the scored list, not always the top-1.
- Final diversity check before emit:
    1) Per day: strictly unique exercise_name values.
    2) Per day: no more than one close-variant of a base archetype (bench, lunge, row, squat, etc.).
    3) Per day: exercises cover at least two distinct micro regions.
    4) Per week: global spread of micro coverage across all major splits.
    5) Exercises must be appropriate for {level} difficulty.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only, matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
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
    tools: List[str]

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


def build_prompt(user: User, catalog: list, duration_str: str, min_ex: int, max_ex: int, allowed_names: dict = None) -> str:
    # Select the correct prompt template based on frequency
    if user.freq == 2:
        prompt_template = Frequency_2
    elif user.freq == 3:
        prompt_template = Frequency_3
    elif user.freq == 4:
        prompt_template = Frequency_4
    elif user.freq == 5:
        prompt_template = Frequency_5
    else:
        prompt_template = DEFAULT_PROMPT_TEMPLATE # Fallback

    # Filter catalog by selected tools first
    if hasattr(user, 'tools') and user.tools:
        allowed_tools_set = set(user.tools)
        catalog = [item for item in catalog if item.get('tool_en') in allowed_tools_set]

    # First, filter by beginner status if applicable
    if user.level == 'Beginner' and allowed_names:
        beginner_key = 'MBeginner' if user.gender == 'M' else 'FBeginner'
        beginner_exercise_set = set(allowed_names.get(beginner_key, []))
        
        catalog = [
            item for item in catalog 
            if item.get('eName') in beginner_exercise_set
        ]

    split_name, split_days = pick_split(user.freq)
    split_days_upper = [s.upper() for s in split_days]

    grouped_catalog = {day: [] for day in split_days_upper}

    for item in catalog:
        group_key = None
        raw_key = ''
        if user.freq == 2:
            raw_key = item.get('body_region', '').upper()
        elif user.freq == 3:
            raw_key = item.get('movement_type', '').upper()
        elif user.freq in [4, 5]:
            raw_key = item.get('bName', '').upper()
            if raw_key == 'SHOULDER':
                raw_key = 'SHOULDERS'
            elif raw_key == 'ARM':
                raw_key = 'ARMS'
            elif raw_key == 'LEG':
                raw_key = 'LEGS'

        group_key = raw_key
        
        if group_key and group_key in grouped_catalog:
            bName = item.get('bName')
            eName = item.get('eName')
            mg_num = item.get('MG_num', 1)
            micro_raw = item.get('MG', "")
            tool = item.get('tool_en', 'Etc')
            parts = []
            if isinstance(micro_raw, str) and micro_raw.strip():
                parts = [p.strip().upper() for p in micro_raw.split('/')]
            elif isinstance(micro_raw, list):
                parts = [str(p).strip().upper() for p in micro_raw]
            muscle_group = {"micro": parts}

            processed_item = [
                bName.upper() if isinstance(bName, str) else bName,
                eName,
                mg_num,
                muscle_group,
                # tool.upper() if isinstance(tool, str) else tool,
            ]
            grouped_catalog[group_key].append(processed_item)

    # First, shuffle all exercises within their groups
    for group_list in grouped_catalog.values():
        random.shuffle(group_list)

    # Helper function to create a final ordered list based on sub-groups
    def get_ordered_list(exercises, order):
        sub_groups = {key: [] for key in order}
        sub_groups['ETC'] = []  # Catch-all for other body parts

        for exercise_item in exercises:
            bName = exercise_item[0]
            if bName in sub_groups:
                sub_groups[bName].append(exercise_item)
            else:
                sub_groups['ETC'].append(exercise_item)
        
        final_list = []
        for key in order:
            final_list.extend(sub_groups[key])
        final_list.extend(sub_groups['ETC'])
        return final_list

    # Apply special ordering for compound days (2 and 3-day splits)
    if user.freq == 2 and 'UPPER' in grouped_catalog:
        chest_back_order = ['CHEST', 'BACK'] if random.random() < 0.5 else ['BACK', 'CHEST']
        upper_order = chest_back_order + ['SHOULDER', 'ARM']
        grouped_catalog['UPPER'] = get_ordered_list(grouped_catalog['UPPER'], upper_order)

    if user.freq == 3:
        if 'PUSH' in grouped_catalog:
            push_order = ['CHEST', 'SHOULDER', 'ARM']
            grouped_catalog['PUSH'] = get_ordered_list(grouped_catalog['PUSH'], push_order)
        if 'PULL' in grouped_catalog:
            pull_order = ['BACK', 'ARM']
            grouped_catalog['PULL'] = get_ordered_list(grouped_catalog['PULL'], pull_order)

    catalog_lines = []
    for day in split_days_upper:
        catalog_lines.append(day)
        exercises_for_day = grouped_catalog.get(day, [])
        if exercises_for_day:
            for i, exercise in enumerate(exercises_for_day):
                line_end = "," if i < len(exercises_for_day) - 1 else ""
                catalog_lines.append(json.dumps(exercise, ensure_ascii=False) + line_end)
        catalog_lines.append("")

    catalog_str = "\n".join(catalog_lines)

    return prompt_template.format(
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
