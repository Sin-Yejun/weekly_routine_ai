# -*- coding: utf-8 -*-
import json
import os
import pandas as pd
from pathlib import Path
import logging
from tqdm import tqdm

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent # weekly_routine_ai is the root
DATA_DIR = BASE_DIR / 'data'
USER_HISTORY_DIR = DATA_DIR / '01_raw' / 'user_workout_history'
PARQUET_USER_PATH = DATA_DIR / '02_processed' / 'parquet' / 'user_v2.parquet'
BODYPART_MAP_PATH = DATA_DIR / '03_core_assets' / 'multilingual-pack' / 'bodypart_name_multi.json'
EXERCISE_MAP_PATH = DATA_DIR / '03_core_assets' / 'multilingual-pack' / 'exercise_list_multi.json'
EXERCISE_CATALOG_PATH = DATA_DIR / '02_processed' / 'processed_query_result.json'
OUTPUT_PATH = DATA_DIR / 'finetuning_data.jsonl'

# --- Helper Functions (Adapted from original scripts) ---

def load_shared_data():
    """Loads dataframes and maps needed for processing."""
    logging.info("Loading shared data...")
    try:
        user_df = pd.read_parquet(PARQUET_USER_PATH)
        with open(BODYPART_MAP_PATH, "r", encoding="utf-8") as f:
            bodypart_map = {item["code"]: item["en"] for item in json.load(f)}
        with open(EXERCISE_MAP_PATH, "r", encoding="utf-8") as f:
            exercise_map = {item["code"]: item["en"] for item in json.load(f)}
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f:
            exercise_catalog = json.load(f)
        logging.info("Shared data loaded successfully.")
        return user_df, bodypart_map, exercise_map, exercise_catalog
    except FileNotFoundError as e:
        logging.error(f"Error loading shared data: {e}")
        raise

def get_user_info(user_df, user_id):
    """Gets profile text and frequency for a specific user from the pre-loaded dataframe."""
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
    """Compresses a list of sets into a compact string."""
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

def summarize_user_history(workout_days: list, bodypart_map: dict, exercise_map: dict) -> str:
    """Creates a detailed text summary from a list of user workout sessions."""
    texts = []
    for idx, day in enumerate(workout_days, 1):
        duration = day.get('duration')
        duration_str = f" - Duration: {duration}min" if duration else ""
        header = f"Recent Workout #{idx}{duration_str}"
        lines = [header]
        if "session_data" in day and day["session_data"]:
            for ex in day["session_data"]:
                b_name = bodypart_map.get(ex.get('bTextId'), ex.get('bName', 'N/A'))
                e_name = exercise_map.get(ex.get('eTextId'), ex.get('eName', 'N/A'))
                
                # Handle cases where 'sets' might be None
                sets_data = ex.get('sets') or []
                num_sets = len(sets_data)
                
                compressed_sets_str = compress_sets(sets_data)
                line = (
                    f"{b_name:<12}- {e_name} ({ex.get('eTextId', 'N/A')}) "
                    f"{num_sets}sets: {compressed_sets_str}"
                )
                lines.append(line)
        texts.append("\n".join(lines))
    return "\n\n".join(texts)

def create_final_prompt(user_info_txt, history_summary_txt, frequency, exercise_catalog):
    """Builds the final prompt for the model."""
    exercise_list_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in exercise_catalog)
    
    # This is a simplified example output structure
    example_output = '[{"session_data": [...], "duration": 60}, ...]' # Note: Escaped quotes within the string literal

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
-   `"bTextId"`: Body part category ID (e.g., `"CAT_LEG"`).
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


def main():
    """Main function to generate finetuning data."""
    user_df, bodypart_map, exercise_map, exercise_catalog = load_shared_data()

    user_files = [f for f in USER_HISTORY_DIR.glob('*.json')]

    processed_count = 0
    skipped_count = 0

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as out_file:
        for user_file in tqdm(user_files, desc="Processing users"):
            try:
                user_id = int(user_file.stem)
            except (ValueError, IndexError):
                logging.warning(f"Could not parse user ID from filename: {user_file.name}. Skipping.")
                skipped_count += 1
                continue

            # 1. Get user info and frequency
            user_info_txt, frequency = get_user_info(user_df, user_id)
            if not user_info_txt:
                # logging.info(f"User ID {user_id} not found in user.parquet. Skipping.")
                skipped_count += 1
                continue

            # 2. Load user history
            with user_file.open('r', encoding='utf-8') as f:
                user_history = json.load(f)
            
            # Data is assumed to be sorted by date descending
            
            # 3. Check if there is enough data
            required_records = frequency + 10
            if len(user_history) < required_records:
                # logging.info(f"User {user_id} has insufficient records ({len(user_history)} < {required_records}). Skipping.")
                skipped_count += 1
                continue

            # 4. Split data into output and history summary parts
            output_sessions = user_history[:frequency]
            history_for_summary = user_history[frequency:required_records]

            # 5. Format the output data
            formatted_output = [{"session_data": s.get("session_data"), "duration": s.get("duration")} for s in output_sessions]

            # 6. Create history summary text
            history_summary_txt = summarize_user_history(history_for_summary, bodypart_map, exercise_map)

            # 7. Create the final input prompt
            final_prompt = create_final_prompt(user_info_txt, history_summary_txt, frequency, exercise_catalog)

            # 8. Write to file
            finetuning_record = {"input": final_prompt, "output": json.dumps(formatted_output, ensure_ascii=False)}
            out_file.write(json.dumps(finetuning_record, ensure_ascii=False) + '\n')
            processed_count += 1

    logging.info(f"--- Processing Complete ---")
    logging.info(f"Successfully processed: {processed_count} users.")
    logging.info(f"Skipped (insufficient data or not found): {skipped_count} users.")
    logging.info(f"Output saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
