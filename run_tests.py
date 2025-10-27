
import json
import urllib.request
import time
import os

# --- Configuration ---
TEST_CASES_PATH = os.path.join('web', 'test_cases.json')
API_ENDPOINT = 'http://127.0.0.1:5001/api/infer'
TOTAL_CASES = 80 # Expected number of cases

# --- Sorting Logic (replicated from script.js) ---
def get_sort_key(exercise):
    """Generates a sort key for an exercise."""
    bname_priority_map = {
        'LEG': 1, 'CHEST': 2, 'BACK': 3, 'SHOULDER': 4, 'ARM': 5, 'ABS': 6, 'ETC': 7
    }
    b_name = (exercise.get('bName') or 'ETC').upper()
    priority = bname_priority_map.get(b_name, 99)
    
    try:
        mg_num = -int(exercise.get('MG_num', 0))
    except (ValueError, TypeError):
        mg_num = 0
        
    try:
        muscle_point_sum = -int(exercise.get('musle_point_sum', 0))
    except (ValueError, TypeError):
        muscle_point_sum = 0
        
    return (priority, mg_num, muscle_point_sum)

# --- Main Processing Function ---
def run_tests():
    """
    Loads test cases, filters out already completed ones, calls the vLLM API for the rest,
    and updates the test case file.
    """
    print(f"Loading test cases from {TEST_CASES_PATH}...")
    try:
        with open(TEST_CASES_PATH, 'r', encoding='utf-8') as f:
            all_cases = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: Could not load or parse {TEST_CASES_PATH}. {e}")
        return

    # Define the 6 specific cases to re-run
    targets_to_rerun = [
        {"gender": "M", "level": "Beginner", "split_id": "SPLIT", "freq": 2},
        {"gender": "M", "level": "Intermediate", "split_id": "SPLIT", "freq": 2},
        {"gender": "M", "level": "Elite", "split_id": "SPLIT", "freq": 3},
        {"gender": "F", "level": "Intermediate", "split_id": "SPLIT", "freq": 3},
        {"gender": "F", "level": "Intermediate", "split_id": "SPLIT", "freq": 4},
        {"gender": "F", "level": "Advanced", "split_id": "SPLIT", "freq": 3},
    ]

    # Create a set of tuples for efficient lookup
    target_set = { (t["gender"], t["level"], t["split_id"], t["freq"]) for t in targets_to_rerun }

    # Separate cases to keep from cases to re-process
    other_cases = []
    cases_to_process = []
    for case in all_cases:
        case_tuple = (case["gender"], case["level"], case["split_id"], case["freq"])
        if case_tuple in target_set:
            cases_to_process.append(case)
        else:
            other_cases.append(case)

    if not cases_to_process:
        print("No target cases found for reprocessing. Exiting.")
        return

    print(f"{len(other_cases)} cases will be kept as is.")
    print(f"Starting to re-process {len(cases_to_process)} target cases...")

    newly_processed_cases = []
    for i, case in enumerate(cases_to_process):
        print(f"--- Processing case {i+1}/{len(cases_to_process)}: {case['gender']}-{case['level']}-{case['freq']}day-{case['split_id']} ---")

        # Construct the full payload for the API
        payload = {
            **case,
            "weight": 75, # Default value from index.html
            "duration": 60, # Default value
            "intensity": "Normal", # Default value
            "tools": ["Barbell", "Dumbbell", "Machine", "Bodyweight", "EZbar", "Etc", "PullUpBar"], # Default "Kettlebell" 제외
            "prevent_weekly_duplicates": True, # Default
            "prevent_category_duplicates": True, # As requested
            "max_tokens": 4096,
            "temperature": 1.0
        }
        
        try:
            # Prepare and send the request
            data = json.dumps(payload).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
            req = urllib.request.Request(API_ENDPOINT, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=180) as response:
                if response.status != 200:
                    print(f"  Error: Received status {response.status}. Skipping.")
                    raw_body = response.read().decode('utf-8', errors='ignore')
                    print(f"  Response body: {raw_body}")
                    case['routine'] = {"error": f"HTTP {response.status}"}
                else:
                    response_data = json.loads(response.read().decode('utf-8'))
                    
                    # Process the received routine
                    raw_routine = response_data.get('routine', {})
                    simplified_routine = {}
                    
                    if raw_routine and 'days' in raw_routine:
                        # Sort exercises within each day
                        for day_exercises in raw_routine['days']:
                            day_exercises.sort(key=get_sort_key)

                        # Extract only the Korean names
                        for day_idx, day_exercises in enumerate(raw_routine['days']):
                            day_key = f"Day {day_idx + 1}"
                            simplified_routine[day_key] = [ex.get('kName', 'Unknown') for ex in day_exercises]
                    
                    # Add the simplified routine to the case
                    case['routine'] = simplified_routine
                    print(f"  Success: Routine generated and processed.")

        except Exception as e:
            print(f"  An error occurred during API call or processing: {e}")
            case['routine'] = {"error": str(e)}
        
        newly_processed_cases.append(case)
        time.sleep(1) # Be nice to the server

    # Combine and write back
    final_cases = other_cases + newly_processed_cases
    print(f"\nAll remaining cases processed. Writing {len(final_cases)} total cases back to {TEST_CASES_PATH}...")
    try:
        with open(TEST_CASES_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_cases, f, indent=2, ensure_ascii=False)
        print("Successfully updated test_cases.json.")
    except IOError as e:
        print(f"Error writing to file: {e}")

if __name__ == '__main__':
    run_tests()
