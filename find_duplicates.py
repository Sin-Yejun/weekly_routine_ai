
import json

def find_duplicates_in_test_cases(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    duplicates_found = []

    for i, test_case in enumerate(test_cases):
        is_duplicate_found_in_case = False
        for week_key in ['week1', 'week2', 'week3', 'week4']:
            if week_key in test_case:
                for day_key, exercises in test_case[week_key].items():
                    if len(exercises) != len(set(exercises)):
                        if not is_duplicate_found_in_case:
                            duplicates_found.append({
                                "case_index": i,
                                "gender": test_case.get("gender"),
                                "level": test_case.get("level"),
                                "split_id": test_case.get("split_id"),
                                "freq": test_case.get("freq"),
                                "week": week_key,
                                "day": day_key,
                                "duplicates": [item for item in exercises if exercises.count(item) > 1]
                            })
                            is_duplicate_found_in_case = True
                        else:
                            # Find the existing entry and append the new duplicate info
                            for entry in duplicates_found:
                                if entry["case_index"] == i:
                                    entry["duplicates"].extend([item for item in exercises if exercises.count(item) > 1])
                                    break
    
    return duplicates_found

if __name__ == "__main__":
    duplicates = find_duplicates_in_test_cases("web/test_cases.json")
    if duplicates:
        print("중복된 운동이 발견된 테스트 케이스:")
        for duplicate in duplicates:
            print(f"  - gender: {duplicate['gender']}, level: {duplicate['level']}, split_id: {duplicate['split_id']}, freq: {duplicate['freq']}")
            print(f"    - week: {duplicate['week']}, day: {duplicate['day']}")
            print(f"    - 중복된 운동: {list(set(duplicate['duplicates']))}")
    else:
        print("중복된 운동이 없습니다.")

