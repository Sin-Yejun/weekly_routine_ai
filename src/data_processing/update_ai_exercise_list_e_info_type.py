
import json

def update_e_info_type_reverse():
    # Load the file to be updated
    with open('data/03_core_assets/multilingual-pack/ai_exercise_list_post_processed.json', 'r', encoding='utf-8') as f:
        ai_exercise_data = json.load(f)

    # Load the file with the new e_info_type values
    with open('data/02_processed/processed_query_result.json', 'r', encoding='utf-8') as f:
        processed_query_data = json.load(f)

    # Create a mapping from eTextId to eInfoType
    e_info_type_mapping = {exercise['eTextId']: exercise['eInfoType'] for exercise in processed_query_data}

    # Update the e_info_type in the ai_exercise_data
    for exercise in ai_exercise_data:
        if exercise['e_text_id'] in e_info_type_mapping:
            exercise['e_info_type'] = e_info_type_mapping[exercise['e_text_id']]

    # Save the updated data back to the file
    with open('data/03_core_assets/multilingual-pack/ai_exercise_list_post_processed.json', 'w', encoding='utf-8') as f:
        json.dump(ai_exercise_data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    update_e_info_type_reverse()
