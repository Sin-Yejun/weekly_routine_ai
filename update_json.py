
import json

processed_query_result_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/json/processed_query_result.json'
post_process_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/json/post_process.json'

try:
    with open(processed_query_result_path, 'r', encoding='utf-8') as f:
        processed_data = json.load(f)

    with open(post_process_path, 'r', encoding='utf-8') as f:
        post_process_data = json.load(f)

    # Create a dictionary for quick lookup from post_process_data
    e_info_type_map = {item['e_text_id']: item['e_info_type'] for item in post_process_data}

    # Update processed_data
    for item in processed_data:
        e_text_id = item.get('eTextId')
        if e_text_id and e_text_id in e_info_type_map:
            item['eInfoType'] = e_info_type_map[e_text_id]

    # Write the updated data back to the file
    with open(processed_query_result_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=4, ensure_ascii=False)

    print(f"Successfully updated {processed_query_result_path}")

except FileNotFoundError as e:
    print(f"Error: File not found - {e.filename}")
except json.JSONDecodeError:
    print("Error: Could not decode JSON from one of the files.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
