
import pandas as pd
import json

def update_exercise_data():
    # 1. exercise_output.csv를 pandas DataFrame으로 읽기
    csv_path = 'data/02_processed/exercise_output.csv'
    df = pd.read_csv(csv_path)

    # 2. processed_query_result_filtered.json 읽기
    json_path = 'data/02_processed/processed_query_result_filtered.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        filtered_exercises = json.load(f)

    # 3. eTextId를 키로 하는 딕셔너리 생성
    exercise_output_map = {}
    for _, row in df.iterrows():
        # MG_point를 숫자 리스트로 변환
        mg_point_str = str(row['MG_point']).strip()
        muscle_points = [int(p.strip()) for p in mg_point_str.split('/')]

        exercise_output_map[row['eTextId']] = {
            'MG': row['MG'],
            'MG_ko': row['MG_Ko'],
            'MG_num': row['MG_num'],
            'musle_point': muscle_points
        }

    # 4. filtered_exercises 업데이트
    for exercise in filtered_exercises:
        etextid = exercise.get('eTextId')
        if etextid in exercise_output_map:
            update_data = exercise_output_map[etextid]
            exercise['MG'] = update_data['MG']
            exercise['MG_ko'] = update_data['MG_ko']
            exercise['MG_num'] = update_data['MG_num']
            exercise['musle_point'] = update_data['musle_point']
            
            # Calculate sum and counts
            musle_points = exercise['musle_point']
            exercise['musle_point_sum'] = sum(musle_points)
            exercise['up_5'] = sum(p >= 5 for p in musle_points)
            exercise['up_4'] = sum(p >= 4 for p in musle_points)
            exercise['up_3'] = sum(p >= 3 for p in musle_points)

    # 5. 업데이트된 데이터를 새로운 JSON 파일에 저장
    output_path = 'data/02_processed/processed_query_result_updated.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_exercises, f, ensure_ascii=False, indent=4)

    print(f"Updated data saved to {output_path}")
    print(f"Total exercises processed: {len(filtered_exercises)}")

if __name__ == '__main__':
    update_exercise_data()
