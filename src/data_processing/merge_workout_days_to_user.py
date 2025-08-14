import json

def merge_workout_days():
    # workout_days.ndjson 파일을 읽어 user_id를 키로 하는 딕셔너리를 생성합니다.
    workout_days_lookup = {}
    with open('/Users/yejunsin/Documents/weekly_routine_ai/data/json/workout_days.ndjson', 'r') as f:
        for line in f:
            data = json.loads(line)
            workout_days_lookup[data['user_id']] = data['workout_days']

    # user.ndjson 파일을 한 줄씩 읽고 workout_days를 추가합니다.
    output_lines = []
    with open('/Users/yejunsin/Documents/weekly_routine_ai/data/json/user.ndjson', 'r') as f:
        for line in f:
            user_data = json.loads(line)
            user_id = user_data.get('id')
            if user_id in workout_days_lookup:
                user_data['workout_days'] = workout_days_lookup[user_id]
            output_lines.append(json.dumps(user_data))

    # 결과를 새로운 ndjson 파일에 씁니다.
    with open('/Users/yejunsin/Documents/weekly_routine_ai/data/json/user_with_workout_days.ndjson', 'w') as f:
        for line in output_lines:
            f.write(line + '\n')

if __name__ == '__main__':
    merge_workout_days()
