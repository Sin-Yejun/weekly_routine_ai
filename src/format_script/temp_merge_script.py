import json

# Load the source and target JSON files
with open('C:\\Users\\yejun\\Desktop\\Project\\weekly_routine_ai\\data\\02_processed\\all_exercises_detail.json', 'r', encoding='utf-8') as f:
    all_exercises_data = json.load(f)

with open('C:\\Users\\yejun\\Desktop\\Project\\weekly_routine_ai\\data\\02_processed\\processed_query_result.json', 'r', encoding='utf-8') as f:
    processed_query_data = json.load(f)

# Create a dictionary for quick lookups from the source file
all_exercises_dict = {exercise.get('code'): exercise for exercise in all_exercises_data}

# Iterate through the target data and update it
for exercise in processed_query_data:
    code = exercise.get('eTextId')
    if code in all_exercises_dict:
        source_exercise = all_exercises_dict[code]
        exercise['MG'] = source_exercise.get('MG')
        exercise['tool'] = source_exercise.get('tool')
        exercise['bName'] = source_exercise.get('bName')
        exercise['kName'] = source_exercise.get('kName')
        exercise['eName'] = source_exercise.get('eName')
        exercise['tool_ko'] = source_exercise.get('tool_ko')
        exercise['MG_ko'] = source_exercise.get('MG_ko')
        exercise['eInfoType'] = source_exercise.get('eInfoType')

# Save the updated data to a new file
with open('C:\\Users\\yejun\\Desktop\\Project\\weekly_routine_ai\\data\\02_processed\\new_all_exercises.json', 'w', encoding='utf-8') as f:
    json.dump(processed_query_data, f, ensure_ascii=False, indent=4)

print("Merge complete. new_all_exercises.json created.")
