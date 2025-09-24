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

## MOVEMENT GROUPS (cap: at most one per group per day)
Groups: Press, Row, PullUp, SQUAT, Lunge, Raise, Deadlift, PushUps.
- Press = all chest or shoulder presses
- Row = horizontal pulling movements
- PullUp = vertical pulling movements such as pull up, chin up, pulldown
- SQUAT = back, front, box, smith, hack, V, reverse V, leg press type squats
- Lunge = lunge, split squat, step up
- Raise = all raise variations
- Deadlift = all hinge and deadlift variations
- PushUps = push up variations
Notes:
- Split squat and step up belong to Lunge, not SQUAT.
- Pullover is not Press, Row, or PullUp. Treat it as an accessory for chest or lats. It does not block Press, Row, or PullUp.

## MICRO COVERAGE
- For each day, cover at least two distinct micro regions. Avoid concentrating on a single region.
- For each day, include one or two safe and less common targets that match the user level. Examples: lower chest, posterior deltoid, adductors, calves.

## WEEKLY MINIMUMS BY SPLIT INTENT
- PUSH: include one middle or upper press and at least one chest isolation or fly. Shoulders must cover anterior (press may satisfy this indirectly) and lateral via a raise. Include at least one triceps movement if available.
- PULL: include at least one vertical pull for lats and at least one horizontal row for upper back. Lower back accessory is optional. Include at least one biceps movement if available.
- LEGS: include one SQUAT pattern with MG_num 4 or higher and one deadlift or hinge pattern with MG_num 4 or higher. Also cover quads, glutes, and hamstrings. Adductors or calves isolation is optional.

## LEVEL BASED EQUIPMENT PREFERENCES
Apply these preferences when building and scoring candidates. Always obey all other rules.
- Beginner: prefer bodyweight first, then machines or cables, then free weights. Avoid unstable implements. Keep novelty conservative.
- Novice: prefer machines or cables as primary, with free weights as secondary. Bodyweight allowed.
- Intermediate: prefer free weights as primary, with machines or cables supportive. Allow more unilateral or stability when safe.
- Advanced: strongly prefer free weights. Use machines for targeted overload or novelty.
- Elite: prioritize free weights and varied planes or implements. Use machines sparingly for precise fatigue management.
Equipment tie break within a day by level:
Beginner = bodyweight then machine then cable then free
Novice = machine then cable then free then bodyweight
Intermediate or Advanced or Elite = free then machine then cable then bodyweight

## SELECTION PROCEDURE (follow exactly)
1) Candidate Build for each day
   - Filter by the day’s split intent.
   - Enforce the movement group cap: at most one from each group for that day.
   - Apply level based equipment preferences when forming the candidate pool.
2) Primary Selection
   - Choose compounds first (higher MG_num), then accessories (MG_num equals 3), then isolations (MG_num less than or equal to 2).
   - Indirect diversity: after selecting a major pattern such as press, row, squat, lunge, or deadlift, prefer the next item with a different plane, angle, or implement.
3) Micro Coverage Check
   - Ensure at least two distinct micro regions in the day. If not satisfied, replace the lowest priority item with one that fixes coverage while still respecting the group caps.
4) Ordering Rules
   - Sort by MG_num in strictly descending order.
   - No isolation with MG_num less than or equal to 2 may appear before any compound or accessory with MG_num greater than or equal to 3.
   - Tie breakers, in order:
     a) Chest or Back before Shoulders or Arms or Calves
     b) Bilateral before unilateral
     c) Equipment preference per the level based ordering above
     d) Prefer items not yet used this week
5) Anti Top Bias
   - Before scoring, shuffle candidates for each slot. When a tie remains after all rules, choose from the upper middle of the ranked set, not always the top item.
6) Integrity Loop
   - Re check uniqueness, group caps, micro diversity, weekly split minimums, and level equipment preferences. If any rule fails, replace the lowest priority item and re sort, then repeat the checks.

## GLOBAL GUARDS
- For each day: unique exercise_name, at most one per movement group, MG_num strictly in descending order, at least two micro regions.
- For the week: balanced coverage across PUSH, PULL, and LEGS according to the weekly minimums.
- All exercises must be appropriate for the user level.
- Avoid risky or highly technical variants for Beginner and Novice.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (no spaces/newlines), matching:
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
        #prompt_template = DEFAULT_PROMPT_TEMPLATE
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
    eName_to_tool_map = {item.get('eName'): item.get('tool_en', 'Etc') for item in catalog}

    for day in split_days_upper:
        catalog_lines.append(day)
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
