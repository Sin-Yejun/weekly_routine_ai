# -*- coding: utf-8 -*-
from prompts import common_prompt, SPLIT_RULES, LEVEL_GUIDE
import random
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Constants from calculation_prompt.py ---

LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}

SPLIT_MUSCLE_GROUPS = {
    "UPPER": "(Upper Chest, Middle Chest, Lower Chest, Upper Back, Lower Back, Lats, Anterior Deltoid, Lateral Deltoid, Posterior Deltoid, Traps, Biceps, Triceps, Forearms)",
    "LOWER": "(Glutes, Quads, Hamstrings, Adductors, Abductors, Calves)",
    "PUSH": "(Upper Chest, Middle Chest, Lower Chest, Anterior Deltoid, Lateral Deltoid, Posterior Deltoid, Triceps)",
    "PULL": "(Upper Back, Lower Back, Lats, Traps, Biceps)",
    "LEGS": "(Glutes, Quads, Hamstrings, Adductors, Abductors, Calves)",
    "CHEST": "(Upper Chest, Middle Chest, Lower Chest)",
    "BACK": "(Upper Back, Lower Back, Lats)",
    "SHOULDERS": "(Anterior Deltoid, Lateral Deltoid, Posterior Deltoid, Traps)",
    "ARMS": "(Biceps, Triceps, Forearms)"
}

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
    prompt_template = common_prompt

    # Filter catalog by selected tools first
    if hasattr(user, 'tools') and user.tools:
        allowed_tools_set = set(user.tools)
        catalog = [item for item in catalog if item.get('tool_en') in allowed_tools_set]

    # Filter catalog by level (Beginner/Novice) if applicable
    if user.level in ['Beginner', 'Novice'] and allowed_names:
        if user.level == 'Beginner':
            level_key = 'MBeginner' if user.gender == 'M' else 'FBeginner'
        else: # Novice
            level_key = 'MNovice' if user.gender == 'M' else 'FNovice'
        
        level_exercise_set = set(allowed_names.get(level_key, []))
        
        catalog = [
            item for item in catalog 
            if item.get('eName') in level_exercise_set
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
    eName_to_tool_map = {item.get('eName'): item.get('tool_en', 'Etc') for item in catalog}

    for day in split_days_upper:
        muscle_group_info = SPLIT_MUSCLE_GROUPS.get(day, "")
        catalog_lines.append(f"{day} {muscle_group_info}".strip())
        exercises_for_day = grouped_catalog.get(day, [])

        if exercises_for_day:
            day_tool_groups = {"Free Weight": [], "Machine": [], "BodyWeight": [], "Etc": []}
            free_weight_tools = {"Barbell", "Dumbbell", "EZbar", "Kettlebell"}

            for exercise_item in exercises_for_day:
                tool = eName_to_tool_map.get(exercise_item[1], 'Etc')
                if tool in free_weight_tools:
                    day_tool_groups["Free Weight"].append(exercise_item)
                elif tool == 'Machine':
                    day_tool_groups["Machine"].append(exercise_item)
                elif tool == 'Bodyweight':
                    day_tool_groups["BodyWeight"].append(exercise_item)
                else:
                    day_tool_groups["Etc"].append(exercise_item)

            if user.level == 'Beginner':
                tool_group_order = ["BodyWeight", "Machine", "Free Weight", "Etc"]
            elif user.level == 'Novice':
                tool_group_order = ["Machine", "Free Weight", "BodyWeight", "Etc"]
            else:
                tool_group_order = ["Free Weight", "Machine", "BodyWeight", "Etc"]

            flat_ordered_list = []
            for group_name in tool_group_order:
                flat_ordered_list.extend(day_tool_groups.get(group_name, []))

            temp_day_lines = []
            for group_name in tool_group_order:
                exercises = day_tool_groups.get(group_name, [])
                if not exercises:
                    continue
                temp_day_lines.append(f"  {group_name}:")
                for exercise in exercises:
                    is_last = (exercise == flat_ordered_list[-1]) if flat_ordered_list else False
                    line_end = "" if is_last else ","
                    temp_day_lines.append("    " + json.dumps(exercise, ensure_ascii=False) + line_end)
            catalog_lines.extend(temp_day_lines)

        catalog_lines.append("")

    catalog_str = "\n".join(catalog_lines)
    
    split_rules = SPLIT_RULES.get(user.freq, "")
    level_guide = LEVEL_GUIDE.get(user.level, "")

    return prompt_template.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        freq=user.freq,
        duration=user.duration,
        intensity=user.intensity,
        split_name=split_name,
        split_days=" / ".join(split_days),
        level_guide=level_guide,
        split_rules=split_rules,
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
            random.shuffle(day)  # Shuffle for random tie-breaking

            bname_priority_map = {
                'CHEST': 1, 'BACK': 1, 'LEG': 1,
                'SHOULDER': 2,
                'ARM': 3,
                'ABS': 4
            }

            def sort_key(entry):
                exercise_name = entry[1]
                exercise_info = name_map.get(exercise_name, {})
                
                b_name = exercise_info.get('bName', 'ETC').upper() # Normalize to uppercase
                mg_num = exercise_info.get('MG_num', 0)
                muscle_point_sum = exercise_info.get('musle_point_sum', 0)

                bname_prio = bname_priority_map.get(b_name, 5)  # 5 for others (ETC)

                try:
                    mg_num = int(mg_num)
                except (ValueError, TypeError):
                    mg_num = 0
                try:
                    muscle_point_sum = int(muscle_point_sum)
                except (ValueError, TypeError):
                    muscle_point_sum = 0
                
                # Sort by bName priority (asc), then MG_num (desc), then muscle_point_sum (desc)
                return (bname_prio, -mg_num, -muscle_point_sum)

            day.sort(key=sort_key)

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
