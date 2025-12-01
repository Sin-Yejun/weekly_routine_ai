
import json
import urllib.request
import time
import os

# --- Configuration ---
TEST_CASES_PATH = os.path.join('web', 'test_cases.json')
API_ENDPOINT = 'http://127.0.0.1:5001/api/infer'

# List of specific cases to re-run based on reported duplicates
DUPLICATE_CASES_TO_RERUN = [
    {'gender': 'M', 'level': 'Advanced', 'split_id': 'SPLIT', 'freq': 4, 'week': 4},
]

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
def rerun_duplicates():
    """
    Loads all test cases, finds the ones specified in DUPLICATE_CASES_TO_RERUN,
    regenerates only the specified week for each, and updates the file.
    """
    print(f"Loading test cases from {TEST_CASES_PATH}...")
    try:
        with open(TEST_CASES_PATH, 'r', encoding='utf-8') as f:
            all_cases = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: Could not load or parse {TEST_CASES_PATH}. {e}")
        return

    cases_processed_count = 0
    for i, case in enumerate(all_cases):
        for dup_case_info in DUPLICATE_CASES_TO_RERUN:
            # Check if the current case from the file matches a duplicate case
            if (case.get('gender') == dup_case_info['gender'] and
                case.get('level') == dup_case_info['level'] and
                case.get('split_id') == dup_case_info['split_id'] and
                case.get('freq') == dup_case_info['freq']):

                week_num_to_rerun = dup_case_info['week']
                
                print(f"\n--- Found matching case to re-run (Case #{i+1}): {case['gender']}-{case['level']}-{case['freq']}day-{case['split_id']} for Week {week_num_to_rerun} ---")

                # Server now handles all level-based tool filtering. Client sends all available tools.
                tools_list = ["Barbell", "Dumbbell", "Machine", "Bodyweight", "EZbar", "Etc", "PullUpBar"]

                # Construct the full payload for the API
                base_case = {k: v for k, v in case.items() if not k.startswith('week')}
                if 'routine' in base_case:
                    del base_case['routine']

                payload = {
                    **base_case,
                    "weight": 75,
                    "duration": 60,
                    "intensity": "Normal",
                    "tools": tools_list,
                    "prevent_weekly_duplicates": False,
                    "prevent_category_duplicates": True,
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
                            case[f'week{week_num_to_rerun}'] = {"error": f"HTTP {response.status}"}
                        else:
                            response_data = json.loads(response.read().decode('utf-8'))
                            
                            # Process the received routine
                            raw_routine = response_data.get('routine', {})
                            simplified_routine = {}
                            
                            if raw_routine and 'days' in raw_routine:
                                for day_exercises in raw_routine['days']:
                                    day_exercises.sort(key=get_sort_key)
                                for day_idx, day_exercises in enumerate(raw_routine['days']):
                                    day_key = f"Day {day_idx + 1}"
                                    simplified_routine[day_key] = [ex.get('kName', 'Unknown') for ex in day_exercises]
                            
                            # Update the specific week in the case
                            case[f'week{week_num_to_rerun}'] = simplified_routine
                            print(f"  Success: Routine for Week {week_num_to_rerun} regenerated and processed.")
                            cases_processed_count += 1

                except Exception as e:
                    print(f"  An error occurred during API call or processing for Week {week_num_to_rerun}: {e}")
                    case[f'week{week_num_to_rerun}'] = {"error": str(e)}
                
                time.sleep(1) # Be nice to the server
                # Break from the inner loop once a match is found and processed
                break

    if cases_processed_count > 0:
        print(f"\n--- {cases_processed_count} matching cases were processed. Writing results to {TEST_CASES_PATH}... ---")
        try:
            with open(TEST_CASES_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)
            print(f"--- Successfully updated {TEST_CASES_PATH}. ---")
        except IOError as e:
            print(f"Error writing to file: {e}")
    else:
        print("\nNo matching cases were found to process.")

if __name__ == '__main__':
    rerun_duplicates()
