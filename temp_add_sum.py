import json
import os
import re

# Define path
base_dir = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai'
json_path = os.path.join(base_dir, 'data', '02_processed', 'processed_query_result.json')

# 1. Read the JSON file
try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"Error reading JSON file: {e}")
    exit()

# 2. Process the data to add the sum
for item in data:
    if 'musle_point' in item and isinstance(item['musle_point'], list):
        point_list = [p for p in item['musle_point'] if isinstance(p, (int, float))]
        item['musle_point_sum'] = sum(point_list)
    else:
        item['musle_point_sum'] = 0

# 3. Write the updated data back to the JSON file
try:
    json_string = json.dumps(data, indent=2, ensure_ascii=False)
    
    # Re-apply the compacting regex from before to keep the format consistent
    final_json_string = re.sub(
        r'("musle_point":\s*)(\[[\s\S]*?\])',
        lambda m: m.group(1) + m.group(2).replace('\n', '').replace(' ', ''),
        json_string
    )
    
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(final_json_string)

    print(f"Successfully updated JSON file at {json_path}")
except Exception as e:
    print(f"An error occurred during JSON writing: {e}")
