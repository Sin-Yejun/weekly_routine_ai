import re
import json
import os
import logging
import random
from typing import Dict, List, Tuple, Optional

import openai
from openai import OpenAI, AsyncOpenAI
from json_repair import repair_json as json_repair_str
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .util import build_prompt, SPLIT_CONFIGS, M_ratio_weight, F_ratio_weight, User as UtilUser # Alias User to avoid conflict

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Weekly Routine AI",
    description="AI-powered weekly workout routine generator using VLLM or OpenAI.",
    version="1.0.0",
)

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger = logging.getLogger("uvicorn") # Use uvicorn's logger

# Load environment variables
load_dotenv()

# --- Path Definitions ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'processed_query_result_200.json')

# --- Load Exercise Catalog and Name Maps ---
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
    # Exit or raise an exception if catalog is critical for app function
    raise RuntimeError(f"Failed to load exercise catalog: {e}")

# --- Global Variables & Helper Functions ---

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

# --- Pydantic Models for Request Bodies ---
class UserConfig(BaseModel):
    gender: str = Field(..., description="User's gender (M/F)")
    weight: float = Field(..., gt=0, description="User's weight in kg")
    level: str = Field(..., description="User's training level (Beginner, Novice, Intermediate, Advanced, Elite)")
    freq: int = Field(..., ge=2, le=5, description="Weekly workout frequency (2-5 days)")
    duration: int = Field(..., ge=30, description="Workout duration in minutes")
    intensity: str = Field(..., description="Workout intensity (Low, Normal, High)")
    split_id: str = Field("SPLIT", description="Type of workout split (e.g., SPLIT, FB)")
    tools: List[str] = Field([], description="List of allowed exercise tools (e.g., Barbell, Dumbbell)")
    prevent_weekly_duplicates: bool = Field(True, description="Prevent duplicate exercises across the week")
    prevent_category_duplicates: bool = Field(True, description="Prevent duplicate categories within a day")
    max_tokens: int = Field(4096, gt=0, description="Maximum tokens for AI model response")
    temperature: float = Field(1.0, ge=0.0, le=2.0, description="Temperature for AI model generation")
    prompt: Optional[str] = Field(None, description="Optional pre-generated prompt string")

# --- Helper Functions (adapted from server.py) ---

def get_user_config_from_model(config: UserConfig) -> Tuple[UtilUser, int, int]:
    """Extracts user configuration from Pydantic model, creates a UtilUser object, and determines exercise counts."""
    
    # Convert Pydantic UserConfig to util.User
    user = UtilUser(
        gender=config.gender,
        weight=config.weight,
        level=config.level,
        freq=config.freq,
        duration=config.duration,
        intensity=config.intensity,
        tools=config.tools
    )
    
    level_schema = EXERCISE_COUNT_SCHEMA.get(user.level, EXERCISE_COUNT_SCHEMA['Intermediate'])
    duration_key = min(level_schema.keys(), key=lambda k: abs(k - user.duration) if k <= user.duration else float('inf'))
    min_ex, max_ex = level_schema[duration_key]
    
    return user, min_ex, max_ex

def make_arm_abs_day_schema_by_name(allowed_names, min_ex, max_ex):
    arm_names = allowed_names.get('ARM', [])
    abs_names = allowed_names.get('ABS', [])

    def _create_pairs(exercise_names):
        pairs = []
        seen = set()
        for ex_name in exercise_names:
            exercise = name_to_exercise_map.get(ex_name)
            if not exercise or not exercise.get('bName'):
                continue
            key = (exercise.get('bName'), ex_name)
            if key in seen:
                continue
            pairs.append([exercise.get('bName'), ex_name])
            seen.add(key)
        return pairs

    arm_pairs = _create_pairs(arm_names)
    abs_pairs = _create_pairs(abs_names)

    if not arm_pairs or not abs_pairs:
        return make_day_schema_pairs_by_name(arm_names + abs_names, min_ex, max_ex)

    num_arm = min_ex // 2
    num_abs = min_ex - num_arm

    prefix_items = []
    for _ in range(num_arm):
        prefix_items.append({"enum": arm_pairs})
    for _ in range(num_abs):
        prefix_items.append({"enum": abs_pairs})
    
    random.shuffle(prefix_items)

    return {
        "type": "array",
        "description": f"A list of exercises for ARM+ABS day. It MUST contain {num_arm} ARM exercises and {num_abs} ABS exercises. All items must be distinct.",
        "minItems": min_ex,
        "maxItems": min_ex,
        "prefixItems": prefix_items,
        "items": False
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
            all_body_part_keys = ['CHEST', 'BACK', 'SHOULDERS', 'LEGS', 'ARM', 'ABS', 'CARDIO', 'ETC']
            all_fullbody_exercises = set()
            for key in all_body_part_keys:
                if key in allowed_names and isinstance(allowed_names[key], list):
                    all_fullbody_exercises.update(allowed_names[key])
            
            allowed_for_day = list(all_fullbody_exercises)
            if not allowed_for_day:
                app.logger.warning("No exercises found in top-level body part lists. Falling back to all exercises.")
                allowed_for_day = list(name_to_exercise_map.keys())

            all_pairs = _pairs_from_names(allowed_for_day)

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

            if not main_leg_pairs:
                main_leg_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                if ex and ex.get('bName') == 'Leg' and name in allowed_for_day]
            if not main_back_pairs:
                main_back_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                if ex and ex.get('bName') == 'Back' and name in allowed_for_day]
            if not main_chest_pairs:
                main_chest_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                    if ex and ex.get('bName') == 'Chest' and name in allowed_for_day]

            min_items = max(min_ex, 3)

            day_schema = {
                "type": "array",
                "description": (
                    "FULLBODY day. First 3 slots are fixed: Leg(main), Chest(main), Back(main)."
                    "All items must be distinct."
                ),
                "minItems": min_items,
                "maxItems": min_items,
                "prefixItems": [
                    {"enum": main_leg_pairs},
                    {"enum": main_chest_pairs},
                    {"enum": main_back_pairs},
                ],
                "items": {"enum": all_pairs}
            }
        else:
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

            if tag == 'PUSH' and str(freq) == '3':
                all_pairs = _pairs_from_names(allowed_for_day)
                
                main_chest_pairs = []
                main_shoulder_pairs = []
                for name in allowed_for_day:
                    ex = name_to_exercise_map.get(name)
                    if not ex or not ex.get('main_ex'):
                        continue
                    bp = (ex.get('bName') or '').strip()
                    pair = [bp, name]
                    if bp == 'Chest':
                        main_chest_pairs.append(pair)
                    elif bp == 'Shoulder':
                        main_shoulder_pairs.append(pair)

                if not main_chest_pairs:
                    main_chest_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                        if ex and ex.get('bName') == 'Chest' and ex.get('main_ex') and name in allowed_for_day]
                if not main_shoulder_pairs:
                    main_shoulder_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items()
                                        if ex and ex.get('bName') == 'Shoulder' and ex.get('main_ex') and name in allowed_for_day]

                if not main_chest_pairs:
                    main_chest_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items() if ex and ex.get('bName') == 'Chest' and ex.get('main_ex')]
                if not main_shoulder_pairs:
                    main_shoulder_pairs = [[ex.get('bName'), name] for name, ex in name_to_exercise_map.items() if ex and ex.get('bName') == 'Shoulder' and ex.get('main_ex')]

                min_items = max(min_ex, 2)

                day_schema = {
                    "type": "array",
                    "description": (
                        "PUSH day for 3-day split. It MUST contain at least one main Chest exercise and one main Shoulder exercise."
                        "All items must be distinct."
                    ),
                    "minItems": min_items,
                    "maxItems": min_items,
                    "prefixItems": [
                        {"enum": main_chest_pairs},
                        {"enum": main_shoulder_pairs},
                    ],
                    "items": {"enum": all_pairs}
                }
            elif tag == 'ARM+ABS':
                day_schema = make_arm_abs_day_schema_by_name(allowed_names, min_ex, max_ex)
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

def _prepare_allowed_names(user: UtilUser, allowed_names: dict) -> dict:
    """Filters the allowed names based on user's tools and level."""
    final_allowed_names = json.loads(json.dumps(allowed_names)) # Start with a deep copy

    # 1. Filter by selected tools
    if user.tools:
        selected_tools_set = {t.lower() for t in user.tools}
        pullupbar_exercises = set(allowed_names.get("TOOL", {}).get("PullUpBar", []))

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
                            new_sub_list.append(name)
                    
                    if not new_sub_list and sub_key not in ['ETC']:
                        app.logger.warning(f"Empty exercise list for freq {key}, day {sub_key} after tool filtering. Falling back to unfiltered list.")
                        new_sub_list = allowed_names.get(key, {}).get(sub_key, [])
                    
                    final_allowed_names[key][sub_key] = new_sub_list

    # 2. Filter by level (Intermediate/Advanced/Elite) for Bodyweight exercises
    if user.level in ['Intermediate', 'Advanced', 'Elite']:
        for key, value in final_allowed_names.items():
            # Handle nested dictionaries (like for frequencies '3', '4', '5')
            if isinstance(value, dict):
                for sub_key, sub_list in value.items():
                    if isinstance(sub_list, list):
                        filtered_list = []
                        for name in sub_list:
                            ex_details = name_to_exercise_map.get(name, {})
                            # Keep if NOT (Bodyweight AND NOT ABS)
                            if not (ex_details.get('tool_en') == 'Bodyweight' and ex_details.get('bName') != 'ABS'):
                                filtered_list.append(name)
                        final_allowed_names[key][sub_key] = filtered_list
            # Handle direct lists (like 'CHEST', 'ARM')
            elif isinstance(value, list):
                filtered_list = []
                for name in value:
                    ex_details = name_to_exercise_map.get(name, {})
                    # Keep if NOT (Bodyweight AND NOT ABS)
                    if not (ex_details.get('tool_en') == 'Bodyweight' and ex_details.get('bName') != 'ABS'):
                        filtered_list.append(name)
                final_allowed_names[key] = filtered_list

    # 3. Filter by level (Beginner/Novice)
    if user.level in ['Beginner', 'Novice']:
        level_key = ('MBeginner' if user.gender == 'M' else 'FBeginner') if user.level == 'Beginner' else ('MNovice' if user.gender == 'M' else 'FNovice')
        level_exercise_set = set(allowed_names.get(level_key, []))
        
        if str(user.freq) in final_allowed_names:
            for tag in final_allowed_names[str(user.freq)]:
                original_exercises = final_allowed_names[str(user.freq)][tag]
                intersected = list(level_exercise_set.intersection(original_exercises))
                
                if not intersected:
                    freq_union = [ex for t, ex_list in allowed_names[str(user.freq)].items() if t != tag for ex in ex_list]
                    safe_intersection = list(level_exercise_set.intersection(freq_union))
                    intersected = safe_intersection if safe_intersection else list(level_exercise_set)
                
                final_allowed_names[str(user.freq)][tag] = intersected
        
        if 'ABS' in final_allowed_names:
            final_allowed_names['ABS'] = list(level_exercise_set.intersection(final_allowed_names['ABS']))

        if 'ARM' in final_allowed_names:
            final_allowed_names['ARM'] = list(level_exercise_set.intersection(final_allowed_names['ARM']))

    return final_allowed_names

def post_validate_and_fix_week(obj, freq=None, split_tags=None, allowed_names=None, level='Intermediate', duration=60, prevent_weekly_duplicates=True, prevent_category_duplicates=True):
    if not isinstance(obj, dict) or "days" not in obj: return obj

    level_schema = EXERCISE_COUNT_SCHEMA.get(level, EXERCISE_COUNT_SCHEMA['Intermediate'])
    duration_key = min(level_schema.keys(), key=lambda k: abs(k - duration) if k <= duration else float('inf'))
    min_ex, max_ex = level_schema[duration_key]

    weekly_used_names = set()
    final_days = []

    for day_idx, day_exercises in enumerate(obj.get("days", [])):
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

        tag = split_tags[day_idx % len(split_tags)]
        if tag.startswith("FULLBODY"):
            body_parts_to_check = {
                "Leg": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Leg' and ex.get('main_ex')],
                "Chest": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Chest' and ex.get('main_ex')],
                "Back": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Back' and ex.get('main_ex')],
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
        elif tag == 'PUSH' and freq == 3:
            body_parts_to_check = {
                "Chest": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Chest' and ex.get('main_ex')],
                "Shoulder": [name for name, ex in name_to_exercise_map.items() if ex.get('bName') == 'Shoulder' and ex.get('main_ex')],
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
                        deduped_day.append([bp, name])
                else:
                    deduped_day.append([bp, name])
            current_day_fixed = deduped_day

        if prevent_category_duplicates:
            categories_used_today = set()
            category_deduped_day = []
            
            current_day_allowed_names = []
            if tag.startswith("FULLBODY"):
                all_body_part_keys = ['CHEST', 'BACK', 'SHOULDERS', 'LEGS', 'ARM', 'ABS', 'CARDIO', 'ETC']
                all_fullbody_exercises = set()
                for key in all_body_part_keys:
                    if key in allowed_names and isinstance(allowed_names[key], list):
                        all_fullbody_exercises.update(allowed_names[key])
                
                current_day_allowed_names = list(all_fullbody_exercises)
                if not current_day_allowed_names:
                    app.logger.warning("No exercises found in top-level body part lists for post-validation. Falling back.")
                    current_day_allowed_names = list(name_to_exercise_map.keys())
            else:
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
                    
                    strict_candidates = []
                    for cand_name in current_day_allowed_names:
                        cand_ex_info = name_to_exercise_map.get(cand_name, {})
                        cand_category = cand_ex_info.get('category')
                        cand_bp = cand_ex_info.get('bName')

                        if (cand_bp == bp and
                            cand_category not in categories_used_today and
                            (not prevent_weekly_duplicates or cand_name not in weekly_used_names) and
                            cand_name not in {p[1] for p in category_deduped_day} and
                            cand_name != name):
                            strict_candidates.append(cand_name)
                    
                    candidates = strict_candidates

                    if not candidates:
                        relaxed_candidates = []
                        for cand_name in current_day_allowed_names:
                            cand_ex_info = name_to_exercise_map.get(cand_name, {})
                            cand_category = cand_ex_info.get('category')

                            if (cand_category not in categories_used_today and
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
                        category_deduped_day.append([bp, name])
                        categories_used_today.add(category)
                        app.logger.warning(f"[Category De-Dupe] Day {day_idx+1}: No suitable replacement found for '{name}' (Category: {category}). Keeping original.")
                else:
                    category_deduped_day.append([bp, name])
                    if category:
                        categories_used_today.add(category)
            current_day_fixed = category_deduped_day

        for _, name in current_day_fixed:
            weekly_used_names.add(name)
        
        final_days.append(current_day_fixed)

    return {"days": final_days}

# --- API Endpoints ---

@app.get("/api/ratios", summary="Get exercise ratio weights")
async def get_ratios_api():
    return JSONResponse(content={
        "M_ratio_weight": M_ratio_weight,
        "F_ratio_weight": F_ratio_weight
    })

@app.get("/api/exercises", summary="Get full exercise catalog")
async def get_exercises_api():
    if not exercise_catalog:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Exercise catalog not found or failed to load.")
    return JSONResponse(content=exercise_catalog)

@app.post("/api/generate-prompt", summary="Generate a workout prompt based on user configuration")
async def generate_prompt_api(config: UserConfig):
    try:
        user, min_ex, max_ex = get_user_config_from_model(config)
        duration_str = str(config.duration)

        with open(os.path.join(os.path.dirname(__file__), "allowed_name_200.json"), "r", encoding="utf-8") as f:
            ALLOWED_NAMES = json.load(f)

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

        split_options = SPLIT_CONFIGS.get(str(user.freq), [])
        split_config = next((c for c in split_options if c['id'] == config.split_id), None)

        if not split_config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid split_id '{config.split_id}' for frequency {user.freq}")

        prompt = build_prompt(user, exercise_catalog, duration_str, min_ex, max_ex, split_config, allowed_names=effective_allowed_names)
        return JSONResponse(content={"prompt": prompt})
    except Exception as e:
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

async def process_inference_request(config: UserConfig, client_creator):
    user, min_ex, max_ex = get_user_config_from_model(config)
    prevent_weekly_duplicates = config.prevent_weekly_duplicates
    prevent_category_duplicates = config.prevent_category_duplicates

    with open(os.path.join(os.path.dirname(__file__), "allowed_name_200.json"), "r", encoding="utf-8") as f:
        ALLOWED_NAMES = json.load(f)

    if not config.prompt:
        duration_str = str(config.duration)
        split_options = SPLIT_CONFIGS.get(str(user.freq), [])
        split_config = next((c for c in split_options if c['id'] == config.split_id), None)
        if not split_config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid split_id '{config.split_id}' for frequency {user.freq}")
        prompt = build_prompt(user, exercise_catalog, duration_str, min_ex, max_ex, split_config, allowed_names=ALLOWED_NAMES)
    else:
        prompt = config.prompt
    
    split_options = SPLIT_CONFIGS.get(str(user.freq), [])
    split_config = next((c for c in split_options if c['id'] == config.split_id), None)
    if not split_config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid split_id '{config.split_id}' for frequency {user.freq}")
    split_tags = split_config['days']
    
    effective_allowed_names = _prepare_allowed_names(user, ALLOWED_NAMES)
    
    week_schema = build_week_schema_by_name(user.freq, split_tags, effective_allowed_names, min_ex, max_ex, level=user.level)

    client, model_name, completer = client_creator()
    
    try:
        resp = await completer(prompt=prompt, week_schema=week_schema, max_tokens=config.max_tokens, temperature=config.temperature)
        raw = getattr(resp.choices[0].message, "content", None) or ""
    except openai.APIConnectionError as e:
        app.logger.error(f"OpenAI API connection error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to connect to AI model: {e}")
    except openai.APIStatusError as e:
        app.logger.error(f"OpenAI API status error: {e.status_code} - {e.response}", exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=f"AI model API error: {e.response}")
    except Exception as e:
        app.logger.error(f"Error during AI model inference: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI model inference failed: {e}")
    
    try:
        obj = json.loads(json_repair_str(raw))
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON repair/decode error: {e}. Raw response: {raw}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI model returned invalid JSON: {e}")

    if "days" not in obj:
        app.logger.error(f"Parsed object missing 'days'. Raw response: {raw}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI model response missing 'days' key.")
    
    processed_obj = post_validate_and_fix_week(
        json.loads(json.dumps(obj)),
        freq=user.freq, 
        split_tags=split_tags, 
        allowed_names=effective_allowed_names, 
        level=user.level, 
        duration=user.duration, 
        prevent_weekly_duplicates=prevent_weekly_duplicates,
        prevent_category_duplicates=prevent_category_duplicates
    )

    enriched_days = []
    for day_exercises in processed_obj.get("days", []):
        enriched_day = []
        for bName, eName in day_exercises:
            exercise_details = name_to_exercise_map.get(eName, {})
            enriched_day.append({
                "eName": eName,
                "bName": bName,
                "kName": exercise_details.get("kName", eName),
                "MG_num": exercise_details.get("MG_num", 0),
                "musle_point_sum": exercise_details.get("musle_point_sum", 0),
                "main_ex": exercise_details.get("main_ex", False),
                "eInfoType": name_to_einfotype_map.get(eName),
                "tool_en": exercise_details.get("tool_en", "Etc")
            })
        enriched_days.append(enriched_day)

    final_response = {"days": enriched_days}
    
    return JSONResponse(content={
        "routine": final_response,
        "raw_routine": obj,
        "prompt": prompt
    })

@app.post("/api/infer", summary="Generate workout routine using vLLM")
async def infer_vllm_api(config: UserConfig):
    def vllm_client_creator():
        client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="token-1234")
        async def completer(prompt, week_schema, max_tokens, temperature):
            return await client.chat.completions.create(
                model=VLLM_MODEL, 
                messages=[{"role": "user", "content": prompt}], 
                temperature=temperature, # Use config.temperature
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
    return await process_inference_request(config, vllm_client_creator)

@app.post("/api/generate-openai", summary="Generate workout routine using OpenAI API")
async def infer_openai_api(config: UserConfig):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OPENAI_API_KEY not set in environment variables.")
    
    def openai_client_creator():
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        async def completer(prompt, week_schema, max_tokens, temperature):
            return await client.chat.completions.create(
                model=OPENAI_MODEL, 
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature, # Use config.temperature
                response_format={"type": "json_object"}
            )
        return client, OPENAI_MODEL, completer
    return await process_inference_request(config, openai_client_creator)

app.mount("/data", StaticFiles(directory=DATA_DIR, html=True), name="data")
app.mount("/", StaticFiles(directory="web", html=True), name="static")

# --- Main entry point for Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
        log_level="info"
    )
# uvicorn web.main:app --port 5001