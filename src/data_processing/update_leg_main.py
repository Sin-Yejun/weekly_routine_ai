import json

def find_leg_main_list():
    # 1. Load the main exercise data file
    processed_data_path = 'data/02_processed/processed_query_result_filtered.json'
    try:
        with open(processed_data_path, 'r', encoding='utf-8') as f:
            exercises = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {processed_data_path}: {e}")
        return

    # 2. Filter for new LEG_MAIN exercises
    new_leg_main_names = []
    for exercise in exercises:
        if (exercise.get('bName') == 'Leg' and 
            isinstance(exercise.get('musle_point_sum'), (int, float)) and
            exercise.get('musle_point_sum') >= 15):
            new_leg_main_names.append(exercise.get('eName'))
            
    # 3. Print the resulting list
    print(f"Found {len(new_leg_main_names)} exercises for LEG_MAIN.")
    # Use json.dumps to pretty-print the list
    print(json.dumps(sorted(list(set(new_leg_main_names))), indent=4, ensure_ascii=False))

if __name__ == '__main__':
    find_leg_main_list()
