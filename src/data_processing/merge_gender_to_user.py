import json
import os

def merge_gender_to_user():
    """
    Merges gender information from user_gender.ndjson into user.ndjson.

    Reads gender data, then iterates through user data, adding the gender
    to each user object based on matching IDs. The merged data is written
    to a new file, user_with_gender.ndjson.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    gender_file_path = os.path.join(script_dir, '../../data/json/user_gender.ndjson')
    user_file_path = os.path.join(script_dir, '../../data/json/user.ndjson')
    output_file_path = os.path.join(script_dir, '../../data/json/user_with_gender.ndjson')

    gender_map = {}
    try:
        with open(gender_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if 'id' in data and 'gender' in data:
                        gender_map[data['id']] = data['gender']
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line in gender file: {line.strip()}")
                    continue
    except FileNotFoundError:
        print(f"Error: {os.path.basename(gender_file_path)} not found at {gender_file_path}. Make sure the path is correct.")
        return

    output_lines = []
    try:
        with open(user_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    user_data = json.loads(line)
                    user_id = user_data.get('id')
                    if user_id in gender_map:
                        user_data['gender'] = gender_map[user_id]
                    
                    output_lines.append(json.dumps(user_data, ensure_ascii=False))

                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line in user file: {line.strip()}")
                    continue
    except FileNotFoundError:
        print(f"Error: {os.path.basename(user_file_path)} not found. Make sure the path is correct.")
        return
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for line in output_lines:
                f.write(line + '\n')
        print(f"Merged data written to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file: {e}")


if __name__ == "__main__":
    merge_gender_to_user()