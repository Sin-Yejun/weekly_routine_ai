import json
import os
from datetime import datetime, timedelta

def analyze_top_workout_weeks(json_path: str):
    """
    Finds the top 3 most active weeks and calculates their average workout count.

    Args:
        json_path (str): The path to the workout history JSON file.
    """
    if not os.path.exists(json_path):
        print(f"오류: JSON 파일을 찾을 수 없습니다: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        workouts = json.load(f)

    if not workouts:
        print("운동 기록이 없습니다.")
        return
    print(f"총 {len(workouts)}개의 운동 기록이 있습니다.")
    if len(workouts) <= 10:
        print("총 운동 횟수가 10회 이하이므로, 주간 운동 횟수를 4로 설정합니다.")
        return

    dates = []
    for w in workouts:
        try:
            dates.append(datetime.fromisoformat(w['date']))
        except (TypeError, ValueError):
            dates.append(datetime.fromtimestamp(w['date'] / 1000))
    
    dates.sort()

    if not dates:
        print("운동 기록 날짜를 분석할 수 없습니다.")
        return

    weekly_counts = []
    # Use a set to store the start date of weeks already processed to avoid duplicates
    processed_weeks = set()

    for i, start_date in enumerate(dates):
        # Define a week by its starting Monday
        week_start_date = start_date - timedelta(days=start_date.weekday())
        if week_start_date in processed_weeks:
            continue
        
        processed_weeks.add(week_start_date)
        week_end_date = week_start_date + timedelta(days=7)
        
        workouts_in_week = [d for d in dates if week_start_date <= d < week_end_date]
        if workouts_in_week:
            weekly_counts.append(len(workouts_in_week))

    if not weekly_counts:
        print("주간 운동 횟수를 계산할 수 없습니다.")
        return

    # Sort the counts in descending order
    weekly_counts.sort(reverse=True)

    print("=== 상위 5주 운동 빈도 분석 ===")
    top_n = 5
    top_counts = weekly_counts[:top_n]

    if not top_counts:
        print("분석할 운동 기록이 충분하지 않습니다.")
        return

    print(f"가장 운동을 많이 한 주의 횟수: {top_counts}")

    average_freq = round(sum(top_counts) / len(top_counts))
    print(f"\n상위 {len(top_counts)}개 주의 평균 운동 횟수는 약 {average_freq}회입니다.")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    user_id = 12  # Example user ID, change as needed
    input_json_path = os.path.join(project_root, 'data', 'json', f'user_{user_id}_workout_history.json')

    analyze_top_workout_weeks(input_json_path)

