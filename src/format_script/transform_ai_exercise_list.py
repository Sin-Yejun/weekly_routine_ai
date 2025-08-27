import json
import csv

def transform_exercise_data():
    # Load the exercise list
    with open('data/03_core_assets/ai_exercise_list.json', 'r', encoding='utf-8') as f:
        exercise_data = json.load(f)

    # Load the body part mapping
    with open('data/03_core_assets/multilingual-pack/post_process_en.json', 'r', encoding='utf-8') as f:
        processed_query_data = json.load(f)
    # Create a mapping from eTextId to eInfoType
    e_info_type_mapping = {exercise['code'] for exercise in exercise_data}

    # 조건에 맞는 데이터만 필터링
    filtered_data = [exercise for exercise in processed_query_data if exercise['e_text_id'] in e_info_type_mapping]

    # 필터링된 데이터 저장
    with open('data/03_core_assets/multilingual-pack/post_process_en_from_ai_list.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    transform_exercise_data()


