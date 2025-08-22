from flask import Flask, jsonify, request, send_from_directory
import json
import os
import pandas as pd
import random

# --- Flask App Initialization --
# Serve static files from the 'web' directory
app = Flask(__name__, static_folder='.', static_url_path='')

# --- Path Definitions ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
USER_HISTORY_DIR = os.path.join(DATA_DIR, '01_raw', 'user_workout_history')
PARQUET_USER_PATH = os.path.join(DATA_DIR, '02_processed', 'parquet', 'user_v2.parquet')
EXERCISE_CATALOG_PATH = os.path.join(DATA_DIR, '03_core_assets', 'multilingual-pack', 'post_process_en_from_ai_list.json')

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

def compress_sets(sets: list) -> str:
    out = []
    if not sets:
        return ""
    for s in sets:
        if not isinstance(s, dict): continue
        reps, weight, time = s.get("reps"), s.get("weight"), s.get("time")
        if time and time > 0:
            out.append(f"{time}s")
            continue
        w_disp = int(weight) if weight is not None and isinstance(weight, (int, float)) and float(weight).is_integer() else weight
        base = f"{reps}"
        if w_disp is not None and w_disp != 0:
            base += f"x{w_disp}"
        out.append(base)
    return " / ".join(out)

def summarize_user_history(workout_days: list) -> str:
    texts = []
    for idx, day in enumerate(workout_days, 1):
        duration = day.get('duration')
        duration_str = f" (Duration: {duration}min)" if duration else ""
        header = f"[Workout #{idx}{duration_str}]"
        lines = [header]
        if "session_data" in day and day["session_data"]:
            for ex in day["session_data"]:
                # 다양한 케이스 허용
                e_text_id = (ex.get('eTextId') or ex.get('e_text_id') or
                             ex.get('eName') or ex.get('e_name') or 'N/A')
                sets_data = ex.get('sets') or []
                if not sets_data:
                    continue
                num_sets = len(sets_data)
                compressed_sets_str = compress_sets(sets_data)
                line = f"- {e_text_id}: {num_sets}sets: {compressed_sets_str}"
                lines.append(line)
        if len(lines) > 1:
            texts.append("\n".join(lines))
    return "\n\n".join(texts)


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

        e_text_id = str(e_text_id).replace('"', '\"')
        b_text_id = str(b_text_id).replace('"', '\"')
        e_name = str(e_name).replace('"', '\"')

        compact_catalog_list.append(
            f'["{e_text_id}", "{b_text_id}", {e_info_type}, "{e_name}"]'
        )

    exercise_list_text = "\n".join(compact_catalog_list)
    example_output = '[[60, [["BB_BSQT", [[80,10,0], [90,8,0]]]]]]'

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
- **Structure**: Ensure balanced muscle group distribution. Allow for rest days. Align routine with user's `Workout Type` (e.g., strength vs. bodybuilding).

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
        
        # TODO: Filter users based on history file length in a future step
        users = user_df[['id', 'gender', 'level']].to_dict(orient='records')
        
        return jsonify(users)
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
    """Generates a finetuning prompt and the ideal output based on provided data."""
    data = request.get_json()
    if not data or 'userInfo' not in data or 'workoutHistory' not in data or 'exerciseCatalog' not in data:
        return jsonify({"error": "Missing required data: userInfo, workoutHistory, or exerciseCatalog."} ), 400

    try:
        user_info = data['userInfo']
        workout_history = data['workoutHistory']
        exercise_catalog = data['exerciseCatalog']

        user_info_txt, frequency = format_user_info(user_info)

        # Split history into what's used for the prompt and what's used for the target output
        # The most recent `frequency` sessions are the target output
        output_sessions = workout_history[:frequency]
        history_for_summary = workout_history[frequency:]

        # Generate the summary text for the prompt from the older history
        history_summary_txt = summarize_user_history(history_for_summary)
        
        # Generate the prompt
        final_prompt = create_final_prompt(user_info_txt, history_summary_txt, frequency, exercise_catalog)

        # Generate the target output array from the most recent sessions
        output_array = dehydrate_to_array(output_sessions)

        return jsonify({
            "prompt": final_prompt,
            "output": json.dumps(output_array, indent=2, ensure_ascii=False) # Use dumps for nice formatting
        })

    except Exception as e:
        # It's helpful to log the exception for debugging
        app.logger.error(f"Error in generate_prompt_api: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"} ), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
