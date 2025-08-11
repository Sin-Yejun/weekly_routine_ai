import sqlite3
import json

# --- 설정 ---
# 데이터베이스 파일 경로
DB_PATH = 'data/hajaSQLite.db'
# 실행할 SQL 쿼리가 담긴 파일 경로
SQL_FILE_PATH = 'data/-- SQLite.sql'
# 결과를 저장할 JSON 파일 경로
OUTPUT_JSON_PATH = 'data/query_result.json'

def execute_sql_and_save_as_json():
    """
    SQL 파일의 쿼리를 SQLite 데이터베이스에서 실행하고 결과를 JSON 파일로 저장합니다.
    """
    try:
        # 1. SQL 쿼리 읽기
        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
            sql_query = f.read()
        print(f"성공적으로 SQL 파일을 읽었습니다: {SQL_FILE_PATH}")

        # 2. 데이터베이스 연결
        conn = sqlite3.connect(DB_PATH)
        # 결과를 딕셔너리 형태로 받기 위해 row_factory 설정
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        print(f"성공적으로 데이터베이스에 연결했습니다: {DB_PATH}")

        # 3. SQL 쿼리 실행
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        print("SQL 쿼리를 성공적으로 실행했습니다.")

        # 4. 결과를 딕셔너리 리스트로 변환
        result_list = [dict(row) for row in rows]

        # 5. JSON 파일로 저장
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as json_file:
            # ensure_ascii=False로 한글이 깨지지 않도록 설정하고, indent=4로 가독성 좋게 저장
            json.dump(result_list, json_file, ensure_ascii=False, indent=4)
        
        print(f"성공적으로 결과를 JSON 파일에 저장했습니다: {OUTPUT_JSON_PATH}")

    except FileNotFoundError as e:
        print(f"[오류] 파일을 찾을 수 없습니다: {e.filename}")
    except sqlite3.Error as e:
        print(f"[데이터베이스 오류] {e}")
    except Exception as e:
        print(f"[알 수 없는 오류] {e}")
    finally:
        # 연결 종료
        if 'conn' in locals() and conn:
            conn.close()
            print("데이터베이스 연결을 닫았습니다.")

if __name__ == '__main__':
    execute_sql_and_save_as_json()
