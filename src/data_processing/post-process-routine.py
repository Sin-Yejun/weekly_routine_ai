import json
from pathlib import Path
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXERCISE_CATALOG_PATH = BASE_DIR / 'data' / '02_processed' / 'processed_query_result.json'

def load_exercise_catalog():
    """Loads the exercise catalog into a dictionary keyed by eTextId."""
    logging.info(f"Loading exercise catalog from {EXERCISE_CATALOG_PATH}...")
    try:
        with open(EXERCISE_CATALOG_PATH, "r", encoding="utf-8") as f:
            exercise_list = json.load(f)
        catalog_map = {item["eTextId"]: item for item in exercise_list if "eTextId" in item}
        logging.info("Exercise catalog loaded successfully.")
        return catalog_map
    except FileNotFoundError as e:
        logging.error(f"Error loading exercise catalog: {e}")
        raise

def reconstruct_from_array(compact_routine_array, catalog_map):
    """
    Converts an ultra-compact array-based routine into a full routine object.
    Schema: [ [duration, [ [eTextId, [ [w,r,t], ... ]], ... ]], ... ]
    """
    if not catalog_map:
        logging.error("Catalog map is empty. Cannot reconstruct routine.")
        return []

    full_routine = []
    for session_arr in compact_routine_array:
        if len(session_arr) != 2:
            continue
        duration, exercises_arr = session_arr[0], session_arr[1]
        session_data = []
        for ex_arr in exercises_arr:
            if len(ex_arr) != 2:
                continue
            e_text_id, sets_arr = ex_arr[0], ex_arr[1]
            sets = [{"weight": s[0], "reps": s[1], "time": s[2]} for s in sets_arr if len(s) == 3]
            
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

def main():
    """
    Example usage: Demonstrates how to use the array reconstruction function.
    """
    print("--- Array-based Post-processing Script Demonstration ---")
    
    # 1. Load the catalog
    catalog = load_exercise_catalog()

    # 2. Example ultra-compact routine (what the model would output)
    compact_array_example = [
        [60, # Session 1 duration
            [
                ["BB_BSQT", [[80, 10, 0], [90, 8, 0]]], # Exercise 1
                ["BB_DL", [[120, 5, 0], [130, 5, 0]]]  # Exercise 2
            ]
        ],
        [55, # Session 2 duration
            [
                ["BB_BP", [[60, 10, 0], [70, 8, 0]]] # Exercise 1
            ]
        ]
    ]
    
    print("\n[1] Ultra-compact array routine (from model):")
    print(json.dumps(compact_array_example, indent=2, ensure_ascii=False))

    # 3. Run the post-processing from array
    full_routine = reconstruct_from_array(compact_array_example, catalog)

    print("\n[2] Full routine (after post-processing):")
    print(json.dumps(full_routine, indent=2, ensure_ascii=False))
    
    print("\n--- Demonstration complete ---")


if __name__ == "__main__":
    main()
