import re
from flask import Flask, jsonify, request, send_from_directory
import json
import os
import logging

import openai
from openai import OpenAI
from json_repair import repair_json as json_repair_str
from dotenv import load_dotenv
from util import User, build_prompt, format_new_routine

# --- Flask App Initialization --
app = Flask(__name__, static_folder='.', static_url_path='')
load_dotenv()
app.logger.setLevel(logging.INFO)

# --- Path Definitions --
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'processed_query_result_filtered.json')

# --- Load Exercise Catalog and Name Maps --
exercise_catalog = []
name_to_exercise_map = {}
name_to_korean_map = {}
try:
    with open(EXERCISE_CATALOG_PATH, 'r', encoding='utf-8') as f:
        exercise_catalog = json.load(f)
        for exercise in exercise_catalog:
            e_name = exercise.get('eName')
            if e_name:
                name_to_exercise_map[e_name] = exercise
                name_to_korean_map[e_name] = {
                    'bName': exercise.get('bName'),
                    'kName': exercise.get('kName'),
                    'MG_num': exercise.get('MG_num'),
                    'musle_point_sum': exercise.get('musle_point_sum'),
                }
except (FileNotFoundError, json.JSONDecodeError) as e:
    app.logger.error(f"CRITICAL: Could not load exercise catalog at {EXERCISE_CATALOG_PATH}: {e}")

# --- Global Variables & Helper Functions ---
BODY_PART_ENUM = ["Abs","Arm","Back","Cardio","Chest","Leg","Lifting","Shoulder","etc"]
SPLITS = {
    2: ["UPPER","LOWER"],
    3: ["PUSH","PULL","LEGS"],
    4: ["CHEST","BACK","SHOULDER","LEGS"],
    5: ["CHEST","BACK","LEGS","SHOULDER","ARM"],
}
VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
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

def make_day_schema_pairs_by_name(allowed_names_for_day, min_ex, max_ex):
    pair_enum = []
    seen = set()
    for ex_name in allowed_names_for_day:
        exercise = name_to_exercise_map.get(ex_name)
        if not exercise: continue
        bp = exercise.get('bName')
        if not bp: continue
        
        key = (bp, ex_name)
        if key in seen: continue
        seen.add(key)
        pair_enum.append([bp, ex_name])
        
    if not pair_enum:
        for ex_name, exercise in name_to_exercise_map.items():
            bp = exercise.get('bName')
            if bp: pair_enum.append([bp, ex_name])
            
    return {
        "type": "array",
        "description": "All items must be distinct: each exercise_name appears only once per day. Arrange them in an effective order (compound → accessories) appropriate to the user’s level.",
        "minItems": min_ex,
        "maxItems": max_ex,
        "items": {"enum": pair_enum},
    }

def build_week_schema_by_name(freq, split_tags, allowed_names, min_ex, max_ex):
    prefix = []
    for tag in split_tags:
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
        
        prefix.append(make_day_schema_pairs_by_name(allowed_for_day, min_ex, max_ex))
    return {"type": "object", "required": ["days"], "properties": {"days": {"type": "array", "minItems": len(prefix), "maxItems": len(prefix), "prefixItems": prefix, "items": False}}}

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

def post_validate_and_fix_week(obj, freq=None, split_tags=None, allowed_names=None, level='Intermediate', duration=60):
    if not isinstance(obj, dict) or "days" not in obj: return obj

    level_schema = EXERCISE_COUNT_SCHEMA.get(level, EXERCISE_COUNT_SCHEMA['Intermediate'])
    duration_key = min(level_schema.keys(), key=lambda k: abs(k - duration) if k <= duration else float('inf'))
    min_ex, max_ex = level_schema[duration_key]

    legs_main_names = set(allowed_names.get('LEGS_MAIN', []))

    modified_allowed_names = json.loads(json.dumps(allowed_names)) # Deep copy
    for freq_key in ['2', '3', '4', '5']:
        if freq_key in modified_allowed_names:
            if 'LOWER' in modified_allowed_names[freq_key]:
                modified_allowed_names[freq_key]['LOWER'] = [name for name in modified_allowed_names[freq_key]['LOWER'] if name not in legs_main_names]
            if 'LEGS' in modified_allowed_names[freq_key]:
                modified_allowed_names[freq_key]['LEGS'] = [name for name in modified_allowed_names[freq_key]['LEGS'] if name not in legs_main_names]

    def fix_day(day, day_idx):
        if not isinstance(day, list): day = []
        fixed, used = [], set()
        for pair in day:
            if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair)): continue
            bp, ex_name = pair
            
            exercise = name_to_exercise_map.get(ex_name)
            if not exercise: continue
            
            cat_bp = exercise.get('bName') or bp
            key = (cat_bp, ex_name)
            if key in used: continue
            used.add(key)
            fixed.append([cat_bp, ex_name])
            if len(fixed) >= max_ex: break
        
        tag = split_tags[day_idx % len(split_tags)]
        is_legs_day = tag in ["LEGS", "LOWER"]

        if is_legs_day:
            max_legs_main = 1 if level in ['Beginner', 'Novice', 'Intermediate'] else 2
            
            current_main_legs = [p for p in fixed if p[1] in legs_main_names]
            current_other_legs = [p for p in fixed if p[1] not in legs_main_names]

            if len(current_main_legs) > max_legs_main:
                current_main_legs = current_main_legs[:max_legs_main]
            
            fixed = current_main_legs + current_other_legs
            used = {tuple(p) for p in fixed}

            if len(fixed) < min_ex:
                main_leg_pool = [[name_to_exercise_map.get(name, {}).get('bName', 'Leg'), name] for name in legs_main_names]
                other_leg_pool = _allowed_pairs_for_day_by_name(freq, tag, modified_allowed_names)

                needed_main = max_legs_main - len(current_main_legs)
                for cand_bp, cand_name in main_leg_pool:
                    if needed_main <= 0 or len(fixed) >= max_ex: break
                    if (cand_bp, cand_name) not in used:
                        fixed.append([cand_bp, cand_name])
                        used.add((cand_bp, cand_name))
                        needed_main -= 1
                
                for cand_bp, cand_name in other_leg_pool:
                    if len(fixed) >= min_ex or len(fixed) >= max_ex: break
                    if (cand_bp, cand_name) not in used:
                        fixed.append([cand_bp, cand_name])
                        used.add((cand_bp, cand_name))

        elif freq and split_tags and allowed_names and len(fixed) < min_ex:
            pool = _allowed_pairs_for_day_by_name(freq, tag, allowed_names)
            for cand_bp, cand_name in pool:
                if (cand_bp, cand_name) in used: continue
                fixed.append([cand_bp, cand_name])
                used.add((cand_bp, cand_name))
                if len(fixed) >= min_ex: break
                
        return fixed[:max_ex]

    return {"days": [fix_day(d, i) for i, d in enumerate(obj.get("days", [])) if isinstance(d, list)]}


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
        duration_str = str(data.get('duration', '60'))
        numeric_duration = int(re.sub(r'[^0-9]', '', duration_str) or '60')
        user = User(gender=data.get('gender', 'M'), weight=float(data.get('weight', 70)), level=data.get('level', 'Intermediate'), freq=int(data.get('freq', 3)), duration=numeric_duration, intensity=data.get('intensity', 'Normal'))
        
        level_schema = EXERCISE_COUNT_SCHEMA.get(user.level, EXERCISE_COUNT_SCHEMA['Intermediate'])
        duration_key = min(level_schema.keys(), key=lambda k: abs(k - user.duration) if k <= user.duration else float('inf'))
        min_ex, max_ex = level_schema[duration_key]

        prompt = build_prompt(user, exercise_catalog, duration_str, min_ex, max_ex)
        return jsonify({"prompt": prompt})
    except Exception as e:
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

def process_inference_request(data, client_creator):
    if not data: return jsonify({"error": "Missing request body"}), 400
    try:
        prompt = data.get('prompt')
        
        duration_str = str(data.get('duration', '60'))
        numeric_duration = int(re.sub(r'[^0-9]', '', duration_str) or '60')

        user = User(
            gender=data.get('gender', 'M'), 
            weight=float(data.get('weight', 70)), 
            level=data.get('level', 'Intermediate'), 
            freq=int(data.get('freq', 3)), 
            duration=numeric_duration, 
            intensity=data.get('intensity', 'Normal')
        )

        if not prompt:
            prompt = build_prompt(user, exercise_catalog, duration_str)
        
        if user.freq not in SPLITS: return jsonify({"error": f"Unsupported weekly frequency: {user.freq}. Use 2, 3, 4, or 5."}), 400
        split_tags = SPLITS[user.freq]
        
        # Calculate min/max exercises based on user level and duration for the schema
        level_schema = EXERCISE_COUNT_SCHEMA.get(user.level, EXERCISE_COUNT_SCHEMA['Intermediate'])
        duration_key = min(level_schema.keys(), key=lambda k: abs(k - user.duration) if k <= user.duration else float('inf'))
        min_ex, max_ex = level_schema[duration_key]

        with open("web/allowed_name_229.json", "r", encoding="utf-8") as f:
            ALLOWED_NAMES = json.load(f)

        week_schema = build_week_schema_by_name(user.freq, split_tags, ALLOWED_NAMES, min_ex, max_ex)
        client, model_name, completer = client_creator()
        
        resp = completer(prompt=prompt, week_schema=week_schema, max_tokens=int(data.get("max_tokens", 4096)), temperature=float(data.get("temperature", 1.0)))
        raw = getattr(resp.choices[0].message, "content", None) or ""
        
        obj = json.loads(json_repair_str(raw))
        if "days" not in obj: return jsonify({"error": "Parsed object missing 'days'."}), 502
        
        obj = post_validate_and_fix_week(obj, freq=user.freq, split_tags=split_tags, allowed_names=ALLOWED_NAMES, level=user.level, duration=user.duration)
        
        summary_unsorted = format_new_routine(obj, name_to_korean_map, enable_sorting=False)
        summary_sorted = format_new_routine(obj, name_to_korean_map, enable_sorting=True)
        
        formatted_summary = {
            "unsorted": summary_unsorted,
            "sorted": summary_sorted
        }
        
        return jsonify({"response": raw, "result": obj, "formatted_summary": formatted_summary})
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
                temperature=0.1, 
                max_tokens=max_tokens, 
                extra_body={"guided_json": 
                            week_schema, "repetition_penalty": 1.3,
                            "presence_penalty": 0.3,
                            "frequency_penalty": 0.4 
                            })
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
                response_format={"type": "json_object"})
        return client, OPENAI_MODEL, completer
    return process_inference_request(request.get_json(), openai_client_creator)

if __name__ == '__main__':
    app.run(
        debug=False,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
    )