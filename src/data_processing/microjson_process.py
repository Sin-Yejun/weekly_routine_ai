import json
import re
import os

# 파일 경로 설정
INPUT_FILE_PATH = 'data/02_processed/exercise_micro.json'

def transform_catalog(exercise_list):
    """
    운동 데이터를 LLM 학습에 최적화된 포맷으로 변환합니다.
    - ebody(부위)별로 그룹화
    - Main/Sub 타겟 분류 (4점 기준, 없을 시 최고점 1개 Main)
    - 문자열 포맷: "이름 (도구) | Main: ... | Sub: ..."
    """
    grouped_catalog = {}

    for item in exercise_list:
        ebody = item.get('ebody', 'Other')
        ename = item.get('ename', item.get('kname', 'Unknown')) # 영문명 없으면 한글명 대채
        etool = item.get('etool', '')
        raw_micro = item.get('micro_score', '')

        # 1. micro_score 파싱: "Quads(5)" -> ("Quads", 5) 튜플 리스트로 변환
        pattern = r"(.+?)\((\d+)\)"
        parts = raw_micro.split(' / ') if raw_micro else []
        
        parsed_muscles = []
        for part in parts:
            match = re.search(pattern, part.strip())
            if match:
                muscle_name = match.group(1).strip()
                score = int(match.group(2))
                parsed_muscles.append((muscle_name, score))

        # 점수 내림차순 정렬 (로직 처리를 위해 필수)
        parsed_muscles.sort(key=lambda x: x[1], reverse=True)

        mains = []
        subs = []

        # 2. Main / Sub 분류 로직
        # 4점 이상인 근육이 하나라도 있는지 확인
        has_high_score = any(m[1] >= 4 for m in parsed_muscles)

        if has_high_score:
            # 4점 이상은 Main, 나머지는 Sub
            mains = [m for m in parsed_muscles if m[1] >= 4]
            subs = [m for m in parsed_muscles if m[1] < 4]
        else:
            # 4점 이상이 아예 없으면: 가장 높은 1개를 Main, 나머지 Sub
            if parsed_muscles:
                mains = [parsed_muscles[0]]
                subs = parsed_muscles[1:]
        
        # 3. 문자열 포맷팅
        def format_muscle_list(muscles):
            return ", ".join([f"{name}({score})" for name, score in muscles])

        main_str = format_muscle_list(mains)
        sub_str = format_muscle_list(subs)

        # 최종 문자열 조합
        formatted_string = f"{ename} ({etool})"
        if main_str:
            formatted_string += f" | Main: {main_str}"
        if sub_str:
            formatted_string += f" | Sub: {sub_str}"

        # 4. Grouping (부위별 묶기)
        if ebody not in grouped_catalog:
            grouped_catalog[ebody] = []
        
        grouped_catalog[ebody].append(formatted_string)

    return grouped_catalog

def main():
    # 1. 경로 계산 (파일명 분리 및 _cleaned 추가)
    if not os.path.exists(INPUT_FILE_PATH):
        print(f"❌ Error: 입력 파일을 찾을 수 없습니다: {INPUT_FILE_PATH}")
        return

    # 경로에서 디렉토리, 파일명, 확장자 분리
    dir_name, full_filename = os.path.split(INPUT_FILE_PATH)
    filename, ext = os.path.splitext(full_filename)
    
    # 출력 파일 경로 생성
    output_filename = f"{filename}_cleaned{ext}"
    output_file_path = os.path.join(dir_name, output_filename)

    print(f"📂 Loading data from: {INPUT_FILE_PATH}")

    # 2. JSON 파일 읽기
    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    # 3. 데이터 변환 수행
    cleaned_data = transform_catalog(data)

    # 4. JSON 파일 저장
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Transformation complete!")
        print(f"💾 Saved to: {output_file_path}")
        
        # 결과 샘플 출력 (첫 번째 키의 데이터 2개만)
        first_key = next(iter(cleaned_data))
        print(f"\n[Preview - {first_key}]")
        for sample in cleaned_data[first_key][:2]:
            print(f"- {sample}")

    except Exception as e:
        print(f"❌ Error writing JSON: {e}")

if __name__ == "__main__":
    main()