import json
from pathlib import Path
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
FINETUNING_FILE_PATH = DATA_DIR / 'finetuning_data.jsonl'
EXERCISE_CATALOG_PATH = DATA_DIR / '02_processed' / 'processed_query_result.json'

# Number of records to display
NUM_RECORDS_TO_VIEW = 1

def load_exercise_catalog_map():
    """Loads the exercise catalog into a dictionary keyed by eTextId."""
    try:
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f:
            exercise_list = json.load(f)
        return {item["eTextId"]: item for item in exercise_list if "eTextId" in item}
    except FileNotFoundError:
        return None

def dehydrate_to_array(full_routine):
    """Converts a full routine to an ultra-compact array format."""
    ultra_compact_routine = []
    if not isinstance(full_routine, list):
        return ultra_compact_routine
        
    for session in full_routine:
        exercises_array = []
        for exercise in session.get("session_data", []):
            sets_array = []
            for s in exercise.get("sets", []):
                sets_array.append([s.get("weight", 0), s.get("reps", 0), s.get("time", 0)])
            exercises_array.append([exercise.get("eTextId"), sets_array])
        session_array = [session.get("duration"), exercises_array]
        ultra_compact_routine.append(session_array)
    return ultra_compact_routine

def rehydrate_from_array(compact_routine_array, catalog_map):
    """Converts an ultra-compact array-based routine back into a full routine object."""
    if not catalog_map: return []
    full_routine = []
    for session_arr in compact_routine_array:
        duration, exercises_arr = session_arr[0], session_arr[1]
        session_data = []
        for ex_arr in exercises_arr:
            e_text_id, sets_arr = ex_arr[0], ex_arr[1]
            sets = [{"weight": s[0], "reps": s[1], "time": s[2]} for s in sets_arr]
            
            catalog_entry = catalog_map.get(e_text_id, {})
            session_data.append({
                "eTextId": e_text_id,
                "sets": sets,
                "bName": catalog_entry.get("bName"),
                "eName": catalog_entry.get("eName"),
                "bTextId": catalog_entry.get("bTextId"),
            })
        full_routine.append({
            "duration": duration,
            "session_data": session_data
        })
    return full_routine

def view_data_with_postprocessing_demo():
    """
    Reads records and demonstrates the ultra-compact array -> post-processing workflow.
    """
    logging.info(f"Attempting to read from: {FINETUNING_FILE_PATH}")
    catalog_map = load_exercise_catalog_map()

    if not FINETUNING_FILE_PATH.exists():
        logging.error(f"File not found: {FINETUNING_FILE_PATH}")
        print(f"Error: The file '{FINETUNING_FILE_PATH.name}' was not found in the 'data' directory.")
        return
        
    if not catalog_map:
        logging.error(f"Catalog not found at {EXERCISE_CATALOG_PATH}. Cannot demonstrate post-processing.")
        return

    with open(FINETUNING_FILE_PATH, 'r', encoding='utf-8') as f:
        print("="*60)
        print("Demonstrating Ultra-Compact Array -> Post-Processing Workflow")
        print("="*60)
        for i, line in enumerate(f):
            if i >= NUM_RECORDS_TO_VIEW:
                break
            
            try:
                record = json.loads(line)
                print(f"\n--- Record #{i+1} ---\n")
                
                full_output_str = record.get("output", "[]")
                full_output_json = json.loads(full_output_str)

                # --- Viewing Options Start ---
                # Instructions: Comment out the section you don't want to see.

                # Option 1: View the ULTRA-COMPACT array data (the new proposed target for the model)
                print("[1] PROPOSED ULTRA-COMPACT OUTPUT (New target for the model)")
                compact_array_output = dehydrate_to_array(full_output_json)
                print(compact_array_output)

                #Option 2: View the RECONSTRUCTED FULL data (after post-processing the array)
                print("\n[2] RECONSTRUCTED FULL OUTPUT (After post-processing the array)")
                rehydrated_output = rehydrate_from_array(compact_array_output, catalog_map)
                print(json.dumps(rehydrated_output, indent=2, ensure_ascii=False))
                
                # --- Viewing Options End ---

                print("\n" + "="*60)

            except json.JSONDecodeError:
                logging.warning(f"Could not decode line {i+1} as JSON.")
                continue

if __name__ == "__main__":
    view_data_with_postprocessing_demo()
