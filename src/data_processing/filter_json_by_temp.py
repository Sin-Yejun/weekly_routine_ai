import json

# 파일 경로 설정
temp_txt_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\data\02_processed\temp.txt'
json_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\data\02_processed\processed_query_result_filtered.json'
output_json_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\data\02_processed\processed_query_result_200.json'

# temp.txt에서 운동 이름 읽기
with open(temp_txt_path, 'r', encoding='utf-8') as f:
    allowed_exercise_names = {line.strip() for line in f}

# processed_query_result_filtered.json에서 데이터 읽기
with open(json_path, 'r', encoding='utf-8') as f:
    all_exercises = json.load(f)

# 허용된 운동 이름에 해당하는 데이터만 필터링
filtered_exercises = [exercise for exercise in all_exercises if exercise['eName'] in allowed_exercise_names]

# 새로운 JSON 파일로 저장
with open(output_json_path, 'w', encoding='utf-8') as f:
    json.dump(filtered_exercises, f, ensure_ascii=False, indent=4)

print(f"'{output_json_path}' 파일에 {len(filtered_exercises)}개의 운동 정보가 저장되었습니다.")