
import json

def merge_and_filter_categories():
    """
    Merges specific categories from one JSON file to another, 
    filtering them against a master list of 200 exercises.
    """
    # 파일 경로 정의
    exercises_200_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\data\02_processed\processed_query_result_200.json'
    source_categories_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\web\allowed_name_227.json'
    target_file_path = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\web\allowed_name_200.json'

    try:
        # 1. 200개 운동의 eName을 세트로 로드
        with open(exercises_200_path, 'r', encoding='utf-8') as f:
            exercises_200_data = json.load(f)
        allowed_200_set = {exercise['eName'] for exercise in exercises_200_data}

        # 2. 새로운 카테고리를 포함하는 소스 파일 로드
        with open(source_categories_path, 'r', encoding='utf-8') as f:
            source_categories_data = json.load(f)

        # 3. 업데이트할 대상 파일 로드
        with open(target_file_path, 'r', encoding='utf-8') as f:
            target_data = json.load(f)

    except FileNotFoundError as e:
        print(f"Error: Could not find a required file. {e}")
        return

    # 4. 카테고리 필터링 및 추가
    categories_to_merge = ['MBeginner', 'FBeginner', 'MNovice', 'FNovice']
    for category in categories_to_merge:
        if category in source_categories_data:
            # 200개 운동 목록에 있는 이름만 필터링
            filtered_list = [name for name in source_categories_data[category] if name in allowed_200_set]
            target_data[category] = sorted(filtered_list)
            print(f"Added/Updated '{category}' with {len(filtered_list)} items.")

    # PullUpBar는 TOOL 내부에 있으므로 별도 처리
    if 'TOOL' in source_categories_data and 'PullUpBar' in source_categories_data['TOOL']:
        pullup_bar_list = source_categories_data['TOOL']['PullUpBar']
        filtered_pullup_list = [name for name in pullup_bar_list if name in allowed_200_set]
        
        if 'TOOL' not in target_data:
            target_data['TOOL'] = {}
        target_data['TOOL']['PullUpBar'] = sorted(filtered_pullup_list)
        print(f"Added/Updated 'TOOL.PullUpBar' with {len(filtered_pullup_list)} items.")

    # 5. 사용자 지정 형식으로 파일 다시 쓰기
    with open(target_file_path, 'w', encoding='utf-8') as f:
        f.write('{\n')
        num_top_level_items = len(target_data)
        for i, (key, value) in enumerate(sorted(target_data.items())):
            line_end = ',' if i < num_top_level_items - 1 else ''
            if isinstance(value, dict):
                f.write(f'    "{key}": {{\n')
                num_sub_items = len(value)
                for j, (sub_key, sub_value) in enumerate(sorted(value.items())):
                    sub_line_end = ',' if j < num_sub_items - 1 else ''
                    list_str = json.dumps(sub_value, ensure_ascii=False)
                    f.write(f'        "{sub_key}": {list_str}{sub_line_end}\n')
                f.write(f'    }}{line_end}\n')
            else:
                list_str = json.dumps(value, ensure_ascii=False)
                f.write(f'    "{key}": {list_str}{line_end}\n')
        f.write('}\n')

    print(f"\nSuccessfully updated '{target_file_path}' with new filtered categories.")

if __name__ == "__main__":
    merge_and_filter_categories()
