
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

    # Rerunning all cases
    cases_to_process = all_cases
    other_cases = [] # No cases to keep

    if not cases_to_process:
        print("No cases found to process. Exiting.")
        return

    print(f"Starting to process {len(cases_to_process)} total cases...")

    for week_num in range(1, 5):
        print(f"\n--- Generating routines for Week {week_num} ---\n")
        
        for i, case in enumerate(cases_to_process):
            # Check if the routine for the current week already exists and is valid
            if f'week{week_num}' in case and case.get(f'week{week_num}') and 'error' not in case.get(f'week{week_num}', {}):
                print(f"  Skipping case {i+1}/{len(cases_to_process)}: Week {week_num} data already exists.")
                continue

            print(f"--- Processing case {i+1}/{len(cases_to_process)} for Week {week_num}: {case['gender']}-{case['level']}-{case['freq']}day-{case['split_id']} ---")

            # Server now handles all level-based tool filtering. Client sends all available tools.
            tools_list = ["Barbell", "Dumbbell", "Machine", "Bodyweight", "EZbar", "Etc", "PullUpBar"]

            # Construct the full payload for the API, excluding other weekly routines
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
                        case[f'week{week_num}'] = {"error": f"HTTP {response.status}"}
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
                        
                        case[f'week{week_num}'] = simplified_routine
                        print(f"  Success: Routine for Week {week_num} generated and processed.")

            except Exception as e:
                print(f"  An error occurred during API call or processing for Week {week_num}: {e}")
                case[f'week{week_num}'] = {"error": str(e)}
            
            time.sleep(1) # Be nice to the server

        # Save results after each week's batch processing
        print(f"\n--- All cases for Week {week_num} processed. Writing results to {TEST_CASES_PATH}... ---")
        try:
            with open(TEST_CASES_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)
            print(f"--- Successfully updated test_cases.json for Week {week_num}. ---\n")
        except IOError as e:
            print(f"Error writing to file after Week {week_num}: {e}")

    print("\nAll weekly routines have been processed.")

if __name__ == '__main__':
    run_tests()
