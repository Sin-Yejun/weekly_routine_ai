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

    # ── Preprocessing & Mapping ──────────────────────────────
    level = int(row.level)
    career = {0: "Beginner", 1: "Novice", 2: "Intermediate"}.get(level, "Advanced")

    # json_extract may include quotes, so strip("\"")
    main_text = str(row.main_text).strip("\"")
    sub_text  = str(row.sub_text).strip("\"")
    frequency = int(row.frequency)

    # ── Final Text ────────────────────────────────
    return (
        f"- Gender : {row.gender}\n"
        f"- Weight : {row.weight}\n"
        #f"- 운동 목표 : [{main_text}] - {sub_text}\n"
        #f"- 운동 목표 : [다이어트 성공하기] - 이번엔 살을 꼭 빼고 싶어요.\n"
        f"- Career : {career}\n"
        f"- Weekly Workout Frequency : {frequency}"
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