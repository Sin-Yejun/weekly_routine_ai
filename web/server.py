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
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'processed_query_result.json')

# --- Load Exercise Catalog and Name Maps --
exercise_catalog = []
exercise_name_map = {}
korean_name_map = {}
try:
    with open(EXERCISE_CATALOG_PATH, 'r', encoding='utf-8') as f:
        exercise_catalog = json.load(f)
        for exercise in exercise_catalog:
            e_text_id = exercise.get('eTextId')
            if e_text_id:
                exercise_name_map[e_text_id] = {
                    'bName': exercise.get('bName'),
                    'eName': exercise.get('eName')
                }
                korean_name_map[e_text_id] = {
                    'bName': exercise.get('bName'),
                    'eName': exercise.get('kName')
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

def make_day_schema_pairs(allowed_ids_for_day):
    pair_enum = []
    seen = set()
    for ex_id in allowed_ids_for_day:
        bp = exercise_name_map.get(ex_id, {}).get('bName')
        if not bp: continue
        key = (bp, ex_id)
        if key in seen: continue
        seen.add(key)
        pair_enum.append([bp, ex_id])
    if not pair_enum:
        for ex_id, v in exercise_name_map.items():
            bp = v.get('bName')
            if bp: pair_enum.append([bp, ex_id])
    return {"type": "array", "items": {"enum": pair_enum}}

def build_week_schema_once(freq, split_tags, allowed_ids):
    prefix = []
    for tag in split_tags:
        try:
            allowed_for_day = allowed_ids[str(freq)][tag]
        except Exception:
            allowed_for_day = allowed_ids.get(tag, [])
        if not allowed_for_day:
            if str(freq) in allowed_ids:
                all_ids = [v for v_list in allowed_ids[str(freq)].values() for v in v_list]
                allowed_for_day = list(dict.fromkeys(all_ids))
            else:
                allowed_for_day = list(exercise_name_map.keys())
        prefix.append(make_day_schema_pairs(allowed_for_day))
    return {"type": "object", "required": ["days"], "properties": {"days": {"type": "array", "minItems": len(prefix), "maxItems": len(prefix), "prefixItems": prefix, "items": False}}}

def _allowed_pairs_for_day(freq, tag, allowed_ids):
    try:
        ids = list(dict.fromkeys(allowed_ids[str(freq)][tag]))
    except Exception:
        ids = list(dict.fromkeys(allowed_ids.get(tag, [])))
    pairs = []
    for ex_id in ids:
        bp = exercise_name_map.get(ex_id, {}).get('bName')
        if bp: pairs.append([bp, ex_id])
    return pairs

def post_validate_and_fix_week(obj, freq=None, split_tags=None, allowed_ids=None, min_ex=4, max_ex=8):
    if not isinstance(obj, dict) or "days" not in obj: return obj
    def fix_day(day, day_idx):
        if not isinstance(day, list): day = []
        fixed, used = [], set()
        for pair in day:
            if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair)): continue
            bp, ex_id = pair
            cat_bp = exercise_name_map.get(ex_id, {}).get('bName') or bp
            key = (cat_bp, ex_id)
            if key in used: continue
            used.add(key)
            fixed.append([cat_bp, ex_id])
            if len(fixed) >= max_ex: break
        if freq and split_tags and allowed_ids and len(fixed) < min_ex:
            tag = split_tags[day_idx % len(split_tags)]
            pool = _allowed_pairs_for_day(freq, tag, allowed_ids)
            for cand_bp, cand_id in pool:
                key = (cand_bp, cand_id)
                if key in used: continue
                fixed.append([cand_bp, cand_id])
                used.add(key)
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
        prompt = build_prompt(user, exercise_catalog, duration_str)
        return jsonify({"prompt": prompt})
    except Exception as e:
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

def process_inference_request(data, client_creator):
    if not data: return jsonify({"error": "Missing request body"}), 400
    try:
        prompt = data.get('prompt')
        if not prompt:
            duration_str = str(data.get('duration', '60'))
            numeric_duration = int(re.sub(r'[^0-9]', '', duration_str) or '60')
            user = User(gender=data.get('gender', 'M'), weight=float(data.get('weight', 70)), level=data.get('level', 'Beginner'), freq=int(data.get('freq', 4)), duration=numeric_duration, intensity=data.get('intensity', 'Normal'))
            prompt = build_prompt(user, exercise_catalog, duration_str)
        
        freq = int(data.get('freq', 4))
        if freq not in SPLITS: return jsonify({"error": f"Unsupported weekly frequency: {freq}. Use 2, 3, 4, or 5."}), 400
        split_tags = SPLITS[freq]
        
        with open("web/allowed_ids_filtered.json", "r", encoding="utf-8") as f:
            ALLOWED_IDS = json.load(f)

        week_schema = build_week_schema_once(freq, split_tags, ALLOWED_IDS)
        client, model_name, completer = client_creator()
        
        resp = completer(prompt=prompt, week_schema=week_schema, max_tokens=int(data.get("max_tokens", 4096)), temperature=float(data.get("temperature", 1.0)))
        raw = getattr(resp.choices[0].message, "content", None) or ""
        
        obj = json.loads(json_repair_str(raw))
        if "days" not in obj: return jsonify({"error": "Parsed object missing 'days'."}), 502
        
        obj = post_validate_and_fix_week(obj, freq=freq, split_tags=split_tags, allowed_ids=ALLOWED_IDS)
        formatted_summary = format_new_routine(obj, korean_name_map)
        
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
                temperature=temperature, 
                max_tokens=max_tokens, 
                extra_body={"guided_json": 
                            week_schema, "repetition_penalty": 1.2
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
                messages=[{"role": "system", "content": "You are a helpful assistant designed to output JSON."}, 
                         {"role": "user", "content": prompt}], 
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
