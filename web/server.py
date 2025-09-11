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
VLLM_BASE_URL="https://s4ie4ass0pq40x-8000.proxy.runpod.net/v1"
#VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
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

def process_inference_request(data, client_creator):
    """
    Generic inference processing for both vLLM and OpenAI.
    """
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    try:
        # 1. & 2. Build the prompt or get it from the request
        prompt = data.get('prompt')
        if not prompt:
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
        client, model_name = client_creator()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=float(data.get("temperature", 0.1)),
            max_tokens=int(data.get("max_tokens", 4096))
        )
        raw_response_text = resp.choices[0].message.content
        app.logger.info(f"Raw model output received (len={len(raw_response_text)}).")

        # 4. Post-process the response
        formatted_summary = "Could not parse or format the model output."
        repaired_json_obj = None
        try:
            # A more robust way to find the JSON object
            match = re.search(r'{\s*(\"days\"|\'days\')\s*:.+}', raw_response_text, re.DOTALL)
            if match:
                json_string = match.group(0)
                repaired_json_obj = repair_json(json_string, return_objects=True)
                if isinstance(repaired_json_obj, list) and repaired_json_obj:
                    repaired_json_obj = repaired_json_obj[0]

                if isinstance(repaired_json_obj, dict) and "days" in repaired_json_obj:
                     formatted_summary = format_new_routine(repaired_json_obj, exercise_name_map)
                else:
                    app.logger.error(f"Repaired JSON is not a valid routine object: {repaired_json_obj}")
            else:
                app.logger.error(f"Could not find a JSON object in the raw output: {raw_response_text}")
        except Exception as e:
            app.logger.error(f"Error during response post-processing: {e}", exc_info=True)

        return jsonify({
            "response": raw_response_text,
            "formatted_summary": formatted_summary,
            "prompt": prompt # Return the generated prompt for debugging
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


@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt_api():
    """Generates just the prompt based on user data."""
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
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
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
    """Calls the OpenAI API."""
    if not OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY environment variable not set."} ), 500
        
    def openai_client_creator():
        client = OpenAI(api_key=OPENAI_API_KEY)
        model_name = OPENAI_MODEL or "gpt-4o-mini"
        return client, model_name
    return process_inference_request(request.get_json(), openai_client_creator)


if __name__ == '__main__':
    app.run(
        debug=False,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
    )
