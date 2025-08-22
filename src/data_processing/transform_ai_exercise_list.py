import json
import csv

def transform_exercise_data():
    # Load the exercise list
    with open('data/03_core_assets/ai_exercise_list.json', 'r', encoding='utf-8') as f:
        exercise_data = json.load(f)

    # Load the body part mapping
    bodypart_mapping = {}
    with open('data/01_raw/reference_csv/bodypart_name_db.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for i, row in enumerate(reader):
            bodypart_mapping[i + 1] = row[2] # English name is in the 3rd column

    # Transform the data
    transformed_data = []
    for exercise in exercise_data:
        transformed_exercise = {
            "e_text_id": exercise["code"],
            "e_name": exercise["en"],
            "b_name": bodypart_mapping.get(exercise["bodypart"], ""),
            "e_info_type": exercise["info_type"][0] if exercise["info_type"] else 0,
            "b_id": exercise["bodypart"],
            "t_id": exercise["tool"]
        }
        transformed_data.append(transformed_exercise)

    # Save the transformed data
    with open('data/03_core_assets/multilingual-pack/ai_exercise_list_post_processed.json', 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    transform_exercise_data()