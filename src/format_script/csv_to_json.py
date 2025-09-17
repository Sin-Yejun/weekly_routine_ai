import csv
import json
from pathlib import Path

def convert_csv_to_json(csv_path, json_path):
    csv_path = Path(csv_path)
    json_path = Path(json_path)

    exercises = []
    with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)

        # 헤더 정리: 줄바꿈/양끝 공백 제거
        header = [h.strip().replace('\n', '') for h in header]
        h = {name: i for i, name in enumerate(header)}

        # CSV에 실제 존재하는 컬럼만 안전하게 인덱스 가져오기
        code_idx        = h.get('Code')
        kname_idx       = h.get('kName')
        ename_idx       = h.get('eName')
        bname_ko_idx    = h.get('bName(Ko)')
        bname_idx       = h.get('bName')
        tool_idx        = h.get('tool')
        tool_ko_idx     = h.get('tool(ko)')
        mg_idx          = h.get('MG')
        mg_ko_idx       = h.get('MG(ko)')
        einfo_idx       = h.get('eInfoType')  # 있으면 넣고, 없으면 빈 문자열

        for row in reader:
            if not any(row):
                continue

            def get(idx):
                return row[idx].strip() if (idx is not None and idx < len(row)) else ''

            # JSON 스키마: 실제 있는 정보 위주로
            data = {
                'code':     get(code_idx),
                'kName':    get(kname_idx),      # 한국어 운동명
                'eName':    get(ename_idx),      # 영어 운동명
                'bName_ko': get(bname_ko_idx),   # 한국어 바디파트
                'bName':    get(bname_idx),      # 영어 바디파트
                'tool':     int(get(tool_idx)),       # 장비(영문)
                'tool_ko':  get(tool_ko_idx),    # 장비(한글)
                'MG':       get(mg_idx),         # 주 타겟 근육(영문)
                'MG_ko':    get(mg_ko_idx),      # 주 타겟 근육(한글)
                'eInfoType': int(get(einfo_idx)),     # 있으면 값, 없으면 ''
            }

            # 완전 빈 객체는 제외 (code나 kName/eName 중 하나라도 있으면 유지)
            if any([data['code'], data['kName'], data['eName']]):
                exercises.append(data)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open('w', encoding='utf-8') as jf:
        json.dump(exercises, jf, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    convert_csv_to_json(
        'data/02_processed/exercise_output.csv',
        'data/02_processed/exercise_output.json'
    )
    print("Conversion complete. JSON file created.")
