import re
from flask import Flask, jsonify, request, send_from_directory
import json
import os
import logging
import random

import openai
from openai import OpenAI
from json_repair import repair_json as json_repair_str
from dotenv import load_dotenv
from prompts import detail_prompt_abstract
from util import User, build_prompt, format_new_routine, SPLIT_CONFIGS

# --- Flask App Initialization --
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['JSON_AS_ASCII'] = False
load_dotenv()
app.logger.setLevel(logging.INFO)

# --- Path Definitions --
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'processed_query_result_200.json')

# --- Load Exercise Catalog and Name Maps --
exercise_catalog = []
name_to_exercise_map = {}
name_to_korean_map = {}
name_to_einfotype_map = {}

try:
    with open(EXERCISE_CATALOG_PATH, 'r', encoding='utf-8') as f:
        exercise_catalog = json.load(f)
        for exercise in exercise_catalog:
            e_name = exercise.get('eName')
            if e_name:
                name_to_exercise_map[e_name] = exercise
                name_to_einfotype_map[e_name] = exercise.get('eInfoType')
                name_to_korean_map[e_name] = {
                    'bName': exercise.get('bName'),
                    'kName': exercise.get('kName'),
                    'MG_num': exercise.get('MG_num'),
                    'category': exercise.get('category'),
                    'musle_point_sum': exercise.get('musle_point_sum'),
                    'MG': exercise.get('MG'),
                    'MG_ko': exercise.get('MG_ko'),
                    'main_ex': exercise.get('main_ex', False),
                }
except (FileNotFoundError, json.JSONDecodeError) as e:
    app.logger.error(f"CRITICAL: Could not load exercise catalog at {EXERCISE_CATALOG_PATH}: {e}")

# --- Global Variables & Helper Functions ---

def build_detail_week_schema(initial_routine: dict, level: str) -> dict:
    """
    2단계(세부 루틴) 출력 구조를 강제하는 JSON 스키마를 생성합니다.
    - days 길이는 1단계 루틴과 동일합니다.
    - 각 day의 exercise 개수는 1단계 day의 개수와 동일합니다.
    - 각 운동의 eInfoType에 따라 세트([reps, weight, time]) 스키마가 동적으로 변경됩니다.
    - 세트 수는 사용자의 레벨에 따라 4~6개로 결정됩니다.
    """
    if level == 'Beginner':
        num_sets = 4
    elif level == 'Novice':
        num_sets = 5
    else:  # Intermediate, Advanced, Elite
        num_sets = 6

    def _build_set_schema(einfo_type, tool: str = ""):
        # reps: 8~15 강제
        reps_schema   = {"type": "integer", "description": "reps", "minimum": 8, "maximum": 15}

        # 덤벨=2kg 배수, 그 외(머신/바벨/케이블 등)=5kg 배수
        t = (tool or "").lower()
        #multiple = 2 if t == "dumbbell" else 5
        weight_schema = {"type": "number", "description": "weight", "minimum": 0}

        time_schema   = {"type": "integer", "description": "time"}

        reps_zero_schema   = {"type": "integer", "const": 0, "description": "reps (must be 0)"}
        weight_zero_schema = {"type": "number",  "const": 0, "description": "weight (must be 0)"}
        time_zero_schema   = {"type": "integer", "const": 0, "description": "time (must be 0)"}

        if einfo_type == 1:      # [0, 0, time]
            prefix_items = [reps_zero_schema, weight_zero_schema, time_schema]
        elif einfo_type == 2:    # [reps, 0, 0]
            prefix_items = [reps_schema, weight_zero_schema, time_zero_schema]
        elif einfo_type == 5:    # [0, weight, time]
            prefix_items = [reps_zero_schema, weight_schema, time_schema]
        elif einfo_type == 6:    # [reps, weight, 0]
            prefix_items = [reps_schema, weight_schema, time_zero_schema]
        else:                    # 기본: [reps, weight, time]
            prefix_items = [reps_schema, weight_schema, time_schema]

        return {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "prefixItems": prefix_items,
            "items": False
        }

    days = initial_routine.get("days", [])
    day_schemas_prefix = []

    for day in days:
        allowed_enames = []
        if isinstance(day, list):
            for pair in day:
                if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[1], str):
                    allowed_enames.append(pair[1])
        
        if not allowed_enames:
            continue

        one_of_exercise_schemas = []
        for ename in allowed_enames:
            # name_to_einfotype_map is a global dictionary available in the file
            einfo_type = name_to_einfotype_map.get(ename)
            exercise_info = name_to_exercise_map.get(ename, {})
            tool = (exercise_info.get("tool_en") or "").lower()
            set_schema = _build_set_schema(einfo_type, tool)
            
            specific_exercise_schema = {
                "type": "array",
                "description": f"Schema for exercise '{ename}'. Consists of ename followed by {num_sets} set arrays.",
                "minItems": num_sets + 1,
                "maxItems": num_sets + 1,
                "prefixItems": [
                    {"type": "string", "const": ename}
                ],
                "items": set_schema
            }
            one_of_exercise_schemas.append(specific_exercise_schema)

        day_schema = {
            "type": "array",
            "description": f"A single day's workout, containing {len(allowed_enames)} unique exercises. The order of exercises must be logical (e.g., compound then isolation).",
            "minItems": len(allowed_enames),
            "maxItems": len(allowed_enames),
            "items": {
                "oneOf": one_of_exercise_schemas
            }
        }
        day_schemas_prefix.append(day_schema)

    return {
        "type": "object",
        "required": ["days"],
        "properties": {
            "days": {
                "type": "array",
                "minItems": len(day_schemas_prefix),
                "maxItems": len(day_schemas_prefix),
                "prefixItems": day_schemas_prefix,
                "items": False
            }
        },
        "additionalProperties": False
    }

# ENABLE_LEG_MAIN_CONSTRAINT = True
ENABLE_LEG_MAIN_CONSTRAINT = False

BODY_PART_ENUM = ["Abs","Arm","Back","Cardio","Chest","Leg","Lifting","Shoulder","etc"]
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
VLLM_MODEL    = "google/gemma-3-4b-it"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

EXERCISE_COUNT_SCHEMA = {
    'Beginner': {
        30: (3, 4), 45: (4, 5), 60: (5, 6), 75: (6, 7), 90: (7, 8)
    },
    'Novice': {
        30: (3, 4), 45: (4, 5), 60: (5, 6), 75: (6, 7), 90: (7, 8)
    },
    'Intermediate': {
        30: (3, 4), 45: (4, 5), 60: (6, 7), 75: (7, 8), 90: (8, 9)
    },
    'Advanced': {
        30: (3, 4), 45: (4, 5), 60: (6, 7), 75: (7, 8), 90: (8, 9)
    },
    'Elite': {
        30: (3, 4), 45: (4, 5), 60: (6, 7), 75: (7, 8), 90: (8, 9)
    }
}

def get_user_config(data: dict) -> tuple[User, int, int]:
    """Extracts user configuration from request data, creates a User object, and determines exercise counts."""
    duration_str = str(data.get('duration', '60'))
    numeric_duration = int(re.sub(r'[^0-9]', '', duration_str) or '60')
    
    user = User(
        gender=data.get('gender', 'M'),
        weight=float(data.get('weight', 70)),
        level=data.get('level', 'Intermediate'),
        freq=int(data.get('freq', 3)),
        duration=numeric_duration,
        intensity=data.get('intensity', 'Normal'),
        tools=data.get('tools', [])
    )
    
    level_schema = EXERCISE_COUNT_SCHEMA.get(user.level, EXERCISE_COUNT_SCHEMA['Intermediate'])
    duration_key = min(level_schema.keys(), key=lambda k: abs(k - user.duration) if k <= user.duration else float('inf'))
    min_ex, max_ex = level_schema[duration_key]
    
    return user, min_ex, max_ex

def _leg_main_cap(level: str) -> int:
    return 2 if level in ('Advanced', 'Elite') else 1


def _leg_pair_enums_for_day(freq, tag, allowed_names):
    # LEG_MAIN
    leg_main_names = list(dict.fromkeys(allowed_names.get('LEG_MAIN', [])))
    main_pairs = []
    for n in leg_main_names:
        ex = name_to_exercise_map.get(n)
        if ex and ex.get('bName'):
            main_pairs.append([ex['bName'], n])

    # 해당 요일 풀(LEGS/LOWER)에서 OTHER = (요일풀 - LEG_MAIN)
    day_pairs_all = _allowed_pairs_for_day_by_name(freq, tag, allowed_names)
    other_pairs = [p for p in day_pairs_all if p[1] not in leg_main_names]

    # ALL = MAIN ∪ OTHER
    all_pairs = main_pairs + [p for p in other_pairs if p not in main_pairs]
    return main_pairs, other_pairs, all_pairs

def make_legs_day_schema_by_name(freq, tag, allowed_names, min_ex, max_ex, level):
    main_pairs, other_pairs, all_pairs = _leg_pair_enums_for_day(freq, tag, allowed_names)
    cap = _leg_main_cap(level)  # K

    # 핵심: 앞의 cap칸은 ALL 허용(=MAIN도 가능), 이후는 OTHER만
    prefix_items = [{"enum": all_pairs} for _ in range(cap)]

    return {
        "type": "array",
        "description": (
            "NO DUPLICATE EXERCISES."
            "At most {} LEG_MAIN exercises allowed; remaining slots must be non-LEG_MAIN. "
        ).format(cap),
        "minItems": min_ex,
        "maxItems": max_ex,
        "prefixItems": prefix_items,
        "items": {"enum": other_pairs}  # cap 이후 칸은 MAIN 금지
    }


def make_day_schema_pairs_by_name(allowed_names_for_day, min_ex, max_ex):
    pair_enum = []
    seen = set()
    random.shuffle(allowed_names_for_day)

    for ex_name in allowed_names_for_day:
        exercise = name_to_exercise_map.get(ex_name)
        if not exercise:
            continue
        bp = exercise.get('bName')
        if not bp:
            continue
        key = (bp, ex_name)
        if key in seen:
            continue
        seen.add(key)
        pair_enum.append([bp, ex_name])

    if not pair_enum:
        for ex_name, exercise in name_to_exercise_map.items():
            bp = exercise.get('bName')
            if bp:
                pair_enum.append([bp, ex_name])

    return {
        "type": "array",
        "description": "All items must be distinct: each exercise_name appears only once per day. Arrange them in an effective order (compound → accessories) appropriate to the user’s level.",
        "minItems": min_ex,
        "maxItems": min_ex,
        "items": {"enum": pair_enum},
    }


def build_week_schema_by_name(freq, split_tags, allowed_names, min_ex, max_ex, level='Intermediate'):
    def _pairs_from_names(name_list):
        pairs = []
        for name in name_list:
            ex = name_to_exercise_map.get(name)
            if ex and ex.get('bName'):
                pairs.append([ex['bName'], name])
        return pairs

    prefix = []
    for tag in split_tags:
        if tag.startswith("FULLBODY"):
            # 1) 이 주차에서 허용되는 모든 이름 풀 수집
            all_allowed_for_freq = set()
            if str(freq) in allowed_names:
                for day_exercises in allowed_names[str(freq)].values():
                    all_allowed_for_freq.update(day_exercises)
            allowed_for_day = list(all_allowed_for_freq) or list(name_to_exercise_map.keys())

            # 2) 전체 enum (pairs)
            all_pairs = _pairs_from_names(allowed_for_day)

            # 3) 메인 페어들(Chest/Back/Legs)만 필터
            main_chest_pairs = []
            main_back_pairs  = []
            main_leg_pairs   = []
            for name in allowed_for_day:
                ex = name_to_exercise_map.get(name)
                if not ex: 
                    continue
                if not ex.get('main_ex'):
                    continue
                bp = (ex.get('bName') or '').strip()
                pair = [bp, name]
                if bp == 'Chest':
                    main_chest_pairs.append(pair)
                elif bp == 'Back':
                    main_back_pairs.append(pair)
                elif bp == 'Leg':
                    main_leg_pairs.append(pair)

            # 4) 방어 로직: 만약 특정 메인 풀이 비어있으면(레벨/도구 필터 등으로) 전체에서 해당 bName 아무거나라도 허용
            if not main_chest_pairs:
                main_chest_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                    if ex and ex.get('bName') == 'Chest' and name in allowed_for_day]
            if not main_back_pairs:
                main_back_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                   if ex and ex.get('bName') == 'Back' and name in allowed_for_day]
            if not main_leg_pairs:
                main_leg_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                  if ex and ex.get('bName') == 'Leg' and name in allowed_for_day]

            # 5) min_ex는 최소 3(메인 3칸) 보장
            min_items = max(min_ex, 3)

            # 6) prefixItems로 앞 3칸 강제, 이후 items는 전체 풀
            day_schema = {
                "type": "array",
                "description": (
                    "FULLBODY day. First 3 slots are fixed: Chest(main), Back(main), Leg(main). "
                    "All items must be distinct."
                ),
                "minItems": min_items,
                "maxItems": min_items,
                "prefixItems": [
                    {"enum": main_chest_pairs},
                    {"enum": main_back_pairs},
                    {"enum": main_leg_pairs}
                ],
                "items": {"enum": all_pairs}
            }
        else:
            # (기존 분할 로직 유지)
            try:
                allowed_for_day = allowed_names[str(freq)][tag]
            except Exception:
                allowed_for_day = allowed_names.get(tag, [])

            if not allowed_for_day:
                if str(freq) in allowed_names:
                    all_names = [v for v_list in allowed_names[str(freq)].values() for v in v_list]
                    allowed_for_day = list(dict.fromkeys(all_names))
                else:
                    allowed_for_day = list(name_to_exercise_map.keys())

            if tag in ("LEGS", "LOWER") and ENABLE_LEG_MAIN_CONSTRAINT:
                day_schema = make_legs_day_schema_by_name(
                    freq=freq, tag=tag, allowed_names=allowed_names,
                    min_ex=min_ex, max_ex=max_ex, level=level
                )
            else:
                day_schema = make_day_schema_pairs_by_name(allowed_for_day, min_ex, max_ex)

        prefix.append(day_schema)

    return {
        "type": "object",
        "required": ["days"],
        "properties": {
            "days": {
                "type": "array",
                "minItems": len(prefix),
                "maxItems": len(prefix),
                "prefixItems": prefix,
                "items": False
            }
        }
    }



def _allowed_pairs_for_day_by_name(freq, tag, allowed_names):
    try:
        names = list(dict.fromkeys(allowed_names[str(freq)][tag]))
    except Exception:
        names = list(dict.fromkeys(allowed_names.get(tag, [])))
    
    pairs = []
    for ex_name in names:
        exercise = name_to_exercise_map.get(ex_name)
        if exercise and exercise.get('bName'):
            pairs.append([exercise.get('bName'), ex_name])
    return pairs

def post_validate_and_fix_week(obj, freq=None, split_tags=None, allowed_names=None, level='Intermediate', duration=60, prevent_weekly_duplicates=True, prevent_category_duplicates=True):
    if not isinstance(obj, dict) or "days" not in obj: return obj

    level_schema = EXERCISE_COUNT_SCHEMA.get(level, EXERCISE_COUNT_SCHEMA['Intermediate'])
    duration_key = min(level_schema.keys(), key=lambda k: abs(k - duration) if k <= duration else float('inf'))
    min_ex, max_ex = level_schema[duration_key]

    weekly_used_names = set()
    final_days = []

    for day_idx, day_exercises in enumerate(obj.get("days", [])):
        # 1. Basic structural fix for the day
        current_day_fixed = []
        temp_used_names = set()
        if isinstance(day_exercises, list):
            for pair in day_exercises:
                if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair)):
                    continue
                bp, ex_name = pair
                bp_clean = bp.replace(" (main)", "").strip()
                exercise = name_to_exercise_map.get(ex_name)
                if not exercise or ex_name in temp_used_names:
                    continue
                
                cat_bp = exercise.get('bName') or bp_clean
                current_day_fixed.append([cat_bp, ex_name])
                temp_used_names.add(ex_name)

        # 2. Enforce main exercises for full-body (if applicable)
        tag = split_tags[day_idx % len(split_tags)]
        if tag.startswith("FULLBODY"):
            body_parts_to_check = {
                "Chest": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Chest' and ex.get('main_ex')],
                "Back": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Back' and ex.get('main_ex')],
                "Leg": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Leg' and ex.get('main_ex')]
            }
            day_names = {p[1] for p in current_day_fixed}

            for bp, main_exercises in body_parts_to_check.items():
                has_main = any(ex_name in day_names for ex_name in main_exercises)
                if not has_main:
                    replacement_main_ex = next((ex for ex in main_exercises if ex not in day_names and ex not in weekly_used_names), None)
                    if not replacement_main_ex: continue

                    replace_idx = -1
                    for i, (p_bp, p_name) in enumerate(current_day_fixed):
                        p_info = name_to_exercise_map.get(p_name, {})
                        if p_info.get('bName') == bp and not p_info.get('main_ex'):
                            replace_idx = i
                            break
                    if replace_idx == -1:
                        for i in range(len(current_day_fixed) - 1, -1, -1):
                            if not name_to_exercise_map.get(current_day_fixed[i][1], {}).get('main_ex'):
                                replace_idx = i
                                break
                    if replace_idx == -1 and current_day_fixed: replace_idx = len(current_day_fixed) - 1

                    if replace_idx != -1:
                        original_to_replace = current_day_fixed[replace_idx]
                        app.logger.info(f"[MainEx Fix] Day {day_idx+1}: Swapping '{original_to_replace[1]}' with '{replacement_main_ex}' for {bp}")
                        current_day_fixed[replace_idx] = [bp, replacement_main_ex]
                        day_names = {p[1] for p in current_day_fixed} # Refresh names

        # 3. Enforce weekly uniqueness (if enabled)
        if prevent_weekly_duplicates:
            deduped_day = []
            for bp, name in current_day_fixed:
                if name in weekly_used_names:
                    original_ex_info = name_to_exercise_map.get(name, {})
                    is_main = original_ex_info.get('main_ex', False)
                    
                    candidates = [cand_name for cand_name, cand_ex in name_to_exercise_map.items() if 
                                  cand_ex.get('bName') == bp and 
                                  cand_ex.get('main_ex', False) == is_main and 
                                  cand_name not in weekly_used_names and 
                                   cand_name not in {p[1] for p in deduped_day}]
                    
                    if candidates:
                        replacement = random.choice(candidates)
                        deduped_day.append([bp, replacement])
                        app.logger.info(f"[De-Dupe] Day {day_idx+1}: Swapping duplicate '{name}' with '{replacement}'")
                    else:
                        deduped_day.append([bp, name]) # No alternative found
                else:
                    deduped_day.append([bp, name])
            current_day_fixed = deduped_day

        # 4. Enforce category uniqueness per day (if enabled)
        if prevent_category_duplicates:
            categories_used_today = set()
            category_deduped_day = []
            
            # Get allowed names for the current day's tag
            current_day_allowed_names = []
            try:
                current_day_allowed_names = allowed_names[str(freq)][tag]
            except KeyError:
                app.logger.warning(f"No allowed_names found for freq {freq}, tag {tag}. Falling back to all exercises.")
                current_day_allowed_names = list(name_to_exercise_map.keys())

            for bp, name in current_day_fixed:
                exercise_info = name_to_exercise_map.get(name, {})
                category = exercise_info.get('category')

                if category and category != '(Uncategorized)' and category in categories_used_today:
                    app.logger.info(f"[Category De-Dupe] Day {day_idx+1}: Category '{category}' for '{name}' already used. Attempting replacement.")
                    
                    # Find replacement candidates (Strict: same body part)
                    strict_candidates = []
                    for cand_name in current_day_allowed_names:
                        cand_ex_info = name_to_exercise_map.get(cand_name, {})
                        cand_category = cand_ex_info.get('category')
                        cand_bp = cand_ex_info.get('bName')

                        if (cand_bp == bp and # Strict: same body part
                            cand_category and cand_category != '(Uncategorized)' and cand_category not in categories_used_today and
                            (not prevent_weekly_duplicates or cand_name not in weekly_used_names) and
                            cand_name not in {p[1] for p in category_deduped_day} and
                            cand_name != name):
                            strict_candidates.append(cand_name)
                    
                    candidates = strict_candidates

                    if not candidates:
                        # Relaxed search: any exercise from allowed_names for the day
                        relaxed_candidates = []
                        for cand_name in current_day_allowed_names:
                            cand_ex_info = name_to_exercise_map.get(cand_name, {})
                            cand_category = cand_ex_info.get('category')

                            if (cand_category and cand_category != '(Uncategorized)' and cand_category not in categories_used_today and
                                (not prevent_weekly_duplicates or cand_name not in weekly_used_names) and
                                cand_name not in {p[1] for p in category_deduped_day} and
                                cand_name != name):
                                relaxed_candidates.append(cand_name)
                        candidates = relaxed_candidates
                    
                    if candidates:
                        replacement = random.choice(candidates)
                        category_deduped_day.append([bp, replacement])
                        categories_used_today.add(name_to_exercise_map.get(replacement, {}).get('category'))
                        if prevent_weekly_duplicates:
                            weekly_used_names.add(replacement)
                        app.logger.info(f"[Category De-Dupe] Day {day_idx+1}: Swapped '{name}' (Category: {category}) with '{replacement}' (Category: {name_to_exercise_map.get(replacement, {}).get('category')})")
                    else:
                        category_deduped_day.append([bp, name]) # No suitable replacement, keep original
                        categories_used_today.add(category)
                        app.logger.warning(f"[Category De-Dupe] Day {day_idx+1}: No suitable replacement found for '{name}' (Category: {category}). Keeping original.")
                else:
                    category_deduped_day.append([bp, name])
                    if category:
                        categories_used_today.add(category)
            current_day_fixed = category_deduped_day

        # Update weekly used names with the final list for the day
        for _, name in current_day_fixed:
            weekly_used_names.add(name)
        
        final_days.append(current_day_fixed)

    return {"days": final_days}


# --- API Endpoints ---
@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    if not exercise_catalog: return jsonify({"error": "Exercise catalog not found or failed to load."}), 500
    return jsonify(exercise_catalog)

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt_api():
    data = request.get_json()
    if not data: return jsonify({"error": "Missing request body"}), 400
    try:
        user, min_ex, max_ex = get_user_config(data)
        duration_str = str(data.get('duration', '60'))

        with open("web/allowed_name_200.json", "r", encoding="utf-8") as f:
            ALLOWED_NAMES = json.load(f)

        # === Level-based filtering for prompt generation ===
        if user.level == 'Beginner':
            level_key = 'MBeginner' if user.gender == 'M' else 'FBeginner'
            level_specific_set = set(ALLOWED_NAMES.get(level_key, []))
        elif user.level == 'Novice':
            level_key = 'MNovice' if user.gender == 'M' else 'FNovice'
            level_specific_set = set(ALLOWED_NAMES.get(level_key, []))
        else:
            level_specific_set = None

        if level_specific_set is not None:
            MODIFIED_ALLOWED_NAMES = json.loads(json.dumps(ALLOWED_NAMES))
            if str(user.freq) in MODIFIED_ALLOWED_NAMES:
                for tag in MODIFIED_ALLOWED_NAMES[str(user.freq)]:
                    original_exercises = MODIFIED_ALLOWED_NAMES[str(user.freq)][tag]
                    intersected_exercises = list(level_specific_set.intersection(original_exercises))
                    if not intersected_exercises:
                        freq_union = [ex for t, ex_list in MODIFIED_ALLOWED_NAMES[str(user.freq)].items() if t != tag for ex in ex_list]
                        safe_intersection = list(level_specific_set.intersection(freq_union))
                        intersected_exercises = safe_intersection if safe_intersection else list(level_specific_set)
                    MODIFIED_ALLOWED_NAMES[str(user.freq)][tag] = intersected_exercises
            effective_allowed_names = MODIFIED_ALLOWED_NAMES
        else:
            effective_allowed_names = ALLOWED_NAMES
        # =================================================

        split_id = data.get('split_id', 'SPLIT')
        split_options = SPLIT_CONFIGS.get(str(user.freq), [])
        split_config = next((c for c in split_options if c['id'] == split_id), None)

        if not split_config:
            return jsonify({"error": f"Invalid split_id '{split_id}' for frequency {user.freq}"}), 400

        prompt = build_prompt(user, exercise_catalog, duration_str, min_ex, max_ex, split_config, allowed_names=effective_allowed_names)
        return jsonify({"prompt": prompt})
    except Exception as e:
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

def _prepare_allowed_names(user: User, allowed_names: dict) -> dict:
    """Filters the allowed names based on user's tools and level."""
    final_allowed_names = json.loads(json.dumps(allowed_names)) # Start with a deep copy

    # 1. Filter by selected tools
    if user.tools:
        selected_tools_set = {t.lower() for t in user.tools}
        pullupbar_exercises = set(allowed_names.get("TOOL", {}).get("PullUpBar", [])) # Use original allowed_names for pullupbar_exercises

        # Iterate through final_allowed_names to filter
        for key, value in final_allowed_names.items():
            if isinstance(value, list):
                new_list = []
                for name in value:
                    exercise_info = name_to_exercise_map.get(name, {})
                    tool_en = exercise_info.get('tool_en', '').lower()
                    is_pullupbar_exercise = name in pullupbar_exercises

                    include = False
                    if is_pullupbar_exercise:
                        if "pullupbar" in selected_tools_set:
                            include = True
                    else:
                        if tool_en in selected_tools_set:
                            include = True
                    
                    if include:
                        new_list.append(name)
                final_allowed_names[key] = new_list
            elif isinstance(value, dict):
                for sub_key, sub_list in value.items():
                    new_sub_list = []
                    for name in sub_list:
                        exercise_info = name_to_exercise_map.get(name, {})
                        tool_en = exercise_info.get('tool_en', '').lower() # Corrected: use exercise_info
                        is_pullupbar_exercise = name in pullupbar_exercises

                        include = False
                        if is_pullupbar_exercise:
                            if "pullupbar" in selected_tools_set:
                                include = True
                        else:
                            if tool_en in selected_tools_set:
                                include = True

                        if include:
                            new_sub_list.append(name)
                    
                    if not new_sub_list and sub_key not in ['ETC']:
                        app.logger.warning(f"Empty exercise list for freq {key}, day {sub_key} after tool filtering. Falling back to unfiltered list.")
                        new_sub_list = allowed_names.get(key, {}).get(sub_key, []) # Fallback should use original allowed_names
                    
                    final_allowed_names[key][sub_key] = new_sub_list

    # 2. Filter by level (Beginner/Novice)
    if user.level in ['Beginner', 'Novice']:
        level_key = ('MBeginner' if user.gender == 'M' else 'FBeginner') if user.level == 'Beginner' else ('MNovice' if user.gender == 'M' else 'FNovice')
        level_exercise_set = set(allowed_names.get(level_key, [])) # Use original allowed_names for level_exercise_set
        
        if str(user.freq) in final_allowed_names:
            for tag in final_allowed_names[str(user.freq)]:
                original_exercises = final_allowed_names[str(user.freq)][tag]
                intersected = list(level_exercise_set.intersection(original_exercises))
                
                if not intersected:
                    freq_union = [ex for t, ex_list in allowed_names[str(user.freq)].items() if t != tag for ex in ex_list] # Fallback uses original allowed_names
                    safe_intersection = list(level_exercise_set.intersection(freq_union))
                    intersected = safe_intersection if safe_intersection else list(level_exercise_set)
                
                final_allowed_names[str(user.freq)][tag] = intersected
        
        # Also filter the top-level 'ABS' list if it exists
        if 'ABS' in final_allowed_names:
            final_allowed_names['ABS'] = list(level_exercise_set.intersection(final_allowed_names['ABS']))

    return final_allowed_names

def process_inference_request(data, client_creator):
    if not data: return jsonify({"error": "Missing request body"}), 400
    try:
        user, min_ex, max_ex = get_user_config(data)
        prompt = data.get('prompt')
        prevent_weekly_duplicates = data.get('prevent_weekly_duplicates', True)
        # prevent_category_duplicates = data.get('prevent_category_duplicates', True) # Removed: always calculate both

        with open("web/allowed_name_200.json", "r", encoding="utf-8") as f:
            ALLOWED_NAMES = json.load(f)

        split_id = data.get('split_id', 'SPLIT')

        if not prompt:
            duration_str = str(data.get('duration', '60'))
            split_options = SPLIT_CONFIGS.get(str(user.freq), [])
            split_config = next((c for c in split_options if c['id'] == split_id), None)
            if not split_config:
                return jsonify({"error": f"Invalid split_id '{split_id}' for frequency {user.freq}"}), 400
            prompt = build_prompt(user, exercise_catalog, duration_str, min_ex, max_ex, split_config, allowed_names=ALLOWED_NAMES)
        
        split_options = SPLIT_CONFIGS.get(str(user.freq), [])
        split_config = next((c for c in split_options if c['id'] == split_id), None)
        if not split_config:
            return jsonify({"error": f"Invalid split_id '{split_id}' for frequency {user.freq}"}), 400
        split_tags = split_config['days']
        
        effective_allowed_names = _prepare_allowed_names(user, ALLOWED_NAMES)
        
        week_schema = build_week_schema_by_name(user.freq, split_tags, effective_allowed_names, min_ex, max_ex, level=user.level)
    
        client, model_name, completer = client_creator()
        
        resp = completer(prompt=prompt, week_schema=week_schema, max_tokens=int(data.get("max_tokens", 4096)), temperature=float(data.get("temperature", 1.0)))
        raw = getattr(resp.choices[0].message, "content", None) or ""
        
        obj = json.loads(json_repair_str(raw))
        if "days" not in obj: return jsonify({"error": "Parsed object missing 'days'."}), 502
        
        # --- Post-processing for unprocessed version (only weekly duplicates, no category prevention) ---
        unprocessed_obj = post_validate_and_fix_week(
            json.loads(json.dumps(obj)), # Deep copy to avoid modifying original
            freq=user.freq, 
            split_tags=split_tags, 
            allowed_names=effective_allowed_names, 
            level=user.level, 
            duration=user.duration, 
            prevent_weekly_duplicates=prevent_weekly_duplicates,
            prevent_category_duplicates=False # Always False for unprocessed
        )
        summary_unprocessed_unsorted = format_new_routine(unprocessed_obj, name_to_korean_map, enable_sorting=False, show_b_name=True)
        summary_unprocessed_sorted = format_new_routine(unprocessed_obj, name_to_korean_map, enable_sorting=True, show_b_name=True)

        # --- Post-processing for processed version (with category prevention) ---
        processed_obj = post_validate_and_fix_week(
            json.loads(json.dumps(obj)), # Deep copy again for processed version
            freq=user.freq, 
            split_tags=split_tags, 
            allowed_names=effective_allowed_names, 
            level=user.level, 
            duration=user.duration, 
            prevent_weekly_duplicates=prevent_weekly_duplicates,
            prevent_category_duplicates=True # Always True for processed
        )
        summary_processed_unsorted = format_new_routine(processed_obj, name_to_korean_map, enable_sorting=False, show_b_name=True)
        summary_processed_sorted = format_new_routine(processed_obj, name_to_korean_map, enable_sorting=True, show_b_name=True)
        
        formatted_summary = {
            "unprocessed": {
                "unsorted": summary_unprocessed_unsorted,
                "sorted": summary_unprocessed_sorted,
                "initial_routine": unprocessed_obj # Return the object for detail generation
            },
            "processed": {
                "unsorted": summary_processed_unsorted,
                "sorted": summary_processed_sorted,
                "initial_routine": processed_obj # Return the object for detail generation
            }
        }
        
        return jsonify({"response": raw, "result": processed_obj, "formatted_summary": formatted_summary})
    except Exception as e:
        app.logger.error(f"Error in process_inference_request: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/infer', methods=['POST'])
def infer_vllm_api():
    def vllm_client_creator():
        client = OpenAI(base_url=VLLM_BASE_URL, api_key="token-1234")
        def completer(prompt, week_schema, max_tokens, temperature):
            return client.chat.completions.create(
                model=VLLM_MODEL, 
                messages=[{"role": "user", "content": prompt}], 
                temperature=1.0,
                presence_penalty=0.2,
                frequency_penalty=0.2,
                max_tokens=max_tokens, 
                extra_body={
                    "guided_json": week_schema,
                    "repetition_penalty": 1.2,
                    "top_p": 0.9,
                    # "top_k": 50
                }
            )
        return client, VLLM_MODEL, completer
    return process_inference_request(request.get_json(), vllm_client_creator)

@app.route('/api/generate-openai', methods=['POST'])
def infer_openai_api():
    if not OPENAI_API_KEY: return jsonify({"error": "OPENAI_API_KEY not set."}), 500
    def openai_client_creator():
        client = OpenAI(api_key=OPENAI_API_KEY)
        def completer(prompt, week_schema, max_tokens, temperature):
            return client.chat.completions.create(
                model=OPENAI_MODEL, 
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature, 
                response_format={"type": "json_object"}
            )
        return client, OPENAI_MODEL, completer
    return process_inference_request(request.get_json(), openai_client_creator)

@app.route('/api/generate-details-prompt', methods=['POST'])
def generate_details_prompt_api():
    data = request.get_json()
    if not data: return jsonify({"error": "Missing request body"}), 400

    try:
        user_config = data.get('user_config', {})
        initial_routine = data.get('initial_routine', {"days": []})
        
        user, _, _ = get_user_config(user_config)

        all_exercises_for_prompt = []
        for day_exercises in initial_routine.get("days", []):
            for bp, e_name in day_exercises:
                exercise_details = name_to_exercise_map.get(e_name)
                if exercise_details:
                    tool = exercise_details.get('tool_en', 'Etc')
                    all_exercises_for_prompt.append({"ename": e_name, "tool": tool})
        
        if not all_exercises_for_prompt:
            return jsonify({"prompt": "No exercises found in the initial routine to generate a details prompt."})

        prompt = detail_prompt_abstract.format(
            gender="male" if user.gender == "M" else "female",
            weight=int(round(user.weight)),
            level=user.level,
            intensity=user.intensity,
            exercise_list_with_einfotype_json=json.dumps(all_exercises_for_prompt, ensure_ascii=False)
        )
        
        return jsonify({"prompt": prompt})

    except Exception as e:
        app.logger.error(f"Error in generate_details_prompt_api: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def _post_process_detailed_day(detailed_day: list) -> list:
    if not isinstance(detailed_day, list):
        app.logger.warning(f"_post_process_detailed_day received non-list input: {detailed_day}. Returning empty list.")
        return []

    cleaned_day = []
    # 이제 detailed_day는 [ [ename, [set]], [ename, [set]], ... ] 형태의 리스트입니다.
    for exercise_array in detailed_day:
        # exercise_array는 [ename, [reps, weight, time], ...] 형태
        if not isinstance(exercise_array, list) or len(exercise_array) < 2:
            app.logger.warning(f"Skipping invalid exercise array item: {exercise_array}")
            continue

        ename = exercise_array[0]
        set_arrays = exercise_array[1:]

        e_info_type = name_to_einfotype_map.get(ename)
        if e_info_type is None:
            app.logger.warning(f"eInfoType not found for {ename}, skipping.")
            continue

        cleaned_set_details = []
        for set_item_arr in set_arrays:
            if not isinstance(set_item_arr, list) or len(set_item_arr) != 3:
                app.logger.warning(f"Skipping invalid set array for {ename}: {set_item_arr}")
                continue
            
            # 배열에서 순서대로 reps, weight, time 추출
            reps, weight, time = set_item_arr

            cleaned_set = {"reps": 0, "weight": 0, "time": 0}

            if e_info_type == 1: # Time-based
                cleaned_set["time"] = time
            elif e_info_type == 2: # Rep-based
                cleaned_set["reps"] = reps
            elif e_info_type == 5: # Weight + Time-based
                cleaned_set["weight"] = weight
                cleaned_set["time"] = time
            elif e_info_type == 6: # Weight + Rep-based
                cleaned_set["weight"] = weight
                cleaned_set["reps"] = reps
            
            # reps가 정수가 아닐 경우를 대비한 방어 코드
            if not isinstance(cleaned_set["reps"], int):
                try:
                    cleaned_set["reps"] = int(float(str(cleaned_set["reps"]).split('-')[0].strip()))
                except (ValueError, TypeError):
                    cleaned_set["reps"] = 0
            
            cleaned_set_details.append(cleaned_set)
        
        # 최종적으로는 원래 사용하던 안정적인 객체 형태로 변환
        cleaned_exercise = {
            "ename": ename,
            "set_details": cleaned_set_details
        }
        cleaned_day.append(cleaned_exercise)
        
    return cleaned_day

def _detailed_completer(prompt, max_tokens, temperature, client, model_name, extra_body: dict = None, response_format: dict = None):
    args = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_body:
        args["extra_body"] = extra_body
    if response_format:
        args["response_format"] = response_format
        
    return client.chat.completions.create(**args)

@app.route('/api/generate-details', methods=['POST'])
def generate_details_api():
    data = request.get_json()
    if not data: return jsonify({"error": "Missing request body"}), 400

    try:
        user_config = data.get('user_config', {})
        initial_routine = data.get('initial_routine', {"days": []})
        
        user, _, _ = get_user_config(user_config) # Re-parse user for consistency
        model_used = data.get('model_used', 'openai') # Default to openai if not specified

        # Consolidate all exercises for the entire week into a single list for the prompt
        all_exercises_for_prompt = []
        for day_exercises in initial_routine["days"]:
            for bp, e_name in day_exercises:
                exercise_details = name_to_exercise_map.get(e_name)
                if exercise_details:
                    all_exercises_for_prompt.append({
                        "ename": e_name,
                        "eInfoType": exercise_details.get('eInfoType'),
                        "tool": exercise_details.get('tool_en', 'Etc')
                    })
        
        if not all_exercises_for_prompt:
            return jsonify({"days": []})

        prompt = detail_prompt_abstract.format(
            gender="male" if user.gender == "M" else "female",
            weight=int(round(user.weight)),
            level=user.level,
            intensity=user.intensity,
            exercise_list_with_einfotype_json=json.dumps(all_exercises_for_prompt, ensure_ascii=False)
        )
        detail_week_schema = build_detail_week_schema(initial_routine, user.level)
        completer_args = {}
        if model_used == 'vllm':
            client = OpenAI(base_url=VLLM_BASE_URL, api_key="token-1234")
            model_name = VLLM_MODEL
            # ✅ vLLM: guided_json은 extra_body로
            resp = _detailed_completer(
                prompt,
                max_tokens=4096,
                temperature=1.0,
                client=client,
                model_name=model_name,
                extra_body={
                    "guided_json": detail_week_schema,
                    "repetition_penalty": 1.2,
                    "top_p": 0.9,
                    # "top_k": 50
                },
            )
        else: # Default to openai
            if not OPENAI_API_KEY:
                return jsonify({"error": "OPENAI_API_KEY not set for OpenAI details generation."}), 500
            client = OpenAI(api_key=OPENAI_API_KEY)
            model_name = OPENAI_MODEL
            # ✅ OpenAI: response_format은 top-level로, extra_body 비움
            resp = _detailed_completer(
                prompt,
                max_tokens=4096,
                temperature=1.0,
                client=client,
                model_name=model_name,
                extra_body=None,
                response_format={"type": "json_object"}  # 여기!!
            )
        raw_llm_output = getattr(resp.choices[0].message, "content", None) or "[]"
        
        app.logger.info(f"Raw LLM Output for entire week: {raw_llm_output}")

        # Repair and parse LLM output
        llm_parsed_week = json.loads(json_repair_str(raw_llm_output))
        
        app.logger.info(f"Parsed LLM Output for entire week: {llm_parsed_week}")

        # Format the detailed routine into a human-readable string
        formatted_string = format_new_routine(llm_parsed_week, name_to_korean_map, enable_sorting=True, show_b_name=False)

        # Return both the raw JSON and the formatted string
        return jsonify({
            "raw_json": llm_parsed_week,
            "formatted_string": formatted_string
        })

    except Exception as e:
        app.logger.error(f"Error in generate_details_api: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/debug/routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint:50s} {methods:20s} {rule.rule}")
        output.append(line)
    return "<pre>" + "\n".join(sorted(output)) + "</pre>"

if __name__ == '__main__':
    app.run(
        debug=False,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
    )
