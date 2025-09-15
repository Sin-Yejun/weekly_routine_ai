import re
from flask import Flask, jsonify, request, send_from_directory
import json
import os
import logging
import requests
import openai
from openai import OpenAI
from json_repair import repair_json as json_repair_str
from dotenv import load_dotenv
from util import User, build_prompt, format_new_routine


BODY_PART_ENUM = ["Abs","Arm","Back","Cardio","Chest","Leg","Lifting","Shoulder","etc"]

def make_day_schema_pairs(allowed_ids_for_day):
    # allowed_ids_for_day: 그 DAY에 허용되는 exercise_id 리스트 (비어있으면 안 됨)
    pair_enum = []
    seen = set()
    for ex_id in allowed_ids_for_day:
        bp = exercise_name_map.get(ex_id, {}).get('bName')
        if not bp:
            continue
        key = (bp, ex_id)
        if key in seen:
            continue
        seen.add(key)
        pair_enum.append([bp, ex_id])

    # 안전: 비어있으면 grammar 변환이 깨집니다 → 최소 한 개는 보장되도록 fallback
    if not pair_enum:
        # freq 전체/카탈로그 전체 등으로 완화해 비지 않게 만드세요.
        # 여기서는 카탈로그 전체를 fallback 예시로.
        for ex_id, v in exercise_name_map.items():
            bp = v.get('bName')
            if bp:
                pair_enum.append([bp, ex_id])

    return {
        "type": "array",               # day = [ [bp,id], ... ]
        # "minItems": 3,            # 하루 3~8개
        # "maxItems": 8,
        "items": {
            # 튜플 스키마 대신 "쌍 자체"를 enum으로 박아 교차제약 해결
            "enum": pair_enum
        }
    }

SPLITS = {
    2: ["UPPER","LOWER"],
    3: ["PUSH","PULL","LEGS"],
    4: ["CHEST","BACK","SHOULDER","LEGS"],
    5: ["CHEST","BACK","LEGS","SHOULDER","ARM"],
}

def build_week_schema_once(freq, split_tags, allowed_ids):
    prefix = []
    for tag in split_tags:
        try:
            allowed_for_day = allowed_ids[str(freq)][tag]
        except Exception:
            allowed_for_day = allowed_ids.get(tag, [])

        # 빈 enum 방지용 fallback (중요!)
        if not allowed_for_day:
            # 예: freq 전체 묶어서라도 한두 개는 채워 넣기
            if str(freq) in allowed_ids:
                all_ids = []
                for v in allowed_ids[str(freq)].values():
                    all_ids.extend(v)
                allowed_for_day = list(dict.fromkeys(all_ids))
            else:
                allowed_for_day = list(exercise_name_map.keys())

        prefix.append(make_day_schema_pairs(allowed_for_day))

    return {
        "type": "object",
        "required": ["days"],
        "additionalProperties": False,
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

# 1) allowed 풀에서 보충하는 헬퍼
def _allowed_pairs_for_day(freq, tag, allowed_ids):
    try:
        ids = list(dict.fromkeys(allowed_ids[str(freq)][tag]))
    except Exception:
        ids = list(dict.fromkeys(allowed_ids.get(tag, [])))
    pairs = []
    for ex_id in ids:
        bp = exercise_name_map.get(ex_id, {}).get('bName')
        if bp:
            pairs.append([bp, ex_id])
    return pairs

# 2) 후처리: 중복 제거 + 부족분 보충 + 8개 컷
def post_validate_and_fix_week(obj, freq=None, split_tags=None, allowed_ids=None, min_ex=3, max_ex=8):
    if not isinstance(obj, dict) or "days" not in obj:
        return obj
    def fix_day(day, day_idx):
        if not isinstance(day, list):
            day = []
        fixed, used = [], set()
        for pair in day:
            if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair)):
                continue
            bp, ex_id = pair
            cat_bp = exercise_name_map.get(ex_id, {}).get('bName') or bp
            key = (cat_bp, ex_id)
            if key in used:
                continue
            used.add(key)
            fixed.append([cat_bp, ex_id])
            if len(fixed) >= max_ex:
                break
        # 부족분 보충
        if freq and split_tags and allowed_ids and len(fixed) < min_ex:
            tag = split_tags[day_idx % len(split_tags)]
            pool = _allowed_pairs_for_day(freq, tag, allowed_ids)
            for cand_bp, cand_id in pool:
                key = (cand_bp, cand_id)
                if key in used:
                    continue
                fixed.append([cand_bp, cand_id])
                used.add(key)
                if len(fixed) >= min_ex:
                    break
        return fixed[:max_ex]
    return {"days": [fix_day(d, i) for i, d in enumerate(obj["days"]) if isinstance(d, list)]}




# --- Flask App Initialization --
app = Flask(__name__, static_folder='.', static_url_path='')
load_dotenv()
app.logger.setLevel(logging.INFO)

# --- Path Definitions --
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'processed_query_result.json')

try:
    with open("web/allowed_ids.json", "r", encoding="utf-8") as f:
        ALLOWED_IDS = json.load(f)
except Exception as e:
    app.logger.error(f"Failed to load ALLOWED_IDS from {e}")

# --- Model & API Configuration --
# 런팟 vLLM 서버 URL ()
#VLLM_BASE_URL="https://s4ie4ass0pq40x-8000.proxy.runpod.net/v1"
VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
VLLM_MODEL    = "google/gemma-3-4b-it"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

# --- Load Exercise Catalog and Name Map --
exercise_catalog = []
exercise_name_map = {}
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
except (FileNotFoundError, json.JSONDecodeError) as e:
    app.logger.error(f"Critical: Could not load or parse exercise catalog at {EXERCISE_CATALOG_PATH}: {e}")

# --- Load Korean Name Map for Formatting --
korean_name_map = {}
KOREAN_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'query_result.json')
try:
    with open(KOREAN_CATALOG_PATH, 'r', encoding='utf-8') as f:
        korean_exercise_catalog = json.load(f)
        for exercise in korean_exercise_catalog:
            e_text_id = exercise.get('eTextId')
            if e_text_id:
                korean_name_map[e_text_id] = {
                    'bName': exercise.get('bName'),
                    'eName': exercise.get('eName')
                }
except Exception as e:
    app.logger.error(f"FATAL: Could not load Korean exercise catalog from {KOREAN_CATALOG_PATH}. The application cannot continue. Error: {e}")
    raise

# --- API Endpoints --

@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """Provides the full list of available exercises."""
    if not exercise_catalog:
        return jsonify({"error": "Exercise catalog not found or failed to load."} ), 500
    return jsonify(exercise_catalog)

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt_api():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    try:
        user = User(
            gender=data.get('gender', 'M'),
            weight=float(data.get('weight', 70)),
            level=data.get('level', 'Intermediate'),
            freq=int(data.get('freq', 3)),
            duration=int(data.get('duration', 60)),
            intensity=data.get('intensity', 'Normal')
        )
        prompt = build_prompt(user, exercise_catalog)
        return jsonify({"prompt": prompt})
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in prompt generation: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


def process_inference_request(data, client_creator):
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    try:
        # 1) prompt
        prompt = data.get('prompt')
        user = None
        if not prompt:
            user = User(
                gender=data.get('gender', 'M'),
                weight=float(data.get('weight', 70)),
                level=data.get('level', 'Beginner'),
                freq=int(data.get('freq', 4)),
                duration=int(data.get('duration', 60)),
                intensity=data.get('intensity', 'Normal')
            )
            prompt = build_prompt(user, exercise_catalog)

        # 2) 주간 분할
        freq = int(data.get('freq', 4))
        if freq not in {2,3,4,5}:
            return jsonify({"error":"Unsupported weekly frequency. Use 2/3/4/5."}), 400
        split_tags = SPLITS[freq]

        # 3) 요일별 허용 ID 스키마
        if not ALLOWED_IDS:
            return jsonify({"error":"ALLOWED_IDS not loaded. Please provide data/allowed_ids.json"}), 500
        week_schema = build_week_schema_once(freq, split_tags, ALLOWED_IDS)

        # 4) 모델 호출
        client, model_name = client_creator()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            extra_body={"guided_json": week_schema, "repetition_penalty": 1.15},
            max_tokens=int(data.get("max_tokens", 4096))
        )
        raw = resp.choices[0].message.content

        # 5) 파싱
        try:
            if raw.lstrip().startswith("{"):
                obj = json.loads(raw)
            else:
                m = re.search(r'\{\s*"days"\s*:\s*\[.*?\]\s*\}', raw, re.DOTALL)
                obj = json.loads(m.group(0)) if m else {"days":[]}
        except Exception:
            repaired_str = json_repair_str(raw)        # ← 문자열(JSON) 반환
            obj = json.loads(repaired_str)             # ← 여기서 표준 json으로 파싱
            if not isinstance(obj, dict):
                return jsonify({"error":"Failed to parse model JSON.", "response": raw}), 502

        if "days" not in obj:
            return jsonify({"error":"Parsed object missing 'days'.", "response": raw}), 502

        # 6) 후처리(라벨 보정/중복 제거 등)
        obj = post_validate_and_fix_week(obj, freq=freq, split_tags=split_tags, allowed_ids=ALLOWED_IDS, min_ex=3, max_ex=8)

        formatted_summary = format_new_routine(obj, exercise_name_map)
        return jsonify({"response": raw, "result": obj, "formatted_summary": formatted_summary})

    except Exception as e:
        app.logger.error(f"Error in process_inference_request: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/infer', methods=['POST'])
def infer_vllm_api():
    """Calls the vLLM server."""
    def vllm_client_creator():
        client = OpenAI(base_url=VLLM_BASE_URL, api_key="token-1234")
        return client, VLLM_MODEL
    return process_inference_request(request.get_json(), vllm_client_creator)


@app.route('/api/generate-openai', methods=['POST'])
def infer_openai_api():
    """Calls the OpenAI API (gpt-5-nano via Responses API)."""
    if not OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY environment variable not set."}), 500

    def openai_client_creator():
        client = OpenAI(api_key=OPENAI_API_KEY)
        model_name = OPENAI_MODEL
        return client, model_name

    return process_inference_request(request.get_json(), openai_client_creator)


if __name__ == '__main__':
    app.run(
        debug=False,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
    )
