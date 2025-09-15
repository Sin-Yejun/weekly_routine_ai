import re
from flask import Flask, jsonify, request, send_from_directory
import json
import os
import logging
import requests
import openai
from openai import OpenAI
from json_repair import loads as repair_json
from dotenv import load_dotenv
from util import User, build_prompt, format_new_routine

def get_allowed_ids(freq: int, split_name: str) -> list:
    try:
        return ALLOWED_IDS[str(freq)][split_name]
    except KeyError:
        return []

def make_anyof_branches_for_ids(allowed_ids_for_day):
    """해당 DAY에서 허용되는 id만 anyOf 분기에 매핑(T 패턴 유지)."""
    time_only_all   = {"TREADMIL","CYCLE","ROW_MACH","PLANK","CLIMB_STAIRS","ASSAULT_BIKE","BAT_ROPE","STEPMILL_MAC","ELLIP_MC","WALKING","RUNNING"}   # T=1
    reps_only_all   = {"PUSH_UP","SIT_UP","LEG_RAISE","BURPEE","AIR_SQT","JUMP_SQT","HINDU_PUSH_UP","V-UP","PULL_UP","DIPS","MOUNT_CLIMB","LUNGE","CHIN_UP","STEP_UP","INVT_ROW","HIP_THRUST","HPET","BACK_ET","CRUNCH","HEEL_TOUCH","HANG_LEG_RAIGE","ABS_ROLL_OUT","ABS_AIR_BIKE","TOES_TO_BAR","BOX_JUMP","JUMPING_JACK","HANG_KNEE_RAISE","HIGH_KNEE_SKIP","DOUBLE_UNDER","INCHWORM","CLAP_PUSH_UP","INC_PUSH_UP","BW_CALF_RAISE","PISTOL_BOX_SQT","GLUTE_BRDG","BENCH_DIPS","BW_LAT_LUNGE","KB_SM_AIR_SQT","PISTOL_SQT","Y_RAISE","DONK_KICK","DEC_SIT_UP","SEAT_KNEE_UP","DEC_PUSH_UP","DONK_CALF_RAISE","KNEE_PU"}  # T=2
    weighted_timed  = {"FARMER_WALK"}  # T=5
    # 나머지는 모두 T=6(가중치형)

    allowed = set(allowed_ids_for_day)
    time_only_ids  = sorted(list(allowed & time_only_all))
    reps_only_ids  = sorted(list(allowed & reps_only_all))
    wt_timed_ids   = sorted(list(allowed & weighted_timed))
    weighted_ids   = sorted(list(allowed - set(time_only_ids) - set(reps_only_ids) - set(wt_timed_ids)))

    branches = []
    if time_only_ids:
        branches.append({
            "type":"array",
            "prefixItems":[
                {"type":"string","enum":["Abs","Cardio","etc"]},
                {"type":"string","enum":time_only_ids},
                {
                    "type":"array",
                    "items":{
                        "type":"array",
                        "prefixItems":[{"const":0},{"const":0},{"type":"integer","minimum":300,"maximum":1800}],
                        "items":False
                    }
                }
            ],
            "items":False
        })
    if wt_timed_ids:
        branches.append({
            "type":"array",
            "prefixItems":[
                {"type":"string","enum":["Cardio"]},
                {"type":"string","enum":wt_timed_ids},
                {
                    "type":"array",
                    "items":{
                        "type":"array",
                        "prefixItems":[{"const":0},{"type":"integer","minimum":5},{"type":"integer","minimum":1}],
                        "items":False
                    }
                }
            ],
            "items":False
        })
    if reps_only_ids:
        branches.append({
            "type":"array",
            "prefixItems":[
                {"type":"string","enum":["Abs","Arm","Back","Cardio","Chest","Leg","Shoulder","etc"]},
                {"type":"string","enum":reps_only_ids},
                {
                    "type":"array",
                    "items":{
                        "type":"array",
                        "prefixItems":[{"type":"integer","minimum":1},{"const":0},{"const":0}],
                        "items":False
                    }
                }
            ],
            "items":False
        })
    if weighted_ids:
        branches.append({
            "type":"array",
            "prefixItems":[
                {"type":"string","enum":["Abs","Arm","Back","Cardio","Chest","Leg","Lifting","Shoulder","etc"]},
                {"type":"string","enum":weighted_ids},
                {
                    "type":"array",
                    "items":{
                        "type":"array",
                        "prefixItems":[{"type":"integer","minimum":1},{"type":"integer","minimum":5},{"const":0}],
                        "items":False
                    }
                }
            ],
            "items":False
        })
    return branches

def make_day_schema_for_ids(allowed_ids_for_day):
    """해당 DAY 전용 스키마(운동 항목 배열)."""
    return {
        "type":"array",              # day = [ [bp,id,sets], ... ]
        "items":{
            "anyOf": make_anyof_branches_for_ids(allowed_ids_for_day)
        }
        # (xgrammar에서 길이 강제는 약하므로 minItems/maxItems는 생략)
    }

SPLITS = {
    2: ["UPPER","LOWER"],
    3: ["PUSH","PULL","LEGS"],
    4: ["CHEST","BACK","SHOULDER","LEGS"],
    5: ["CHEST","BACK","LEGS","SHOULDER","ARM"],
}

def build_week_schema_once(freq, split_tags, allowed_ids):
    """
    주간 한 번 호출용 스키마.
    days.prefixItems = [DAY1 스키마, DAY2 스키마, ...] 로 '요일별 허용 id'를 스키마 레벨에서 강제.
    """
    prefix = []
    for tag in split_tags:
        allowed_ids_for_day = []
        try:
            allowed_ids_for_day = allowed_ids[str(freq)][tag]
        except Exception:
            # 혹시 freq 키 없이 평면 구조로 제공되었으면 폴백
            allowed_ids_for_day = allowed_ids.get(tag, [])
        prefix.append(make_day_schema_for_ids(allowed_ids_for_day))
    return {
        "type":"object",
        "properties":{
            "days":{
                "type":"array",
                "prefixItems": prefix,
                "items": False  # 일부 버전에선 거부/무시될 수 있어 제거해도 됨
            }
        },
        "required":["days"],
        "additionalProperties": False
    }
def _snap5(x):
    try:
        return int(round(int(x)/5.0)*5)
    except Exception:
        return 0

def post_validate_and_fix_week(obj):
    """
    {"days":[ day1, day2, ... ]}
    - 중복 운동 병합하지 않음(항목은 그대로 유지)
    - 각 운동 항목의 세트 수: 1~8세트로 제한 (9세트 이상이면 앞 8세트만)
    - 카디오는 하루 1종 1세트만 반영
    - T 패턴 정리 + weight 5kg 스냅
    - 총 세트 과다 컷 로직 제거
    - bodypart 라벨은 카탈로그(bName)로 강제 교정
    """
    if not isinstance(obj, dict) or "days" not in obj:
        return obj

    time_only_ids = {
        "TREADMIL","CYCLE","ROW_MACH","PLANK","CLIMB_STAIRS","ASSAULT_BIKE",
        "BAT_ROPE","STEPMILL_MAC","ELLIP_MC","WALKING","RUNNING"
    }

    def fix_day(day):
        if not isinstance(day, list):
            return []

        fixed = []
        cardio_seen = False

        for item in day:
            # item = [bp, ex_id, sets]
            if not (isinstance(item, list) and len(item) == 3 and isinstance(item[1], str) and isinstance(item[2], list)):
                continue

            # 원본 값
            bp, ex_id, sets = item[0], item[1], item[2]

            # --- 세트 정규화(T 패턴 강제) ---
            new_sets = []
            for s in sets:
                if not isinstance(s, list) or len(s) < 3:
                    continue
                # 기존 로직 유지하되 normalize
                r, w, t = s[0], s[1], s[2]
                if ex_id in time_only_ids:
                    # T=1: [0,0,time>0]
                    t = max(300, int(t) if isinstance(t, int) else 600)
                    new_sets.append([0, 0, t])
                elif ex_id == "FARMER_WALK":
                    # T=5: [0, weight>=5(5kg step), time>0]
                    w = max(5, _snap5(w))
                    t = max(60, int(t) if isinstance(t, int) else 60)
                    new_sets.append([0, w, t])
                elif ex_id in {
                    "PUSH_UP","SIT_UP","LEG_RAISE","BURPEE","AIR_SQT","JUMP_SQT","HINDU_PUSH_UP","V-UP","PULL_UP",
                    "DIPS","MOUNT_CLIMB","LUNGE","CHIN_UP","STEP_UP","INVT_ROW","HIP_THRUST","HPET","BACK_ET",
                    "CRUNCH","HEEL_TOUCH","HANG_LEG_RAIGE","ABS_ROLL_OUT","ABS_AIR_BIKE","TOES_TO_BAR","BOX_JUMP",
                    "JUMPING_JACK","HANG_KNEE_RAISE","HIGH_KNEE_SKIP","DOUBLE_UNDER","INCHWORM","CLAP_PUSH_UP",
                    "INC_PUSH_UP","BW_CALF_RAISE","PISTOL_BOX_SQT","GLUTE_BRDG","BENCH_DIPS","BW_LAT_LUNGE",
                    "KB_SM_AIR_SQT","PISTOL_SQT","Y_RAISE","DONK_KICK","DEC_SIT_UP","SEAT_KNEE_UP","DEC_PUSH_UP","DONK_CALF_RAISE","KNEE_PU"
                }:
                    # T=2: [reps>0,0,0]
                    r = max(1, int(r) if isinstance(r, int) else 10)
                    new_sets.append([r, 0, 0])
                else:
                    # T=6: [reps>0, weight>=5(5kg step), 0]
                    r = max(1, int(r) if isinstance(r, int) else 6)
                    w = max(5, _snap5(w))
                    new_sets.append([r, w, 0])

            # --- 세트 수 제한: 1~8세트 ---
            if not new_sets:
                continue
            if len(new_sets) > 8:
                new_sets = new_sets[:8]

            # --- 카디오는 하루 1종 1세트만 반영 ---
            if ex_id in time_only_ids:
                if cardio_seen:
                    # 이미 카디오가 있었으면 스킵
                    continue
                new_sets = new_sets[:1]
                cardio_seen = True

            # --- bodypart를 카탈로그(bName) 기준으로 강제 교정 ---
            try:
                # 전역에 로드된 exercise_name_map 사용 (processed_query_result.json 기반)
                cat_bp = exercise_name_map.get(ex_id, {}).get('bName')
                if cat_bp:
                    bp = cat_bp
            except Exception:
                pass

            fixed.append([bp, ex_id, new_sets])

        return fixed

    days = obj["days"]
    return {"days": [fix_day(d) for d in days]}


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
    """Generates and returns just the prompt."""
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
        # 1) prompt 문맥(네 build_prompt 재사용 가능)
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

        # 2) 주간 횟수/분할 시퀀스
        freq = int(data.get('freq', 4))
        if freq not in {2,3,4,5}:
            return jsonify({"error":"Unsupported weekly frequency. Use 2/3/4/5."}), 400
        split_tags = SPLITS[freq]

        # 3) 카탈로그 → 분할별 허용 ID 자동 생성
        if not ALLOWED_IDS:
            return jsonify({"error":"ALLOWED_IDS not loaded. Please provide data/allowed_ids.json"}), 500
        week_schema = build_week_schema_once(freq, split_tags, ALLOWED_IDS)

        # 5) 단 한 번 호출 (xgrammar). 정말 길이 강제가 필요하면 아래 extra_body에 outlines 지정 가능
        client, model_name = client_creator()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            extra_body={"guided_json": week_schema},  # {"guided_decoding_backend":"outlines"}로 교체 가능
            max_tokens=int(data.get("max_tokens", 4096))
        )
        raw = resp.choices[0].message.content

        # 6) 파싱 + 후검증/보정
        try:
            if raw.lstrip().startswith("{"):
                obj = json.loads(raw)
            else:
                m = re.search(r'\{\s*"days"\s*:\s*\[.*?\]\s*\}', raw, re.DOTALL)
                obj = json.loads(m.group(0)) if m else {"days":[]}
        except Exception:
            # 최후의 보정
            repaired = repair_json(raw, return_objects=True)
            obj = repaired[0] if isinstance(repaired, list) and repaired else repaired
            if not isinstance(obj, dict):
                return jsonify({"error":"Failed to parse model JSON.", "response": raw}), 502

        if "days" not in obj:
            return jsonify({"error":"Parsed object missing 'days'.", "response": raw}), 502

        # 7) 후처리(중복병합/라벨교정/T패턴강제)
        obj = post_validate_and_fix_week(obj)

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
