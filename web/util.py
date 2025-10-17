# -*- coding: utf-8 -*-
from prompts import common_prompt, detail_prompt_abstract, SPLIT_RULES, LEVEL_GUIDE, LEVEL_SETS, LEVEL_PATTERN, LEVEL_WORKING_SETS, DUMBBELL_GUIDE
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

def parse_duration_bucket(bucket: str) -> int:
    if not isinstance(bucket, str): return 60
    numbers = re.findall(r'\d+', bucket)
    return int(numbers[-1]) if numbers else 60

def round_to_step(x: float, step: int = 5) -> int:
    return int(round(x / step) * step)

def compute_tm(gender: str, bodyweight: float, level: str, step: int = 5) -> dict:
    """TM = round( 0.9 * (bodyweight * L[gender][lift][level_code]) , step )"""
    code = LEVEL_CODE.get(level)
    if not code or gender not in L:  # 안전장치
        return {"BP":0,"SQ":0,"DL":0,"OHP":0}
    coeffs = L[gender]
    tm = {}
    for lift in ("BP","SQ","DL","OHP"):
        raw = 0.9 * (bodyweight * coeffs[lift][code])
        tm[lift] = round_to_step(raw, step)
    return tm

def build_load_row(tm_val: int, pcts=ANCHOR_PCTS, step: int = 5) -> str:
    # "55%:xx, 60%:yy, 65%:zz, 70%:aa" 형태 문자열
    parts = []
    for p in pcts:
        kg = round_to_step(tm_val * p, step)
        parts.append(f"{int(p*100)}%:{kg}")
    return ", ".join(parts)

def _parse_reps_pattern(level: str) -> list[int]:
    """
    prompts.LEVEL_PATTERN[level]에서 숫자 배열만 뽑기.
    예: "- Novice: [15,12,10,9,8]" -> [15,12,10,9,8]
    """
    pat = LEVEL_PATTERN.get(level, "")
    nums = re.findall(r'\d+', pat)
    return [int(n) for n in nums] if nums else [12, 10, 8, 8]

def _parse_working_pct_bounds(level: str) -> tuple[float, float]:
    """
    prompts.LEVEL_WORKING_SETS[level]에서 퍼센트 범위를 추출해 (low, high) 반환.
    - Beginner: "65–70% of TM" -> (0.65, 0.70)
    - Novice: "70% of TM"      -> (0.70, 0.70)
    """
    text = LEVEL_WORKING_SETS.get(level, "")
    m_range = re.search(r'(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\s*%', text)
    if m_range:
        low, high = float(m_range.group(1))/100.0, float(m_range.group(2))/100.0
        return (min(low, high), max(low, high))
    m_single = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if m_single:
        v = float(m_single.group(1))/100.0
        return (v, v)
    return (0.70, 0.70)

def _linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1: 
        return [a]
    step = (b - a) / (n - 1)
    return [a + i*step for i in range(n)]

def _round_by_tool(kg: float, tool: str) -> int:
    """Dumbbell=2kg, 그 외=5kg 배수 반올림."""
    step = 2 if (tool or '').lower() == 'dumbbell' else 5
    return round_to_step(kg, step)

def build_example_sets_by_level(tm_val: int, level: str, tool: str = 'Barbell') -> str:
    """
    Warm-up 2세트 + Working (레벨 범위 등분)
    - 세트 수: LEVEL_PATTERN 기반 → 서버 스키마(4/5/6)와 자연 일치
    - 1세트: 바벨이면 무조건 20kg(빈봉), 덤벨/머신이면 규칙적용
    - 2세트: TM의 50%
    - 3세트+: LEVEL_WORKING_SETS의 범위를 등분
    """
    reps = _parse_reps_pattern(level)
    total_sets = max(4, len(reps))  # 안전장치
    # Warm-up
    warmup_pcts = [0.25, 0.50]  # ~25% (빈봉 대체), 50%
    # Working
    work_low, work_high = _parse_working_pct_bounds(level)
    work_sets = max(0, total_sets - 2)
    work_pcts = _linspace(work_low, work_high, work_sets) if work_sets > 0 else []

    pcts = warmup_pcts + work_pcts
    pcts = pcts[:total_sets]
    reps = reps[:total_sets] + [reps[-1]]*(total_sets - len(reps)) if len(reps) < total_sets else reps[:total_sets]

    out = []
    for idx, (r, p) in enumerate(zip(reps, pcts), 1):
        if idx == 1 and (tool or '').lower() == 'barbell':
            kg = 20  # 빈봉 고정(서버 스키마도 바벨 최소 20kg과 일치)
        else:
            kg = _round_by_tool(tm_val * p, tool)
        out.append(f"[{r},{kg},0]")
    return ", ".join(out)

def _filter_catalog(catalog: list, user: User, allowed_names: dict) -> list:
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

def create_detail_prompt(user: User, initial_routine: dict, name_to_exercise_map: dict) -> str:
    """Generates the prompt for the detailed routine generation API."""
    all_exercises_for_prompt = []
    for day_exercises in initial_routine.get("days", []):
        for bp, e_name in day_exercises:
            exercise_details = name_to_exercise_map.get(e_name)
            if exercise_details:
                tool = exercise_details.get('tool_en', 'Etc')
                all_exercises_for_prompt.append({"ename": e_name, "tool": tool})
    
    if not all_exercises_for_prompt:
        return "No exercises found in the initial routine to generate a details prompt."

    tm = compute_tm(user.gender, user.weight, user.level)
    bp_loads = build_load_row(tm['BP'])
    sq_loads = build_load_row(tm['SQ'])
    dl_loads = build_load_row(tm['DL'])
    ohp_loads = build_load_row(tm['OHP'])

    # ★ 레벨/툴 반영 예시 세트 (Barbell & Dumbbell)
    bp_example    = build_example_sets_by_level(tm['BP'], user.level, tool='Barbell')
    sq_example    = build_example_sets_by_level(tm['SQ'], user.level, tool='Barbell')
    dl_example    = build_example_sets_by_level(tm['DL'], user.level, tool='Barbell')
    ohp_example   = build_example_sets_by_level(tm['OHP'], user.level, tool='Barbell')
    bp_example_db = build_example_sets_by_level(tm['BP'], user.level, tool='Dumbbell')
    sq_example_db = build_example_sets_by_level(tm['SQ'], user.level, tool='Dumbbell')

    prompt = detail_prompt_abstract.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        intensity=user.intensity,
        exercise_list_with_einfotype_json=json.dumps(all_exercises_for_prompt, ensure_ascii=False),
        TM_BP=tm['BP'],
        TM_SQ=tm['SQ'],
        TM_DL=tm['DL'],
        TM_OHP=tm['OHP'],
        BP_loads=bp_loads,
        SQ_loads=sq_loads,
        DL_loads=dl_loads,
        OHP_loads=ohp_loads,
        level_sets=LEVEL_SETS[user.level],
        level_pattern=LEVEL_PATTERN[user.level],
        level_working_sets=LEVEL_WORKING_SETS[user.level],
        dumbbell_weight_guide=DUMBBELL_GUIDE[user.level],
        BP_example=bp_example, SQ_example=sq_example,
        DL_example=dl_example, OHP_example=ohp_example,
        BP_example_db=bp_example_db, SQ_example_db=sq_example_db
    )
    
    return prompt
