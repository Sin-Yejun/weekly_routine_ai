import pandas as pd
import json
import os
import pyarrow.parquet as pq

import pandas as pd
import json
import os
import pyarrow.parquet as pq

def convert_workout_data_to_json(user_id: int, output_path: str):
    """
    특정 사용자의 운동 데이터를 Parquet 파일에서 읽어와 JSON 파일로 변환합니다.
    이제 중첩된 JSON 문자열을 올바르게 파싱합니다.

    Args:
        user_id (int): 조회할 사용자의 ID.
        output_path (str): JSON 파일을 저장할 경로.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    parquet_path = os.path.join(project_root, 'data', 'parquet', 'workout_session.parquet')

    if not os.path.exists(parquet_path):
        print(f"Error: Parquet file not found at {parquet_path}")
        return

    table = pq.read_table(
        parquet_path,
        columns=['user_id', 'date', 'session_data', 'duration'],
        filters=[('user_id', '==', user_id)]
    )
    df = table.to_pandas()
    user_df = df.sort_values(by='date', ascending=False)

    daily_workouts = []
    for row in user_df.itertuples():
        exercises_with_success_sets = []
        try:
            exercises_list = json.loads(row.session_data)
            for exercise_data in exercises_list:
                sets_str = exercise_data.get('sets')
                success_sets = []
                if isinstance(sets_str, str):
                    try:
                        parsed_sets = json.loads(sets_str)
                        for s in parsed_sets:
                            if s.get('state') == 'success':
                                success_sets.append({
                                    'sReps': s.get('reps'),
                                    'sWeight': s.get('weight'),
                                    'sTime': s.get('time', 0)
                                })
                    except (json.JSONDecodeError, SyntaxError):
                        continue
                
                if success_sets:
                    exercises_with_success_sets.append({
                        'bName': exercise_data.get('bName'),
                        'eName': exercise_data.get('eName'),
                        'bTextId': exercise_data.get('bTextId'),
                        'eTextId': exercise_data.get('eTextId'),
                        'data': success_sets
                    })
        except (json.JSONDecodeError, TypeError):
            continue

        if exercises_with_success_sets:
            daily_workouts.append({
                'date': row.date,
                'duration': row.duration,
                'exercises': exercises_with_success_sets
            })

    final_workouts = []
    for i, workout in enumerate(daily_workouts, 1):
        workout['dayNum'] = i
        # Convert date to string for JSON serialization
        workout['date'] = workout['date'].isoformat() if hasattr(workout['date'], 'isoformat') else workout['date']
        final_workouts.append(workout)

    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_workouts, f, ensure_ascii=False, indent=4)

    print(f"Successfully converted data for user {user_id} to {output_path}")

if __name__ == '__main__':
    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir)) # Go up two levels

    # Define the output path for the JSON file
    user_id = 12
    output_file_path = os.path.join(project_root, 'data', 'json', f'user_{user_id}_workout_history.json')

    # Run the conversion for the specified user
    convert_workout_data_to_json(user_id, output_file_path)
