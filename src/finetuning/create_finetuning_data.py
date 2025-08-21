# -*- coding: utf-8 -*-
import json
import os
import random
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
    """Creates a compact text summary of user workout sessions using eTextId."""
    texts = []
    for idx, day in enumerate(workout_days, 1):
        duration = day.get('duration')
        duration_str = f" (Duration: {duration}min)" if duration else ""
        header = f"[Workout #{idx}{duration_str}]"
        lines = [header]
        if "session_data" in day and day["session_data"]:
            for ex in day["session_data"]:
                e_text_id = ex.get('eTextId', 'N/A')
                
                sets_data = ex.get('sets') or []
                if not sets_data:
                    continue
                
                num_sets = len(sets_data)
                compressed_sets_str = compress_sets(sets_data)
                
                line = f"- {e_text_id}: {num_sets}sets: {compressed_sets_str}"
                lines.append(line)
        
        # Only include workouts that have actual exercise data
        if len(lines) > 1:
            texts.append("\n".join(lines))
            
    return "\n\n".join(texts)

def create_final_prompt(user_info_txt, history_summary_txt, frequency, exercise_catalog):
    """Builds a balanced and more concise prompt for the model."""
    # 1. Use the compact catalog format
    compact_catalog_list = [
        f'["{e.get("eTextId", "")}", "{e.get("bTextId", "")}", {e.get("eInfoType", 0)}, "{e.get("eName", "")}"]'
        for e in exercise_catalog
    ]
    exercise_list_text = ",\n".join(compact_catalog_list)

    # The output format is now the ultra-compact array
    example_output = '[[60, [["BB_BSQT", [[80,10,0], [90,8,0]]]]]]'

    # 2. Use more concise instructions with detailed Level Gating
    prompt = f"""
## [Task]
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
                exercises_array.append([exercise.get("eTextId"), sets_array])
        session_array = [session.get("duration"), exercises_array]
        ultra_compact_routine.append(session_array)
    return ultra_compact_routine

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
                skipped_count += 1
                continue

            # 2. Load user history
            with user_file.open('r', encoding='utf-8') as f:
                user_history = json.load(f)
            
            # 3. Check if there is enough data
            required_records = frequency + 10
            if len(user_history) < required_records:
                skipped_count += 1
                continue

            # 4. Split data into output and history summary parts
            output_sessions = user_history[:frequency]
            history_for_summary = user_history[frequency:required_records]

            # 5. Format the output data to the ultra-compact array format
            output_array = dehydrate_to_array(output_sessions)

            # 6. Create a filtered exercise catalog for the prompt
            output_exercise_ids = set()
            for session in output_sessions:
                if session.get("session_data"):
                    for exercise in session["session_data"]:
                        if exercise.get("eTextId"):
                            output_exercise_ids.add(exercise["eTextId"])

            history_exercise_ids = set()
            for day in history_for_summary:
                if "session_data" in day and day["session_data"]:
                    for ex in day["session_data"]:
                        if ex.get("eTextId"):
                            history_exercise_ids.add(ex["eTextId"])

            required_exercise_ids = output_exercise_ids.union(history_exercise_ids)
            
            required_catalog = [ex for ex in exercise_catalog if ex.get("eTextId") in required_exercise_ids]
            
            included_ids = {ex['eTextId'] for ex in required_catalog if 'eTextId' in ex}
            remaining_exercises = [ex for ex in exercise_catalog if ex.get("eTextId") not in included_ids]
            
            num_to_add = min(10, len(remaining_exercises))
            random.seed(user_id)
            random_exercises = random.sample(remaining_exercises, num_to_add)
            
            filtered_exercise_catalog = required_catalog + random_exercises

            # 7. Create history summary text
            history_summary_txt = summarize_user_history(history_for_summary, bodypart_map, exercise_map)

            # 8. Create the final input prompt
            final_prompt = create_final_prompt(user_info_txt, history_summary_txt, frequency, filtered_exercise_catalog)

            # 9. Write to file
            # Use separators=(',',':') for minified JSON string to save space
            finetuning_record = {"input": final_prompt, "output": json.dumps(output_array, ensure_ascii=False, separators=(',',':'))}
            out_file.write(json.dumps(finetuning_record, ensure_ascii=False) + '\n')
            processed_count += 1

    logging.info(f"--- Processing Complete ---")
    logging.info(f"Successfully processed: {processed_count} users.")
    logging.info(f"Skipped (insufficient data or not found): {skipped_count} users.")
    logging.info(f"Output saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()