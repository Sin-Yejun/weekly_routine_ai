import json

# 입력 및 출력 파일 경로 설정
input_json_path = 'data/02_processed/processed_query_result.json'
output_txt_path = 'data/02_processed/eTextIds.txt'

try:
    # JSON 파일 읽기
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # eTextId 값 추출
    # JSON이 객체 리스트이고 각 객체에 'eTextId'가 있다고 가정
    if isinstance(data, list):
        e_text_ids = [item.get('eTextId') for item in data if item.get('eTextId')]
    else:
        e_text_ids = []
        print("경고: JSON 데이터가 객체 리스트가 아닙니다.")

    # 요청된 형식으로 문자열 포맷팅: "ID1","ID2",...
    formatted_ids = ','.join([f'"{id}"' for id in e_text_ids])

    # 출력 텍스트 파일에 쓰기
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(formatted_ids)

    print(f"성공적으로 {len(e_text_ids)}개의 eTextId를 {output_txt_path}에 저장했습니다.")

except FileNotFoundError:
    print(f"오류: {input_json_path} 파일을 찾을 수 없습니다.")
except json.JSONDecodeError:
    print(f"오류: {input_json_path}에서 JSON을 디코딩할 수 없습니다.")
except Exception as e:
    print(f"예상치 못한 오류가 발생했습니다: {e}")
