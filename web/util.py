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


def _filter_catalog(catalog: list, user: User, allowed_names: dict) -> list:
    """Filters the catalog based on user's tools and level."""
    # Filter by selected tools
    if hasattr(user, 'tools') and user.tools:
        allowed_tools_set = set(user.tools)
        catalog = [item for item in catalog if item.get('tool_en') in allowed_tools_set]

    # Filter by level (Beginner/Novice)
    if user.level in ['Beginner', 'Novice'] and allowed_names:
        level_key = 'MBeginner' if user.gender == 'M' else 'FBeginner' if user.level == 'Beginner' else 'MNovice' if user.gender == 'M' else 'FNovice'
        level_exercise_set = set(allowed_names.get(level_key, []))
        catalog = [item for item in catalog if item.get('eName') in level_exercise_set]
    
    return catalog

def _group_catalog_by_split(catalog: list, freq: int) -> Dict[str, list]:
    """Groups the catalog by split days based on frequency."""
    _, split_days = pick_split(freq)
    split_days_upper = [s.upper() for s in split_days]
    grouped_catalog = {day: [] for day in split_days_upper}

    for item in catalog:
        raw_key = ''
        if freq == 2:
            raw_key = item.get('body_region', '').upper()
        elif freq == 3:
            raw_key = item.get('movement_type', '').upper()
        elif freq in [4, 5]:
            raw_key = item.get('bName', '').upper()
            if raw_key == 'SHOULDER': raw_key = 'SHOULDERS'
            elif raw_key == 'ARM': raw_key = 'ARMS'
            elif raw_key == 'LEG': raw_key = 'LEGS'

        if raw_key and raw_key in grouped_catalog:
            bName = item.get('bName')
            eName = item.get('eName')
            mg_num = item.get('MG_num', 1)
            micro_raw = item.get('MG', "")
            parts = [p.strip().upper() for p in micro_raw.split('/')] if isinstance(micro_raw, str) and micro_raw.strip() else [str(p).strip().upper() for p in micro_raw] if isinstance(micro_raw, list) else []
            muscle_group = {"micro": parts}
            
            processed_item = [
                bName.upper() if isinstance(bName, str) else bName,
                eName,
                mg_num,
                muscle_group,
            ]
            grouped_catalog[raw_key].append(processed_item)
            
    return grouped_catalog

def _apply_special_ordering(grouped_catalog: Dict[str, list], freq: int):
    """Applies special ordering for 2 and 3-day splits."""
    for group_list in grouped_catalog.values():
        random.shuffle(group_list)

    def get_ordered_list(exercises, order):
        sub_groups = {key: [] for key in order}
        sub_groups['ETC'] = []
        for exercise_item in exercises:
            bName = exercise_item[0]
            sub_groups.get(bName, sub_groups['ETC']).append(exercise_item)
        
        final_list = []
        for key in order:
            final_list.extend(sub_groups[key])
        final_list.extend(sub_groups['ETC'])
        return final_list

    if freq == 2 and 'UPPER' in grouped_catalog:
        chest_back_order = ['CHEST', 'BACK'] if random.random() < 0.5 else ['BACK', 'CHEST']
        upper_order = chest_back_order + ['SHOULDER', 'ARM']
        grouped_catalog['UPPER'] = get_ordered_list(grouped_catalog['UPPER'], upper_order)

    if freq == 3:
        if 'PUSH' in grouped_catalog:
            grouped_catalog['PUSH'] = get_ordered_list(grouped_catalog['PUSH'], ['CHEST', 'SHOULDER', 'ARM'])
        if 'PULL' in grouped_catalog:
            grouped_catalog['PULL'] = get_ordered_list(grouped_catalog['PULL'], ['BACK', 'ARM'])
    
    return grouped_catalog

def _build_catalog_string(grouped_catalog: Dict[str, list], user: User, catalog: list) -> str:
    """Builds the final catalog string for the prompt."""
    _, split_days = pick_split(user.freq)
    split_days_upper = [s.upper() for s in split_days]
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

            tool_order = ["Free Weight", "Machine", "BodyWeight", "Etc"]
            if user.level == 'Beginner':
                tool_order = ["BodyWeight", "Machine", "Free Weight", "Etc"]
            elif user.level == 'Novice':
                tool_order = ["Machine", "Free Weight", "BodyWeight", "Etc"]

            for group_name in tool_order:
                exercises = day_tool_groups.get(group_name, [])
                if not exercises: continue
                catalog_lines.append(f"  {group_name}:")
                for i, exercise in enumerate(exercises):
                    line_end = "," if i < len(exercises) - 1 else ""
                    catalog_lines.append("    " + json.dumps(exercise, ensure_ascii=False) + line_end)
        catalog_lines.append("")

    return "\n".join(catalog_lines)

def build_prompt(user: User, catalog: list, duration_str: str, min_ex: int, max_ex: int, allowed_names: dict = None) -> str:
    prompt_template = common_prompt

    filtered_catalog = _filter_catalog(catalog, user, allowed_names)
    grouped_catalog = _group_catalog_by_split(filtered_catalog, user.freq)
    ordered_grouped_catalog = _apply_special_ordering(grouped_catalog, user.freq)
    catalog_str = _build_catalog_string(ordered_grouped_catalog, user, filtered_catalog)

    split_name, split_days = pick_split(user.freq)
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

def _get_sort_key(entry, name_map, bname_priority_map):
    """Helper function to generate a sort key for an exercise entry."""
    exercise_name = entry[1]
    exercise_info = name_map.get(exercise_name, {})
    
    b_name = exercise_info.get('bName', 'ETC').upper()
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
            day.sort(key=lambda entry: _get_sort_key(entry, name_map, bname_priority_map))

        lines = [f"## Day{i} (운동개수: {len(day)})" ]
        for entry in day:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            bodypart, exercise_name = entry
            
            exercise_full_info = name_map.get(exercise_name, {})
            
            korean_name = exercise_full_info.get("kName", exercise_name)
            b_name = exercise_full_info.get("bName", bodypart)
            mg_num = exercise_full_info.get("MG_num", "N/A")
            musle_point_sum = exercise_full_info.get("musle_point_sum", "N/A")
            lines.append(f"{b_name:<10} {korean_name:<15} ({mg_num}, {musle_point_sum})")
        if len(lines) > 1:
            out.append("\n".join(lines))
    return "\n\n".join(out)
