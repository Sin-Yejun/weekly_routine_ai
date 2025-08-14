import json

def process_data(query_result_path, ai_exercise_list_path, bodypart_name_multi_path, output_path):
    # Load data
    with open(query_result_path, 'r', encoding='utf-8') as f:
        query_data = json.load(f)
    with open(ai_exercise_list_path, 'r', encoding='utf-8') as f:
        exercise_list_data = json.load(f)
    with open(bodypart_name_multi_path, 'r', encoding='utf-8') as f:
        bodypart_data = json.load(f)

    # Create lookup dictionaries
    exercise_lookup = {item['code']: item['en'] for item in exercise_list_data}
    bodypart_lookup = {item['code']: item['en'] for item in bodypart_data}

    processed_results = []
    for item in query_data:
        e_text_id = item.get('eTextId')
        b_text_id = item.get('bTextId')

        # Filter: Only include exercises present in ai_exercise_list.json
        if e_text_id in exercise_lookup:
            new_e_name = exercise_lookup[e_text_id]
            new_b_name = bodypart_lookup.get(b_text_id, item.get('bName')) # Fallback to original if not found

            processed_item = {
                'bName': new_b_name,
                'bTextId': b_text_id,
                'eName': new_e_name,
                'eTextId': e_text_id,
            }
            processed_results.append(processed_item)

    # Save processed data
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_results, f, ensure_ascii=False, indent=4)

    print(f"Processed data saved to {output_path}")

if __name__ == '__main__':
    query_result_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/json/query_result.json'
    ai_exercise_list_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/json/ai_exercise_list.json'
    bodypart_name_multi_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/multilingual-pack/bodypart_name_multi.json'
    output_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/json/processed_query_result.json'

    process_data(query_result_path, ai_exercise_list_path, bodypart_name_multi_path, output_path)
