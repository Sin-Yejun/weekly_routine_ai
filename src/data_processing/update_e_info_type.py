
import json

def update_e_info_type():
    # Load the file to be updated
    with open('data/03_core_assets/multilingual-pack/post_process_en.json', 'r', encoding='utf-8') as f:
        post_process_data = json.load(f)

    # Load the file with the new e_info_type values
    with open('data/03_core_assets/multilingual-pack/ai_exercise_list_post_processed.json', 'r', encoding='utf-8') as f:
        ai_exercise_data = json.load(f)

    # Create a mapping from e_text_id to e_info_type
    e_info_type_mapping = {exercise['e_text_id']: exercise['e_info_type'] for exercise in ai_exercise_data}

    # Update the e_info_type in the post_process_data
    for exercise in post_process_data:
        if exercise['e_text_id'] in e_info_type_mapping:
            exercise['e_info_type'] = e_info_type_mapping[exercise['e_text_id']]

    # Save the updated data back to the file
    with open('data/03_core_assets/multilingual-pack/post_process_en.json', 'w', encoding='utf-8') as f:
        json.dump(post_process_data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    update_e_info_type()
