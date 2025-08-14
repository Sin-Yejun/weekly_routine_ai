import json
import os
from history_summary import get_latest_workout_texts_detail
from user_info import get_user_profile_text, get_user_frequency

def create_prompt():
    """
    Build an English prompt for weekly/daily routine generation.
    - No catalog size limit (list all available exercises).
    - Remove split recommendations and weight-notation sections.
    - Example Output follows the user's sample (no 'type' field).
    """
    # Recent workout history (last 10)
    txt_list = get_latest_workout_texts_detail(10) or []
    history_summary_txt = "\n\n".join(txt_list)

    # User info / frequency
    user_info_txt = get_user_profile_text() or ""
    frequency = get_user_frequency() or 3

    # Load available exercise catalog
    exercise_list = []
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        json_path = os.path.join(project_root, 'data/json', 'processed_query_result.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            exercise_list = json.load(f)
    except:
        pass

    exercise_list_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in exercise_list)

    example_output = '[{"session_data": [{"sets": [{"weight": 28.0, "reps": 20, "time": 0}, {"weight": 63.0, "reps": 30, "time": 0}, {"weight": 63.0, "reps": 20, "time": 0}], "bName": "Leg", "eName": "Hip Abduction Machine", "bTextId": "CAT_LEG", "eTextId": "HIP_ABD_MC"}, {"sets": [{"weight": 33.0, "reps": 20, "time": 0}, {"weight": 54.0, "reps": 25, "time": 0}, {"weight": 40.0, "reps": 15, "time": 0}, {"weight": 68.0, "reps": 20, "time": 0}, {"weight": 47.0, "reps": 15, "time": 0}, {"weight": 47.0, "reps": 15, "time": 0}], "bName": "Leg", "eName": "Leg Extension", "bTextId": "CAT_LEG", "eTextId": "LGE_EXT"}, {"sets": [{"weight": 12.0, "reps": 20, "time": 0}, {"weight": 12.0, "reps": 20, "time": 0}], "bName": "Leg", "eName": "Dumbbell Bulgarian Split Squat", "bTextId": "CAT_LEG", "eTextId": "DB_BULSPLIT_SQT"}, {"sets": [{"weight": 60.0, "reps": 5, "time": 0}, {"weight": 50.0, "reps": 15, "time": 0}], "bName": "Leg", "eName": "Back Squat", "bTextId": "CAT_LEG", "eTextId": "BB_BSQT"}], "duration": 118}, {"session_data": [{"sets": [{"weight": 11.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}, {"weight": 21.0, "reps": 15, "time": 0}, {"weight": 21.0, "reps": 15, "time": 0}], "bName": "Arm", "eName": "Cable Curl", "bTextId": "CAT_ARM", "eTextId": "CABLE_CURL"}, {"sets": [{"weight": 11.0, "reps": 20, "time": 0}, {"weight": 18.0, "reps": 10, "time": 0}, {"weight": 18.0, "reps": 12, "time": 0}, {"weight": 18.0, "reps": 12, "time": 0}], "bName": "Arm", "eName": "Cable Curl", "bTextId": "CAT_ARM", "eTextId": "CABLE_CURL"}, {"sets": [{"weight": 28.0, "reps": 20, "time": 0}, {"weight": 63.0, "reps": 10, "time": 0}, {"weight": 63.0, "reps": 15, "time": 0}, {"weight": 63.0, "reps": 15, "time": 0}, {"weight": 63.0, "reps": 15, "time": 0}], "bName": "Leg", "eName": "Hip Abduction Machine", "bTextId": "CAT_LEG", "eTextId": "HIP_ABD_MC"}], "duration": 51}, {"session_data": [{"sets": [{"weight": 32.0, "reps": 15, "time": 0}, {"weight": 41.0, "reps": 15, "time": 0}, {"weight": 50.0, "reps": 13, "time": 0}, {"weight": 45.0, "reps": 13, "time": 0}], "bName": "Chest", "eName": "Pec Deck Fly Machine", "bTextId": "CAT_CHEST", "eTextId": "PEC_DECK_MC"}, {"sets": [{"weight": 0.0, "reps": 30, "time": 0}, {"weight": 0.0, "reps": 30, "time": 0}, {"weight": 0.0, "reps": 30, "time": 0}], "bName": "Abs", "eName": "Abdominal Hip Thrust", "bTextId": "CAT_ABS", "eTextId": "ABS_HIP_THRU"}, {"sets": [{"weight": 16.0, "reps": 15, "time": 0}, {"weight": 26.0, "reps": 4, "time": 0}, {"weight": 24.0, "reps": 4, "time": 0}, {"weight": 24.0, "reps": 4, "time": 0}, {"weight": 24.0, "reps": 4, "time": 0}], "bName": "Chest", "eName": "Incline Dumbbell Bench Press", "bTextId": "CAT_CHEST", "eTextId": "DB_INC_BP"}, {"sets": [{"weight": 0.0, "reps": 12, "time": 0}, {"weight": 0.0, "reps": 12, "time": 0}, {"weight": 0.0, "reps": 12, "time": 0}, {"weight": 0.0, "reps": 12, "time": 0}], "bName": "Chest", "eName": "Dips", "bTextId": "CAT_CHEST", "eTextId": "DIPS"}, {"sets": [{"weight": 18.0, "reps": 20, "time": 0}, {"weight": 18.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}], "bName": "Arm", "eName": "Cable Push Down", "bTextId": "CAT_ARM", "eTextId": "CABLE_PUSH_DOWN"}], "duration": 50}]'


    prompt = f"""## [Task]
weekly-routine

## [User Info]
{user_info_txt}

## [Recent Workout History]
{history_summary_txt}

## Instructions
- You are an AI trainer. Generate a **personalized week-long detailed workout routine** using only the information in [User Info] and [Recent Workout History].
- Consider the user's goals, weekly frequency ({{frequency}} days), recent movement patterns, and injuries/limitations.
- **Output MUST be a valid JSON array only** (no prose, no comments, **no code fences**).
- The JSON array length **MUST equal {{frequency}}**.
- Each session object MUST include:
  - "session_data": an array of exercises (see constraints below)
  - "duration": total minutes for the session
- Each exercise object MUST include:
  - "sets": list of set objects with keys "weight" (kg), "reps" (count), "time" (seconds). Use these consistency rules based on `eInfoType`:
      * If eInfoType = 1: time > 0, reps = 0, weight = 0.0
      * If eInfoType = 2: reps > 0, time = 0, weight = 0.0
      * If eInfoType = 6: reps > 0, weight > 0, time = 0
  - "bName": one of ["Leg","Chest","Back","Shoulder","Arm","Lifting","Abs","etc","Cardio"]
  - "eName": human-readable exercise name
  - "bTextId": "CAT_<AREA>"
  - "eTextId": canonical exercise id (if not in the catalog, assign an UPPER_SNAKE_CASE id like "ABS_HIP_THRU")
- **Level gating (mandatory):**
  1) Beginner: bodyweight + machines only. No free-weight compounds, no pull-ups/muscle-ups/olympic lifts. Substitute with safe machine or assisted variants.
  2) Novice: machines as main work, free weights as accessories. Avoid high-skill movements.
  3) Intermediate: free weights as main work, machines as accessories.
  4) Advanced: specialize by chosen training type (strength focus vs. hypertrophy focus).
  5) Elite: same structure as Advanced with higher loading/volume and tighter progression.
- **Load selection**: Base loads on the user's most recent successful working set for that movement. If uncertain, start **5–10% below** the heaviest recent working set. If there is no recent record, determine working set loads considering the user’s body weight and training level.

## Available Exercise Catalog (unrestricted)
{exercise_list_text}

## Example Output (structure only; do NOT copy these numbers and do NOT include backticks in your final answer)
{example_output}

## Final Instruction
- Return **ONLY** the JSON array. Do not add any explanations.
"""
    return prompt

if __name__ == "__main__":
    prompt = create_prompt()
    print(prompt)
