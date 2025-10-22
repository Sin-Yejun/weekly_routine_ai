# -*- coding: utf-8 -*-
from .prompts import common_prompt, SPLIT_RULES, LEVEL_GUIDE
import random
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

import os

# --- Load ratio weights from JSON files ---
def load_ratio_from_json(file_name):
    # Correctly construct the path relative to the util.py file's location
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, 'ratios', file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # In a real app, you'd want more robust error handling/logging
        print(f"Error loading {file_name}: {e}")
        return {}

M_ratio_weight = load_ratio_from_json('M_ratio_weight.json')
F_ratio_weight = load_ratio_from_json('F_ratio_weight.json')
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
    "ARM": "(Biceps, Triceps, Forearms)",
    "Abs": "(Upper Abs, Lower Abs, Obliques, Core)",
    "ARM+ABS": "(Biceps, Triceps, Forearms, Upper Abs, Lower Abs, Obliques, Core)"
}

# --- Helper Functions ---

SPLIT_CONFIGS = {
    "2": [
        {"id": "SPLIT", "name": "(Upper/Lower)", "days": ["UPPER", "LOWER"], "rule_key": 2},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B"], "rule_key": "FB_2"}
    ],
    "3": [
        {"id": "SPLIT", "name": "(Push/Pull/Legs)", "days": ["PUSH", "PULL", "LEGS"], "rule_key": 3},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B", "FULLBODY_C"], "rule_key": "FB_3"}
    ],
    "4": [
        {"id": "SPLIT", "name": "(4-Day Split)", "days": ["CHEST", "BACK", "SHOULDERS", "LEGS"], "rule_key": 4},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B", "FULLBODY_C", "FULLBODY_D"], "rule_key": "FB_4"}
    ],
    "5": [
        {"id": "SPLIT", "name": "(5-Day Split)", "days": ["CHEST", "BACK", "LEGS", "SHOULDERS", "ARM+ABS"], "rule_key": 5},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B", "FULLBODY_C", "FULLBODY_D", "FULLBODY_E"], "rule_key": "FB_5"}
    ]
}

L = {
    "M": {"BP":{"B":0.6,"N":1.0,"I":1.3,"A":1.6,"E":2.0},
        "SQ":{"B":0.8,"N":1.2,"I":1.6,"A":2.0,"E":2.5},
        "DL":{"B":1.0,"N":1.5,"I":2.0,"A":2.5,"E":3.0},
        "OHP":{"B":0.4,"N":0.7,"I":0.9,"A":1.1,"E":1.4}},
    
    "F": {"BP":{"B":0.39,"N":0.65,"I":0.845,"A":1.04,"E":1.3},
        "SQ":{"B":0.52,"N":0.78,"I":1.04,"A":1.3,"E":1.625},
        "DL":{"B":0.65,"N":0.975,"I":1.3,"A":1.625,"E":1.95},
        "OHP":{"B":0.26,"N":0.455,"I":0.585,"A":0.715,"E":0.91}}
}
ANCHOR_PCTS = [0.55, 0.60, 0.65, 0.70]
@dataclass
class User:
    gender: str
    weight: float
    level: str
    freq: int
    duration: int
    intensity: str
    tools: List[str]





def _filter_catalog(catalog: list, user: User, allowed_names: dict) -> list:
    ## 카탈로그 필터링
    """Filters the catalog based on user's tools and level."""
    
    # 1. Filter by selected tools
    if hasattr(user, 'tools') and user.tools:
        selected_tools_set = {t.lower() for t in user.tools}
        pullupbar_exercises = set(allowed_names.get("TOOL", {}).get("PullUpBar", []))
        
        filtered_list = []
        for item in catalog:
            tool_en = item.get('tool_en', '').lower()
            e_name = item.get('eName', '')
            is_pullupbar_exercise = e_name in pullupbar_exercises

            include = False
            if is_pullupbar_exercise:
                if "pullupbar" in selected_tools_set:
                    include = True
            else:
                if tool_en in selected_tools_set:
                    include = True
            
            if include:
                filtered_list.append(item)
        catalog = filtered_list

    # 2. Filter by level (Beginner/Novice)
    if user.level in ['Beginner', 'Novice'] and allowed_names:
        level_key = 'MBeginner' if user.gender == 'M' else 'FBeginner' if user.level == 'Beginner' else 'MNovice' if user.gender == 'M' else 'FNovice'
        level_exercise_set = set(allowed_names.get(level_key, []))
        catalog = [item for item in catalog if item.get('eName') in level_exercise_set]
    
    return catalog

def _group_catalog_by_split(catalog: list, split_days: List[str]) -> Dict[str, list]:
    ## 분할별 카탈로그 그룹화
    """Groups the catalog by split days based on the provided day tags."""
    is_full_body_split = any(day.startswith("FULLBODY") for day in split_days)

    # For full body, create one unified catalog. For splits, create one for each day.
    if is_full_body_split:
        grouped_catalog = {"FULLBODY": []}
    else:
        grouped_catalog = {day: [] for day in split_days}

    for item in catalog:
        # Common processing for all items
        bName = item.get('bName')
        eName = item.get('eName')
        mg_num = item.get('MG_num', 1)
        micro_en_raw = item.get('MG', "")
        micro_en_parts = [p.strip() for p in micro_en_raw.split('/')] if isinstance(micro_en_raw, str) and micro_en_raw.strip() else []
        scores = item.get('musle_point', [])
        formatted_micro_parts = []
        if len(micro_en_parts) == len(scores):
            for i in range(len(micro_en_parts)):
                part = micro_en_parts[i]
                score = scores[i]
                formatted_micro_parts.append(f"{part}({score})")
        else:
            formatted_micro_parts = micro_en_parts
        muscle_group = {"micro": formatted_micro_parts}
        category = item.get('category')
        main_ex = item.get('main_ex', False)
        processed_item = [
            bName.upper() if isinstance(bName, str) else bName,
            eName,
            category,
            mg_num,
            muscle_group,
            main_ex,
        ]

        if is_full_body_split:
            grouped_catalog["FULLBODY"].append(processed_item)
        else:
            # Refactored logic for split workouts
            freq = len(split_days)
            target_day_tag = None

            if freq == 2:
                target_day_tag = item.get('body_region', '').upper()
            elif freq == 3:
                target_day_tag = item.get('movement_type', '').upper()
            elif freq in [4, 5]:
                bName_upper = item.get('bName', '').upper()
                
                if bName_upper == 'CHEST': target_day_tag = 'CHEST'
                elif bName_upper == 'BACK': target_day_tag = 'BACK'
                elif bName_upper == 'LEG': target_day_tag = 'LEGS'
                elif bName_upper == 'SHOULDER': target_day_tag = 'SHOULDERS'
                elif bName_upper == 'ARM' or bName_upper == 'ABS':
                    if 'ARM+ABS' in split_days:
                        target_day_tag = 'ARM+ABS'
                    elif bName_upper == 'ARM' and 'ARMS' in split_days:
                        target_day_tag = 'ARM'
                    elif bName_upper == 'ABS' and 'ABS' in split_days:
                        target_day_tag = 'ABS'
            
            if target_day_tag and target_day_tag in grouped_catalog:
                grouped_catalog[target_day_tag].append(processed_item)

    return grouped_catalog

def _apply_special_ordering(grouped_catalog: Dict[str, list], split_days: List[str]):
    ## 특별 순서 적용
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

    freq = len(split_days)
    is_full_body_split = any(day.startswith("FULLBODY") for day in split_days)

    if not is_full_body_split:
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

def _build_catalog_string(grouped_catalog: Dict[str, list], split_days: List[str], catalog: list) -> str:
    ## 카탈로그 문자열 생성
    """Builds the final catalog string for the prompt with nested grouping."""
    catalog_lines = []
    eName_to_tool_map = {item.get('eName'): item.get('tool_en', 'Etc') for item in catalog}
    is_full_body_split = any(day.startswith("FULLBODY") for day in split_days)

    if is_full_body_split:
        # For full body, print a single unified catalog
        catalog_lines.append("FULL BODY (All exercises available for all days)")
        exercises_for_day = grouped_catalog.get("FULLBODY", [])
        if exercises_for_day:
            category_groups = {}
            for exercise in exercises_for_day:
                category = exercise[2] if exercise[2] else "(Uncategorized)"
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(exercise)

            for category in sorted(category_groups.keys()):
                cat_exercises = category_groups[category]
                catalog_lines.append(f"  {category}:")
                for i, exercise in enumerate(cat_exercises):
                    tool = eName_to_tool_map.get(exercise[1], 'Etc')
                    line_end = "," if i < len(cat_exercises) - 1 else ""
                    bName = exercise[0]
                    eName = exercise[1]
                    is_main = exercise[5]
                    display_bName = f"{bName} (main)" if is_main else bName
                    prompt_item = [display_bName, eName, tool, exercise[3], exercise[4]]
                    catalog_lines.append("    " + json.dumps(prompt_item, ensure_ascii=False) + line_end)
    else:
        # Existing logic for split workouts
        for day in split_days:
            muscle_group_info = SPLIT_MUSCLE_GROUPS.get(day, "")
            catalog_lines.append(f"{day} {muscle_group_info}".strip())
            exercises_for_day = grouped_catalog.get(day, [])

            if exercises_for_day:
                category_groups = {}
                for exercise in exercises_for_day:
                    category = exercise[2] if exercise[2] else "(Uncategorized)"
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(exercise)

                for category in sorted(category_groups.keys()):
                    cat_exercises = category_groups[category]
                    catalog_lines.append(f"  {category}:")
                    for i, exercise in enumerate(cat_exercises):
                        tool = eName_to_tool_map.get(exercise[1], 'Etc')
                        line_end = "," if i < len(cat_exercises) - 1 else ""
                        bName = exercise[0]
                        eName = exercise[1]
                        is_main = exercise[5]
                        display_bName = f"{bName} (main)" if is_main else bName
                        prompt_item = [display_bName, eName, tool, exercise[3], exercise[4]]
                        catalog_lines.append("    " + json.dumps(prompt_item, ensure_ascii=False) + line_end)

    return "\n".join(catalog_lines)

def build_prompt(user: User, catalog: list, duration_str: str, min_ex: int, max_ex: int, split_config: dict, allowed_names: dict = None) -> str:
    ## 프롬프트 생성
    prompt_template = common_prompt

    split_days = split_config["days"]
    split_name = split_config["name"]
    rule_key = split_config["rule_key"]

    filtered_catalog = _filter_catalog(catalog, user, allowed_names)
    grouped_catalog = _group_catalog_by_split(filtered_catalog, split_days)
    ordered_grouped_catalog = _apply_special_ordering(grouped_catalog, split_days)
    catalog_str = _build_catalog_string(ordered_grouped_catalog, split_days, filtered_catalog)

    split_rules = SPLIT_RULES.get(rule_key, "")
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

def format_new_routine(plan_json: dict, name_map: dict, enable_sorting: bool = False, show_b_name: bool = True) -> str:
    ## 새로운 루틴 포맷팅
    import logging
    import random
    import json
    logging.basicConfig(level=logging.INFO)

    if not isinstance(plan_json, dict) or "days" not in plan_json:
        return "Invalid plan format."
    out = []
    for i, day in enumerate(plan_json["days"], 1):
        if not isinstance(day, list):
            continue

        if enable_sorting:
            bname_priority_map = {
                'CHEST': 1, 'BACK': 1, 'LEG': 1, 'SHOULDER': 2, 'ARM': 3, 'ABS': 4
            }
            random_bname_order = {bname: random.random() for bname in bname_priority_map.keys()}

            def get_randomized_sort_key(entry):
                exercise_name = None
                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list):
                    exercise_name = entry[0]
                elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str):
                    exercise_name = entry[1]
                else:
                    return (99, 0.5, 0, 0)

                exercise_info = name_map.get(exercise_name, {})
                b_name = exercise_info.get('bName', 'ETC').upper()
                mg_num = exercise_info.get('MG_num', 0)
                muscle_point_sum = exercise_info.get('musle_point_sum', 0)
                prio = bname_priority_map.get(b_name, 5)
                random_prio = random_bname_order.get(b_name, 0.5)
                try: mg_num = int(mg_num)
                except (ValueError, TypeError): mg_num = 0
                try: muscle_point_sum = int(muscle_point_sum)
                except (ValueError, TypeError): muscle_point_sum = 0
                return (prio, random_prio, -mg_num, -muscle_point_sum)
            day.sort(key=get_randomized_sort_key)

        # --- Conditional Formatting ---
        if show_b_name:
            # LOGIC FOR INITIAL ROUTINE (with b_name and padding)
            day_display_data = []
            micro_sums = {}
            max_b_name_width = 0
            max_k_name_width = 0

            for entry in day:
                data = {"b_name": "", "k_name": "", "details": ""}
                exercise_name = None
                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list): exercise_name = entry[0]
                elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str): exercise_name = entry[1]
                if not exercise_name: continue

                exercise_info = name_map.get(exercise_name, {})
                b_name = exercise_info.get("bName", "N/A")
                is_main = exercise_info.get("main_ex", False)
                data["b_name"] = f"{b_name} (main)" if is_main else b_name
                data["k_name"] = exercise_info.get("kName", exercise_name)
                data["details"] = f"({exercise_info.get('category', 'N/A')})"

                b_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["b_name"])
                k_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["k_name"])
                if b_name_width > max_b_name_width: max_b_name_width = b_name_width
                if k_name_width > max_k_name_width: max_k_name_width = k_name_width
                day_display_data.append(data)

                micro_groups_raw = exercise_info.get("MG_ko")
                micro_groups = []
                if isinstance(micro_groups_raw, str): micro_groups = [m.strip() for m in micro_groups_raw.split('/') if m.strip()]
                elif isinstance(micro_groups_raw, list): micro_groups = [str(m).strip() for m in micro_groups_raw if str(m).strip()]
                try: muscle_point = int(exercise_info.get("musle_point_sum", 0))
                except (ValueError, TypeError): muscle_point = 0
                if muscle_point > 0:
                    for group in micro_groups:
                        micro_sums[group] = micro_sums.get(group, 0) + muscle_point

            day_header = f"## Day{i} (운동개수: {len(day)})"
            if micro_sums:
                sorted_micro_sums = sorted(micro_sums.items(), key=lambda item: item[1], reverse=True)
                micro_sum_str = ", ".join([f"{group}: {point}" for group, point in sorted_micro_sums])

            lines = [day_header]
            for data in day_display_data:
                b_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["b_name"])
                k_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["k_name"])
                padding1 = " " * (max_b_name_width - b_name_width + 2)
                padding2 = " " * (max_k_name_width - k_name_width + 3)
                line = f'{data["b_name"]}{padding1}{data["k_name"]}{padding2}{data["details"]}'
                lines.append(line)

            if len(lines) > 1:
                out.append("\n".join(lines))

        else:
            # LOGIC FOR DETAILED ROUTINE (no b_name, single space)
            day_display_data = []
            micro_sums = {}
            for entry in day:
                data = {"k_name": "", "details": ""}
                exercise_name = None
                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list): exercise_name = entry[0]
                elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str): exercise_name = entry[1]
                if not exercise_name: continue

                exercise_info = name_map.get(exercise_name, {})
                data["k_name"] = exercise_info.get("kName", exercise_name)

                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list):
                    sets = entry[1:]
                    set_parts = []
                    for s in sets:
                        if isinstance(s, list) and len(s) == 3:
                            reps, weight, time = s
                            if reps > 0 and weight > 0: set_parts.append(f"{reps}x{weight}")
                            elif reps > 0: set_parts.append(f"{reps}회")
                            elif time > 0 and weight > 0: set_parts.append(f"{weight}kg {time}초")
                            elif time > 0: set_parts.append(f"{time}초")
                    data["details"] = " / ".join(set_parts)
                else:
                    data["details"] = f"({exercise_info.get('category', 'N/A')})"
                
                day_display_data.append(data)
                
                micro_groups_raw = exercise_info.get("MG_ko")
                micro_groups = []
                if isinstance(micro_groups_raw, str): micro_groups = [m.strip() for m in micro_groups_raw.split('/') if m.strip()]
                elif isinstance(micro_groups_raw, list): micro_groups = [str(m).strip() for m in micro_groups_raw if str(m).strip()]
                try: muscle_point = int(exercise_info.get("musle_point_sum", 0))
                except (ValueError, TypeError): muscle_point = 0
                if muscle_point > 0:
                    for group in micro_groups:
                        micro_sums[group] = micro_sums.get(group, 0) + muscle_point

            day_header = f"## Day{i} (운동개수: {len(day)})"
            if micro_sums:
                sorted_micro_sums = sorted(micro_sums.items(), key=lambda item: item[1], reverse=True)
                micro_sum_str = ", ".join([f"{group}: {point}" for group, point in sorted_micro_sums])

            lines = [day_header]
            for data in day_display_data:
                line = f'{data["k_name"]} {data["details"]}'
                lines.append(line)

            if len(lines) > 1:
                out.append("\n".join(lines))

    formatted_routine = "\n\n".join(out)
    if not show_b_name:
        raw_output_str = json.dumps(plan_json, ensure_ascii=False)
        return f"{formatted_routine}\n\n--- Raw Model Output ---\n{raw_output_str}"
    
    return formatted_routine
