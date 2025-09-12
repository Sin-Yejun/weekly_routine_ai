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

ALLOWED_IDS = {
    "UPPER": [...],
    "LOWER": [...],
    "PUSH": [...],
    "PULL": [...],
    "LEGS": [...],
    "CHEST": [...],
    "BACK": [...],
    "SHOULDER": [...],
    "ARM": [...],
    "CARDIO":[...],
    "ABS":[...]

}

# --- Flask App Initialization --
app = Flask(__name__, static_folder='.', static_url_path='')
load_dotenv()
app.logger.setLevel(logging.INFO)

# --- Path Definitions --
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '02_processed', 'processed_query_result.json')

# --- Model & API Configuration --
# 런팟 vLLM 서버 URL ()
#VLLM_BASE_URL="https://s4ie4ass0pq40x-8000.proxy.runpod.net/v1"
VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
#VLLM_BASE_URL="https://s4ie4ass0pq40x-8000.proxy.runpod.net/v1"
VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
VLLM_MODEL    = "google/gemma-3-4b-it"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

schema = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {
                            "type": "array",
                            "prefixItems": [
                                {"type": "string", "enum": ["Abs", "Cardio", "etc"]},
                                {"type": "string", "enum": [
                                    "TREADMIL", "CYCLE", "ROW_MACH", "PLANK", "CLIMB_STAIRS", "ASSAULT_BIKE",
                                    "BAT_ROPE", "STEPMILL_MAC", "ELLIP_MC", "WALKING", "RUNNING"
                                ]},
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "prefixItems": [
                                            {"const": 0},
                                            {"const": 0},
                                            {"type": "integer", "minimum": 300, "maximum": 1800}
                                        ],
                                        "items": False,
                                        "minItems": 3,
                                        "maxItems": 3
                                    },
                                    "minItems": 1,
                                    "maxItems": 1
                                }
                            ],
                            "items": False
                        },
                        {
                            "type": "array",
                            "prefixItems": [
                                {"type": "string", "enum": ["Cardio"]},
                                {"type": "string", "enum": ["FARMER_WALK"]},
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "prefixItems": [
                                            {"const": 0},
                                            {"type": "integer", "minimum": 5, "maximum": 500},
                                            {"type": "integer", "minimum": 1, "maximum": 1800}
                                        ],
                                        "items": False,
                                        "minItems": 3,
                                        "maxItems": 3
                                    }
                                }
                            ],
                            "items": False
                        },
                        {
                            "type": "array",
                            "prefixItems": [
                                {"type": "string", "enum": [
                                    "Abs", "Arm", "Back", "Cardio", "Chest", "Leg", "Shoulder", "etc"
                                ]},
                                {"type": "string", "enum": [
                                    "PUSH_UP", "SIT_UP", "LEG_RAISE", "BURPEE", "AIR_SQT", "JUMP_SQT", "HINDU_PUSH_UP",
                                    "V-UP", "PULL_UP", "DIPS", "MOUNT_CLIMB", "LUNGE", "CHIN_UP", "STEP_UP", "INVT_ROW",
                                    "HIP_THRUST", "HPET", "BACK_ET", "CRUNCH", "HEEL_TOUCH", "HANG_LEG_RAIGE", "ABS_ROLL_OUT",
                                    "ABS_AIR_BIKE", "TOES_TO_BAR", "BOX_JUMP", "JUMPING_JACK", "HANG_KNEE_RAISE", "HIGH_KNEE_SKIP",
                                    "DOUBLE_UNDER", "INCHWORM", "CLAP_PUSH_UP", "INC_PUSH_UP", "BW_CALF_RAISE", "PISTOL_BOX_SQT",
                                    "GLUTE_BRDG", "BENCH_DIPS", "BW_LAT_LUNGE", "KB_SM_AIR_SQT", "PISTOL_SQT", "Y_RAISE",
                                    "DONK_KICK", "DEC_SIT_UP", "SEAT_KNEE_UP", "DEC_PUSH_UP", "DONK_CALF_RAISE", "KNEE_PU"
                                ]},
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "prefixItems": [
                                            {"type": "integer", "minimum": 1, "maximum": 20},
                                            {"const": 0},
                                            {"const": 0}
                                        ],
                                        "items": False,
                                        "minItems": 3,
                                        "maxItems": 3
                                    },
                                    "minItems": 3,
                                    "maxItems": 10
                                }
                            ],
                            "items": False
                        },
                        {
                            "type": "array",
                            "prefixItems": [
                                {"type": "string", "enum": [
                                    "Abs", "Arm", "Back", "Cardio", "Chest", "Leg", "Lifting", "Shoulder", "etc"
                                ]},
                                {"type": "string", "enum": [
                                    "BB_BSQT", "BB_DL", "BB_FSQ", "LEG_PRESS", "LEG_CURL", "LGE_EXT", "BB_BP", "BB_INC_PRESS",
                                    "DB_BP", "DB_FLY", "CROSS_OVER", "BB_LOW", "DB_LOW", "LAT_PULL_DOWN", "BB_PRESS",
                                    "DB_SHD_PRESS", "DB_LAT_RAISE", "DB_F_RAISE", "DB_SHRUG", "BB_BC_CURL", "DB_BC_CURL",
                                    "DB_TRI_EXT", "DB_KICKBACK", "DB_WRIST_CURL", "THRUSTER", "DB_BO_LAT_RAISE", "WEI_PULL_UP",
                                    "RUS_TWIST", "PENDLAY_ROW", "MC_LOW", "WEI_DIPS", "SM_BB_DL", "EZB_CURL", "SEATED_CABLE_ROW",
                                    "CABLE_PUSH_DOWN", "INN_THIGH_MC", "GOOD_MORN", "BB_SPLIT_SQT", "DB_BULSPLIT_SQT",
                                    "DB_SPLIT_SQT", "GOBLET_SQT", "KB_GOBLET_SQT", "RM_BB_DL", "DB_LUNGE", "WEI_HIP_THRUST",
                                    "DB_INC_FLY", "DB_INC_BP", "CHEST_PRESS_MC", "PEC_DECK_MC", "INC_BP_MAC", "DB_PULLOVER",
                                    "WEI_CHIN_UP", "INC_BB_ROW", "INC_DB_ROW", "OA_DB_ROW", "WEI_HPET", "SHD_PRESS_MAC",
                                    "BB_SHRUG", "FACE_PULL", "CABLE_REV_FLY", "BB_UPRIGHT_ROW", "DB_UPRIGHT_ROW",
                                    "EZB_UPRIGHT_ROW", "DB_HAM_CURL", "CABLE_CURL", "CG_BB_BP", "BB_WRIST_CURL",
                                    "EZB_WRIST_CURL", "LYING_TRI_EXT", "DB_SIDE_BEND", "PUSH_PRESS", "KB_SWING", "WB_SHOT",
                                    "V_SQT", "REV_V_SQT", "T_BAR_ROW_MAC", "DB_PREA_CURL", "BB_PREA_CURL", "EZ_PREA_CURL",
                                    "REV_PEC_DECK_MC", "HIP_ABD_MC", "KB_SNATCH", "CABLE_CRUNCH", "ARM_CURL_MC", "SM_SQT",
                                    "HACK_SQT", "CABLE_LAT_RAISE", "ABS_CRUNCH_MC", "PAUSE_SQT", "SM_SPLIT_SQT", "SM_ROW",
                                    "CABLE_ARM_PULL_DOWN", "PAUSE_BB_ROW", "PAUSE_SM_DL", "SM_DL", "PAUSE_DL", "SM_BP",
                                    "CABLE_HAM_CURL", "SM_SHRUG", "CABLE_FRONT_RAISE", "DB_SNATCH", "SM_INC_PRESS", "BB_LUNGE",
                                    "DB_SM_SQT", "ASS_PULLUP_MC", "BB_LAT_LUNGE", "DB_DEC_FLY", "WEI_HANG_KNEE_RAISE",
                                    "ASS_DIP_MC", "BB_SPLIT_SQT_REAL", "DB_SQT", "BB_BOX_SQT", "DB_BURPEE", "BB_FLOOR_PRESS",
                                    "BB_STD_CALF_RAISE", "DB_LEG_CURL", "BB_DEC_BP", "DB_THRUSTER", "EZB_FRONT_RAISE",
                                    "STIFF_DL", "DB_REAR_LAT_RAISE", "BB_FR_LUNGE", "BB_FRONT_RAISE", "BB_HACK_SQT",
                                    "BB_JUMP_SQT", "SUMO_DEAD_HIGH", "LAT_WIDE_PULL", "HANG_CLEAN", "HANG_SNATCH",
                                    "DEC_DB_BP", "HIP_THRUST_MAC", "INC_DB_CURL", "DEC_CHEST_MAC", "INC_CABLE_FLY",
                                    "STD_CABLE_FLY", "KB_DL", "KB_SM_DL", "DB_SM_DL", "DB_LAT_LUNGE", "HZ_LEG_PRESS",
                                    "NOR_HAM_CURL", "BB_SM_SQT", "KB_SM_SQT", "SEAT_BB_SHD_PRESS", "SEAT_DB_SHD_PRESS",
                                    "PLATE_SHD_PRESS", "DB_Y_RAISE", "LOW_ROW_MC", "HIGH_ROW_MC", "WEI_DEC_SIT_UP",
                                    "DEFICIT_DL", "TURKISH_GET_UP", "INC_CHEST_PRESS_MC", "CABLE_PULL_THRU",
                                    "CABLE_BO_LAT_RAISE", "CABLE_UPRIGHT_ROW", "TORSO_ROT_MC", "RACK_PULL", "KB_SHD_PRESS",
                                    "INC_DB_SHD_PRESS", "LIN_HACK_SQT_MC", "SM_CALF_RAISE", "DB_STD_CALF_RAISE",
                                    "MID_ROW_MC", "CONCENT_CURL", "INC_BB_FR_RAISE", "INC_EZ_FRONT_RAISE",
                                    "INC_DB_FRONT_RAISE", "BB_INC_FRONT_RAISE", "EZ_INC_FRONT_RAISE", "DB_INC_FRONT_RAISE",
                                    "EZ_REVERSE_CURL", "EZ_TRI_EXT", "SEAT_DB_LAT_RAISE", "SM_BULSPLIT_SQT",
                                    "INC_DB_PULL_OVER", "DB_LYING_TRI_EXT", "EZ_LYING_TRI_EXT", "SM_HIP_THRUSTER",
                                    "PAUSED_BP", "DB_SKULL_CRUSH", "SEAT_BB_TRI_EXT", "BICEP_CURL_MC", "CHEST_FLY_MC",
                                    "DB_FRONT_SQT", "CHEST_SUP_T_ROW"
                                ]},
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "prefixItems": [
                                            {"type": "integer", "minimum": 1, "maximum": 20},
                                            {"type": "integer", "minimum": 5, "maximum": 500},
                                            {"const": 0}
                                        ],
                                        "items": False,
                                        "minItems": 3,
                                        "maxItems": 3
                                    },
                                    "minItems": 3,
                                    "maxItems": 10
                                }
                            ],
                            "items": False
                        }
                    ]
                }
            }
        }
    },
    "required": ["days"],
    "additionalProperties": False
}

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


def process_inference_request(data, client_creator, use_max_completion_tokens=False):
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    try:
        prompt = data.get('prompt')
        if not prompt:
            app.logger.info("No prompt provided, generating one from user data.")
            user = User(
                gender=data.get('gender', 'M'),
                weight=float(data.get('weight', 70)),
                level=data.get('level', 'Intermediate'),
                freq=int(data.get('freq', 3)),
                duration=int(data.get('duration', 60)),
                intensity=data.get('intensity', 'Normal')
            )
            prompt = build_prompt(user, exercise_catalog)
        
        # 3. Call the model via the provided client creator
        # app.logger.info(f"Sending prompt to model: {prompt}")
        client, model_name = client_creator()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            # extra_body={"guided_json": schema},
            max_tokens=int(data.get("max_tokens", 4096))
        )
        raw_response_text = resp.choices[0].message.content
        # app.logger.info(f"Raw model output received (len={len(raw_response_text)}).")

        # --- Post-process: JSON repair & formatting (기존 그대로) ---
        formatted_summary = raw_response_text

        return jsonify({
            "response": raw_response_text,
            "formatted_summary": formatted_summary,
            "prompt": prompt
        })

    except openai.APIStatusError as e:
        app.logger.error(f"Model API returned an error status: {e}")
        error_details = {"error": str(e)}
        try:
            error_details = e.response.json()
        except Exception:
            pass
        return jsonify({
            "response": json.dumps(error_details),
            "formatted_summary": f"Model API returned an error:\n{json.dumps(error_details, indent=2)}"
        }), e.status_code or 502
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in inference processing: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500



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

    return process_inference_request(request.get_json(), openai_client_creator, use_max_completion_tokens=False)


if __name__ == '__main__':
    app.run(
        debug=False,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
    )
