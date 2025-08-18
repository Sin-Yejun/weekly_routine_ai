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
        json_path = 'data/02_processed/processed_query_result.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            exercise_list = json.load(f)
    except:
        pass

    exercise_list_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in exercise_list)

    example_output = '[{"session_data": [{"sets": [{"weight": 28.0, "reps": 20, "time": 0}, {"weight": 63.0, "reps": 30, "time": 0}, {"weight": 63.0, "reps": 20, "time": 0}], "bName": "Leg", "eName": "Hip Abduction Machine", "bTextId": "CAT_LEG", "eTextId": "HIP_ABD_MC"}, {"sets": [{"weight": 33.0, "reps": 20, "time": 0}, {"weight": 54.0, "reps": 25, "time": 0}, {"weight": 40.0, "reps": 15, "time": 0}, {"weight": 68.0, "reps": 20, "time": 0}, {"weight": 47.0, "reps": 15, "time": 0}, {"weight": 47.0, "reps": 15, "time": 0}], "bName": "Leg", "eName": "Leg Extension", "bTextId": "CAT_LEG", "eTextId": "LGE_EXT"}, {"sets": [{"weight": 12.0, "reps": 20, "time": 0}, {"weight": 12.0, "reps": 20, "time": 0}], "bName": "Leg", "eName": "Dumbbell Bulgarian Split Squat", "bTextId": "CAT_LEG", "eTextId": "DB_BULSPLIT_SQT"}, {"sets": [{"weight": 60.0, "reps": 5, "time": 0}, {"weight": 50.0, "reps": 15, "time": 0}], "bName": "Leg", "eName": "Back Squat", "bTextId": "CAT_LEG", "eTextId": "BB_BSQT"}], "duration": 118}, {"session_data": [{"sets": [{"weight": 11.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}, {"weight": 21.0, "reps": 15, "time": 0}, {"weight": 21.0, "reps": 15, "time": 0}], "bName": "Arm", "eName": "Cable Curl", "bTextId": "CAT_ARM", "eTextId": "CABLE_CURL"}, {"sets": [{"weight": 11.0, "reps": 20, "time": 0}, {"weight": 18.0, "reps": 10, "time": 0}, {"weight": 18.0, "reps": 12, "time": 0}, {"weight": 18.0, "reps": 12, "time": 0}], "bName": "Arm", "eName": "Cable Curl", "bTextId": "CAT_ARM", "eTextId": "CABLE_CURL"}, {"sets": [{"weight": 28.0, "reps": 20, "time": 0}, {"weight": 63.0, "reps": 10, "time": 0}, {"weight": 63.0, "reps": 15, "time": 0}, {"weight": 63.0, "reps": 15, "time": 0}, {"weight": 63.0, "reps": 15, "time": 0}], "bName": "Leg", "eName": "Hip Abduction Machine", "bTextId": "CAT_LEG", "eTextId": "HIP_ABD_MC"}], "duration": 51}, {"session_data": [{"sets": [{"weight": 32.0, "reps": 15, "time": 0}, {"weight": 41.0, "reps": 15, "time": 0}, {"weight": 50.0, "reps": 13, "time": 0}, {"weight": 45.0, "reps": 13, "time": 0}], "bName": "Chest", "eName": "Pec Deck Fly Machine", "bTextId": "CAT_CHEST", "eTextId": "PEC_DECK_MC"}, {"sets": [{"weight": 0.0, "reps": 30, "time": 0}, {"weight": 0.0, "reps": 30, "time": 0}, {"weight": 0.0, "reps": 30, "time": 0}], "bName": "Abs", "eName": "Abdominal Hip Thrust", "bTextId": "CAT_ABS", "eTextId": "ABS_HIP_THRU"}, {"sets": [{"weight": 16.0, "reps": 15, "time": 0}, {"weight": 26.0, "reps": 4, "time": 0}, {"weight": 24.0, "reps": 4, "time": 0}, {"weight": 24.0, "reps": 4, "time": 0}, {"weight": 24.0, "reps": 4, "time": 0}], "bName": "Chest", "eName": "Incline Dumbbell Bench Press", "bTextId": "CAT_CHEST", "eTextId": "DB_INC_BP"}, {"sets": [{"weight": 0.0, "reps": 12, "time": 0}, {"weight": 0.0, "reps": 12, "time": 0}, {"weight": 0.0, "reps": 12, "time": 0}, {"weight": 0.0, "reps": 12, "time": 0}], "bName": "Chest", "eName": "Dips", "bTextId": "CAT_CHEST", "eTextId": "DIPS"}, {"sets": [{"weight": 18.0, "reps": 20, "time": 0}, {"weight": 18.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}, {"weight": 16.0, "reps": 20, "time": 0}], "bName": "Arm", "eName": "Cable Push Down", "bTextId": "CAT_ARM", "eTextId": "CABLE_PUSH_DOWN"}], "duration": 50}]'


    prompt = f"""## [Task]
weekly-routine

## [Primary Goal]
Generate a personalized, safe, and effective weekly workout routine based on the user's profile, recent history, and stated goals.

## [User Info]
{user_info_txt}

## [Recent Workout History]
{history_summary_txt}

## [Core Instructions]
1.  **Role**: You are an expert AI personal trainer.
2.  **Personalization**: Generate a **detailed, week-long workout routine** tailored to the [User Info] and [Recent Workout History].
3.  **Data-Driven**: Base your recommendations *only* on the provided data. Do not invent exercises not in the catalog unless necessary.
4.  **Output Format**:
    *   **MUST be a valid JSON array** of session objects.
    *   No prose, comments, or markdown code fences (```).
    *   The root of the output must be `[` and the end must be `]`.
    *   The number of session objects in the array **MUST exactly match the user's weekly frequency ({frequency} days)**.

## [Detailed JSON Structure]

### Session Object:
-   `"session_data"`: An array of Exercise Objects.
-   `"duration"`: Total estimated duration of the session in minutes.

### Exercise Object:
-   `"sets"`: Array of Set Objects.
-   `"bName"`: Body part name. Must be one of: `["Leg", "Chest", "Back", "Shoulder", "Arm", "Lifting", "Abs", "etc", "Cardio"]`.
-   `"eName"`: Human-readable exercise name from the catalog.
-   `"bTextId"`: Body part category ID from the catalog. (e.g., `"CAT_LEG"`).
-   `"eTextId"`: Canonical exercise ID from the catalog. If an exercise is not in the catalog, create a new, logical `UPPER_SNAKE_CASE` ID (e.g., `"NEW_CARDIO_MACHINE"`).

### Set Object:
-   `"weight"`: Weight in kg.
-   `"reps"`: Repetition count.
-   `"time"`: Time in seconds.
-   **Consistency Rules (based on `eInfoType` from catalog):**
    *   `eInfoType = 1` (Time-based): `time > 0`, `reps = 0`, `weight = 0.0`.
    *   `eInfoType = 2` (Bodyweight/Reps-only): `reps > 0`, `time = 0`, `weight = 0.0`.
    *   `eInfoType = 6` (Weight-based): `reps > 0`, `weight >= 0`, `time = 0`.

## [Training Principles]

### 1. Level Gating (Mandatory)
-   **Beginner**: Focus on machine-based exercises and bodyweight movements. Avoid complex free-weight compounds (e.g., barbell squats, deadlifts) and high-skill gymnastics (e.g., pull-ups, muscle-ups). Substitute with safer alternatives (e.g., Leg Press instead of Barbell Squat, Lat Pulldown instead of Pull-up).
-   **Novice**: Introduce basic free-weight exercises (e.g., dumbbell press, goblet squats) as accessories, while keeping machines for main strength work.
-   **Intermediate**: Prioritize free-weight compound movements for main lifts. Use machines and isolation exercises for supplemental volume.
-   **Advanced/Elite**: Design the routine around the user's specific `Workout Type` (e.g., strength, hypertrophy). Expect higher intensity, volume, and inclusion of advanced techniques.

### 2. Load Selection & Progression
-   **Existing Movements**: Base the load on the user's most recent successful working set for that exercise in the [Recent Workout History].
-   **Progressive Overload**: Apply a small, logical increase (e.g., 2.5-5% weight increase or +1-2 reps) compared to the last relevant session.
-   **New Movements or No History**: If no recent data exists, estimate a conservative starting weight based on the user's level and body weight. It's better to start too light than too heavy.

### 3. Routine Structure
-   **Balance**: Ensure a balanced distribution of exercises across major muscle groups throughout the week. Avoid overworking a single muscle group.
-   **Rest Days**: The number of workouts implies rest days. Structure the routine to allow for adequate recovery (e.g., don't schedule two heavy leg days back-to-back).
-   **Goal Alignment**: The exercise selection and structure should reflect the user's `Workout Type` (e.g., more compound lifts for 'strength', more volume and isolation for 'bodybuilding').

## [Available Exercise Catalog]
{exercise_list_text}

## [Example Output] (This is a structural guide ONLY. Do NOT copy these values.)
{example_output}

## [Final Instruction]
- Review all instructions carefully.
- Return **ONLY** the generated JSON array.
"""
    return prompt

if __name__ == "__main__":
    prompt = create_prompt()
    print(prompt)
