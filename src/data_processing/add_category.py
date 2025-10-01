
import pandas as pd
import json

def add_category_to_exercises():
    # 1. category.csv를 pandas DataFrame으로 읽기
    category_csv_path = 'data/02_processed/category.csv'
    category_df = pd.read_csv(category_csv_path)

    # 2. processed_query_result_filtered.json 읽기
    json_path = 'data/02_processed/processed_query_result_filtered.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        exercises = json.load(f)

    # 3. eName을 키로 하는 카테고리 딕셔너리 생성
    category_map = pd.Series(category_df.category.values, index=category_df.eName).to_dict()

    # 4. exercises에 category 필드 추가
    for exercise in exercises:
        ename = exercise.get('eName')
        exercise['category'] = category_map.get(ename, None)

    # 5. 업데이트된 데이터를 새로운 JSON 파일에 저장
    output_path = 'data/02_processed/processed_query_result_filtered.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(exercises, f, ensure_ascii=False, indent=4)

    print(f"Updated data with categories saved to {output_path}")
    print(f"Total exercises processed: {len(exercises)}")

if __name__ == '__main__':
    add_category_to_exercises()
