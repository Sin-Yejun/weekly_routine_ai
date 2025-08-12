import json

def find_max_weight_and_reps(file_path, target_exercises):
    """
    지정된 JSON 파일에서 특정 운동의 최대 무게와 해당 횟수를 찾습니다.

    Args:
        file_path (str): 운동 기록이 담긴 JSON 파일의 경로.
        target_exercises (list): bTextId를 기준으로 찾고자 하는 운동 목록.

    Returns:
        dict: 각 운동별 최대 무게와 횟수 정보.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        workout_history = json.load(f)

    max_stats = {exercise: {"max_weight": 0, "reps_at_max_weight": 0} for exercise in target_exercises}

    for session in workout_history:
        for exercise in session.get("exercises", []):
            e_text_id = exercise.get("eTextId")
            if e_text_id in target_exercises:
                current_max_weight = max_stats[e_text_id]["max_weight"]
                for s in exercise.get("data", []):
                    s_weight = s.get("sWeight", 0)
                    if s_weight > current_max_weight:
                        current_max_weight = s_weight
                        max_stats[e_text_id]["max_weight"] = s_weight
                        max_stats[e_text_id]["reps_at_max_weight"] = s.get("sReps", 0)
                    # If weights are equal, check if reps are higher
                    elif s_weight == current_max_weight:
                        if s.get("sReps", 0) > max_stats[e_text_id]["reps_at_max_weight"]:
                            max_stats[e_text_id]["reps_at_max_weight"] = s.get("sReps", 0)


    return max_stats

if __name__ == "__main__":
    user_id = 72934
    file_path = f'data/json/user_{user_id}_workout_history.json'
    target_b_text_ids = ["BB_BSQT", "BB_BP", "BB_DL"]
    
    results = find_max_weight_and_reps(file_path, target_b_text_ids)
    one_rm_estimates = {exercise: round(stats["max_weight"] * (1 + stats["reps_at_max_weight"] / 30), 1) for exercise, stats in results.items()}
    # level_estimates = 
    for exercise, stats in results.items():
        print(f"운동: {exercise}")
        print(f"  최대 무게 (sWeight): {stats['max_weight']}")
        print(f"  그 때의 횟수 (sReps): {stats['reps_at_max_weight']}")
        print(f"  예상 1RM: {one_rm_estimates[exercise]}")
        print("-" * 20)
