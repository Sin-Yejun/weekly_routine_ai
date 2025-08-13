import json

def filter_workout_sessions(user_file, workout_file, output_file):
    """
    Filters workout sessions, keeping only those with user_ids present in the user file.
    """
    user_ids = set()
    with open(user_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                user_data = json.loads(line.strip())
                user_ids.add(user_data.get('id'))
            except json.JSONDecodeError:
                print(f"Skipping malformed JSON line in {user_file}: {line.strip()}")

    filtered_sessions = []
    with open(workout_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                session_data = json.loads(line.strip())
                if session_data.get('user_id') in user_ids:
                    filtered_sessions.append(json.dumps(session_data))
            except json.JSONDecodeError:
                print(f"Skipping malformed JSON line in {workout_file}: {line.strip()}")

    with open(output_file, 'w', encoding='utf-8') as f:
        for session in filtered_sessions:
            f.write(session + '\n')

    print(f"Filtered data saved to {output_file}")

if __name__ == "__main__":
    user_ndjson_path = 'data/json/user.ndjson'
    workout_ndjson_path = 'data/json/workout_session.ndjson'
    output_ndjson_path = 'data/json/filtered_workout_session.ndjson'

    filter_workout_sessions(user_ndjson_path, workout_ndjson_path, output_ndjson_path)
