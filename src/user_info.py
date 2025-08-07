from pathlib import Path
import sqlite3, pandas as pd, json

DB_PATH = Path("data/hajaSQLite.db")

def get_user_profile_text() -> str:
    SQL = """
    SELECT gender,
           weight,
           json_extract(goal,'$.level')        AS level,
           json_extract(goal,'$.goal.mainText') AS main_text,
           json_extract(goal,'$.goal.subText')  AS sub_text,
           json_extract(goal,'$.frequency')     AS frequency
    FROM setting
    """

    with sqlite3.connect(DB_PATH) as conn:
        row = pd.read_sql_query(SQL, conn).iloc[0]

    # ── 전처리 & 매핑 ──────────────────────────────
    level = int(row.level)
    career = {0: "왕초보", 1: "초보자", 2: "중급자"}.get(level, "고급자")

    # json_extract 가 문자열에 따옴표를 포함할 수 있어 strip("\"")
    main_text = str(row.main_text).strip("\"")
    sub_text  = str(row.sub_text).strip("\"")
    frequency = int(row.frequency)

    # ── 최종 텍스트 ────────────────────────────────
    return (
        f"- 성별 : {row.gender}\n"
        f"- 체중 : {row.weight}\n"
        #f"- 운동 목표 : [{main_text}] - {sub_text}\n"
        #f"- 운동 목표 : [다이어트 성공하기] - 이번엔 살을 꼭 빼고 싶어요.\n"
        f"- 운동 경력 : {career}\n"
        f"- 주간 운동 수행 횟수 : {frequency}회"
    )

def get_user_frequency() -> int:
    """사용자의 주간 운동 빈도를 반환합니다."""
    SQL = "SELECT json_extract(goal,'$.frequency') AS frequency FROM setting"
    with sqlite3.connect(DB_PATH) as conn:
        frequency = pd.read_sql_query(SQL, conn)["frequency"].item()
    return int(frequency)


# 예시 호출
if __name__ == "__main__":
    print(get_user_profile_text())
    print(f"주간 운동 횟수: {get_user_frequency()}")