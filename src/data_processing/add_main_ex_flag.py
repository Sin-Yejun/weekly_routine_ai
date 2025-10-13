import json

# 파일 경로와 메인 운동 목록 설정
json_file_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\data\02_processed\processed_query_result_200.json'
main_exercise_names = {
    "Back Squat", "Barbell Bench Press", "Barbell Incline Bench Press",
    "Barbell Row", "Conventional Deadlift", "Dumbbell Bench Press",
    "Dumbbell Lunge", "Dumbbell Row", "Dumbbell Shoulder Press",
    "Hack Squat Machine", "Incline Bench Press Machine", "Incline Dumbbell Bench Press",
    "Lat Pull Down", "Leg Curl", "Leg Extension", "Leg Press",
    "Linear Hack Squat Machine", "Overhead Press", "Reverse V Squat",
    "Romanian Deadlift", "Seated Dumbbell Shoulder Press", "Seated Row Machine",
    "Sumo Deadlift", "V Squat"
}

# JSON 파일 읽기
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        exercises = json.load(f)
except FileNotFoundError:
    print(f"오류: '{json_file_path}' 파일을 찾을 수 없습니다.")
    exit()

# main_ex 필드 추가 또는 업데이트
for exercise in exercises:
    if exercise.get('eName') in main_exercise_names:
        exercise['main_ex'] = True
    else:
        exercise['main_ex'] = False

# 수정된 데이터로 JSON 파일 덮어쓰기
with open(json_file_path, 'w', encoding='utf-8') as f:
    json.dump(exercises, f, ensure_ascii=False, indent=4)

print(f"'{json_file_path}' 파일에 'main_ex' 필드를 추가/업데이트했습니다. 총 {len(exercises)}개의 운동 정보가 업데이트되었습니다.")