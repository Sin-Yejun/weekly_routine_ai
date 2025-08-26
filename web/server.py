from flask import Flask, jsonify, request, send_from_directory
import json
import os
import pandas as pd
import random
import requests
from openai import OpenAI
from json_repair import loads as repair_json

from util import summarize_user_history, FormattingStyle

def _to_number(x):
    """Converts any numeric/string form to a number safely. Returns 0 on failure."""
    if isinstance(x, (int, float)):
        return int(x) if isinstance(x, float) and x.is_integer() else x
    if isinstance(x, str):
        s = x.strip()
        try:
            if '.' in s:
                v = float(s)
                return int(v) if v.is_integer() else v
            return int(s)
        except (ValueError, TypeError):
            m = re.search(r'-?\d+(?:\.\d+)?', s)
            if m:
                v = float(m.group(0))
                return int(v) if v.is_integer() else v
    return 0

# --- Flask App Initialization --
# Serve static files from the 'web' directory
app = Flask(__name__, static_folder='.', static_url_path='')

# --- Path Definitions ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
USER_HISTORY_DIR = os.path.join(DATA_DIR, '01_raw', 'user_workout_history')
PARQUET_USER_PATH = os.path.join(DATA_DIR, '02_processed', 'parquet', 'user_v2.parquet')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '03_core_assets', 'multilingual-pack', 'post_process_en_from_ai_list.json')
QUERY_RESULT_PATH = os.path.join(DATA_DIR, '02_processed', 'query_result.json')
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
VLLM_MODEL    = os.getenv("VLLM_MODEL", "google/gemma-3-4b-it")

# --- Load Exercise Name Map ---
exercise_name_map = {}
try:
    with open(QUERY_RESULT_PATH, 'r', encoding='utf-8') as f:
        query_result = json.load(f)
        for exercise in query_result:
            e_text_id = exercise.get('eTextId')
            if e_text_id:
                exercise_name_map[e_text_id] = {
                    'bName': exercise.get('bName'),
                    'eName': exercise.get('eName')
                }
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Warning: Could not load or parse {QUERY_RESULT_PATH}: {e}")


# --- Helper Functions from test_prompt.py ---

def format_user_info(user_info):
    gender = user_info.get('gender', 'N/A')
    weight = user_info.get('weight', 'N/A')
    level = user_info.get('level', 'N/A')
    workout_type = user_info.get('type', 'N/A')
    frequency = user_info.get('frequency', 3)

    profile_text = (
        f"- Gender: {gender}\n"
        f"- Weight: {weight}kg\n"
        f"- Workout Type: {workout_type}\n"
        f"- Training Level: {level}\n"
        f"- Weekly Workout Frequency: {frequency}"
    )
    return profile_text, frequency

def get_user_info(user_df, user_id):
    user_series = user_df[user_df["id"] == user_id]
    if user_series.empty:
        return None, None
    
    user_data = user_series.iloc[0]
    frequency = int(user_data.get('frequency', 3))
    
    profile_text = (
        f"- Gender: {user_data.get('gender', 'N/A')}\n"
        f"- Weight: {user_data.get('weight', 'N/A')}kg\n"
        f"- Workout Type: {user_data.get('type', 'N/A')}\n"
        f"- Training Level: {user_data.get('level', 'N/A')}\n"
        f"- Weekly Workout Frequency: {frequency}"
    )
    return profile_text, frequency

def create_final_prompt(user_info_txt, history_summary_txt, frequency, exercise_catalog):
    compact_catalog_list = []
    for e in exercise_catalog:
        e_text_id = e.get("e_text_id") or e.get("eTextId") or ""
        b_text_id = 'CAT_' + (e.get("b_name", "").upper() or e.get("bName", "").upper() or "")
        e_info_type = (
            e.get("eInfoType")
            if e.get("eInfoType") is not None
            else e.get("e_info_type", 0)
        )
        e_name = e.get("eName") or e.get("e_name") or ""

        e_text_id = str(e_text_id).replace('"', '"')
        b_text_id = str(b_text_id).replace('"', '"')
        e_name = str(e_name).replace('"', '"')

        compact_catalog_list.append(
            f'["{e_text_id}", "{b_text_id}", {e_info_type}, "{e_name}"]'
        )

    exercise_list_text = "\n".join(compact_catalog_list)
    example_output = '[[60, [["BB_BSQT", [[80,10,0], [90,8,0, ... ]], ... ]], ... ]'

    prompt = f"""## [Task]
Generate a weekly workout routine based on user data.

## [User Info]
{user_info_txt}

## [Recent Workout History]
{history_summary_txt}

## [Instructions]
1.  **Role**: You are an expert AI personal trainer.
2.  **Goal**: Create a detailed, week-long workout routine for the user.
3.  **Data-Driven**: Base recommendations *only* on the provided data. Use the catalog.
4.  **Output Format**: MUST be a valid JSON array of arrays (ultra-compact format), with a length of exactly {frequency}. No comments or markdown.
    - **Schema**: `[ [duration, [ [eTextId, [ [w,r,t], ... ]], ... ]], ... ]`

## [Training Principles]
- **Level Gating**:
  - **Beginner**: Mainly bodyweight exercises, assisted by machines. Avoid complex free-weights.
  - **Novice**: Mainly machines for strength, assisted by basic free-weights.
  - **Intermediate**: Mainly free-weights for strength, assisted by machines.
  - **Advanced**: Design routine based on `Workout Type` with higher specificity and detail.
  - **Elite**: More advanced and higher intensity routines than Advanced, using heavy weights.
- **Progression**: Apply progressive overload. Slightly increase weight (~2.5-5%) or reps (+1-2) from the last relevant workout. For new exercises, estimate a conservative starting weight.
- **Structure**: Ensure balanced muscle group distribution. Allow for rest days. Align routine with user\'s `Workout Type` (e.g., strength vs. bodybuilding).

## [Available Exercise Catalog]
[
{exercise_list_text}
]

## [Example Output] (Structural guide ONLY. Do NOT copy values.)
{example_output}

## [Final Instruction]
Return **ONLY** the generated JSON array.
"""
    return prompt

def dehydrate_to_array(full_routine):
    """Converts a full routine to an ultra-compact array format."""
    ultra_compact_routine = []
    if not isinstance(full_routine, list):
        return ultra_compact_routine
        
    for session in full_routine:
        exercises_array = []
        if session.get("session_data"):
            for exercise in session.get("session_data", []):
                sets_array = []
                if exercise.get("sets"):
                    for s in exercise.get("sets", []):
                        sets_array.append([s.get("weight", 0), s.get("reps", 0), s.get("time", 0)])
                exercises_array.append([exercise.get("eTextId") or exercise.get("e_text_id"), sets_array])
        session_array = [session.get("duration"), exercises_array]
        ultra_compact_routine.append(session_array)
    return ultra_compact_routine


def group_and_hydrate(repaired_json):
    """
    불완전/중첩 JSON 안에서 [duration, [exercises]] 세션을 모두 수집하되,
    '탐지 방식'이 달라 생기는 중복만 제거하고 실제로 같은 내용의 '다른 날'은 유지.
    """
    # 잘못 한 번 더 감싼 경우 풀기
    if isinstance(repaired_json, list) and len(repaired_json) == 1 and isinstance(repaired_json[0], list):
        repaired_json = repaired_json[0]

    sessions_by_origin = {}  # origin_key -> [duration, exercises]
    order = []

    def walk(node):
        if not isinstance(node, list):
            return

        # 1) 정확한 페어: [duration, [exercises]]
        if len(node) == 2 and isinstance(node[0], (int, float)) and isinstance(node[1], list):
            origin = f"exact:{id(node)}"  # 이 리스트 객체 자체가 오리진
            if origin not in sessions_by_origin:
                sessions_by_origin[origin] = [node[0], node[1]]
                order.append(origin)
            # 하위에 또 세션이 숨어 있을 수 있으니 계속 탐색
            for el in node:
                walk(el)
            return  # 이 노드에서는 분리형 탐지는 중복 유발하므로 스킵

        # 2) 분리형: 같은 리스트 안에서 ... duration, [exercises], ...
        for i in range(len(node) - 1):
            if isinstance(node[i], (int, float)) and isinstance(node[i + 1], list):
                origin = f"adj:{id(node)}:{i}"  # 같은 부모 리스트의 i 위치에서 발견
                if origin not in sessions_by_origin:
                    sessions_by_origin[origin] = [node[i], node[i + 1]]
                    order.append(origin)

        # 3) 더 깊이
        for el in node:
            walk(el)

    walk(repaired_json)

    # 오리진 기준으로만 중복 제거된(=탐지중복만 제거된) 세션들을 순서대로 반환
    unique_in_order = [sessions_by_origin[k] for k in order]
    return hydrate_from_array(unique_in_order)


def hydrate_from_array(compact_routine):
    """Converts an ultra-compact array format back to a full routine structure."""
    full_routine = []
    if not isinstance(compact_routine, list):
        return full_routine

    # 어떤 깊이의 중첩된 리스트에서도 [w,r,t] 형태의 세트 리스트를 추출하는 내부 함수
    def _find_and_parse_sets(data_block):
        # data_block이 [w,r,t] 형태인지 확인
        if isinstance(data_block, list) and len(data_block) == 3:
            # 리스트의 요소들이 숫자로 직접 변환 가능한지 확인 (즉, [w,r,t] 형태의 실제 세트인지)
            if all(not isinstance(x, (list, dict)) for x in data_block):
                try:
                    w, r, t = _to_number(data_block[0]), _to_number(data_block[1]), _to_number(data_block[2])
                    if r >= 0:
                        yield {"weight": w, "reps": r, "time": t}
                        return # 성공적으로 파싱했으면 더 깊이 들어가지 않음
                except (TypeError, ValueError):
                    pass # 숫자로 변환 실패 시, 하위 리스트로 간주하고 계속 진행

        # 리스트인 경우 (그리고 위에서 실제 세트로 처리되지 않았다면), 하위 요소들을 재귀적으로 탐색
        if isinstance(data_block, list):
            for item in data_block:
                yield from _find_and_parse_sets(item)

    for session_array in compact_routine:
        if not isinstance(session_array, list) or len(session_array) != 2:
            continue

        duration, exercises_array = session_array
        session_data = []
        if isinstance(exercises_array, list):
            for exercise_array in exercises_array:
                if not isinstance(exercise_array, list) or len(exercise_array) < 1:
                    continue

                e_text_id = exercise_array[0]
                # eTextId 이후의 모든 요소를 세트 데이터 후보로 간주
                raw_set_data_blocks = exercise_array[1:]

                sets_data = []
                for block in raw_set_data_blocks:
                    sets_data.extend(list(_find_and_parse_sets(block)))

                session_data.append({"eTextId": e_text_id, "sets": sets_data})

        full_routine.append({"duration": duration, "session_data": session_data})
    return full_routine



# --- API Endpoints ---

@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/api/users', methods=['GET'])
def get_users():
    """Provides a list of users, eventually filtered by data availability."""
    try:
        if not os.path.exists(PARQUET_USER_PATH):
            return jsonify({"error": "User data file not found."} ), 404
            
        user_df = pd.read_parquet(PARQUET_USER_PATH)
        
        # Return all relevant user fields for the UI
        user_columns = ['id', 'gender', 'level', 'weight', 'type', 'frequency']
        # Ensure all columns exist, fill missing with a default if necessary
        for col in user_columns:
            if col not in user_df.columns:
                user_df[col] = None # or a suitable default

        # Safely convert pandas DataFrame to list of dicts, avoiding numpy type issues
        users_json_str = user_df[user_columns].to_json(orient='records')
        users = json.loads(users_json_str)
        
        # Return only the first 10 users for a cleaner UI
        return jsonify(users[:10])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>/history', methods=['GET'])
def get_user_history(user_id):
    """Provides the workout history for a specific user."""
    try:
        history_file_path = os.path.join(USER_HISTORY_DIR, f'{user_id}.json')
        if not os.path.exists(history_file_path):
            return jsonify({"error": "User history not found."} ), 404
            
        with open(history_file_path, "r", encoding="utf-8") as f:
            history_data = json.load(f)
        
        return jsonify(history_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """Provides the full list of available exercises."""
    try:
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f:
            exercise_catalog = json.load(f)
        return jsonify(exercise_catalog)
    except FileNotFoundError:
        return jsonify({"error": "Exercise catalog not found."} ), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt_api():
    """Generates a finetuning prompt based on provided data."""
    data = request.get_json()
    if not data or 'userInfo' not in data or 'workoutHistory' not in data or 'exerciseCatalog' not in data:
        return jsonify({"error": "Missing required data: userInfo, workoutHistory, or exerciseCatalog."} ), 400

    try:
        user_info = data['userInfo']
        workout_history = data['workoutHistory']
        exercise_catalog = data['exerciseCatalog']

        user_info_txt, frequency = format_user_info(user_info)

        history_summary_txt = summarize_user_history(workout_history, exercise_name_map, FormattingStyle.HISTORY_SUMMARY)
        
        final_prompt = create_final_prompt(user_info_txt, history_summary_txt, frequency, exercise_catalog)

        return jsonify({
            "prompt": final_prompt,
            "output": "" 
        })

    except Exception as e:
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"} ), 500


@app.route('/api/infer', methods=['POST'])
def infer_api():
    """
    Body: { "prompt": "<string>", "temperature": 0.0, "max_tokens": 1024 }
    Calls the vLLM server, gets a routine, and returns both the raw
    JSON and a human-readable formatted summary.
    """
    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    try:
        client = OpenAI(base_url=VLLM_BASE_URL, api_key="token-1234")

        resp = client.chat.completions.create(
            model=VLLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=float(data.get("temperature", 0.0)),
            max_tokens=int(data.get("max_tokens", 2048)),
        )
        
        raw_response_text = resp.choices[0].message.content

        app.logger.info(f"Raw model output to be processed: {raw_response_text}")
        formatted_summary = "Could not parse or format the model output."
        try:
            first_bracket = raw_response_text.find('[')
            last_bracket = raw_response_text.rfind(']')
            
            if first_bracket != -1 and last_bracket != -1:
                json_string = raw_response_text[first_bracket:last_bracket+1]
                
                repaired_json = repair_json(json_string)
                
                hydrated_routine = group_and_hydrate(repaired_json)

                formatted_summary = summarize_user_history(hydrated_routine, exercise_name_map, FormattingStyle.FORMATTED_ROUTINE)
            else:
                app.logger.error(f"Could not find JSON array in raw output: {raw_response_text}")
        except Exception as e:
            app.logger.error(f"Error during post-processing: {e}", exc_info=True)

        return jsonify({
            "response": raw_response_text,
            "formatted_summary": formatted_summary
        })

    except Exception as e:
        app.logger.error(f"Error calling vLLM server: {e}", exc_info=True)
        return jsonify({"error": f"Failed to reach or process response from vLLM server: {e}"}), 502

if __name__ == '__main__':
    app.run(
        debug=False,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5001")),
    )