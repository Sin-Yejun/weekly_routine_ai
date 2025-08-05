# -*- coding: utf-8 -*-
"""
이 스크립트는 SQLite 데이터베이스에서 최근 운동 기록을 조회하여
가독성 좋은 텍스트 형식으로 요약합니다.

주요 기능:
- DB에서 최근 5일간의 운동 데이터를 가져옵니다.
- 데이터를 가공하여 운동별, 세트별로 정리합니다.
- 각 운동 세션을 텍스트로 요약하여 리스트로 반환합니다.
"""
import json
from typing import List, Dict
import sqlite3, json, pandas as pd
from pathlib import Path

def get_latest_workout_texts() -> list[str]:
    """
    데이터베이스에서 최근 운동 기록을 가져와 텍스트로 요약하여 반환합니다.
    """
    # ───────────────────────────────────────────────────────────────
    # 0. 설정값
    # ───────────────────────────────────────────────────────────────
    DB_PATH = Path("data/hajaSQLite.db")     # DB 파일 경로
    KG2LBS   = 2.20462                      # kg → lbs 변환 상수

    # ───────────────────────────────────────────────────────────────
    # 1. SQL 쿼리 정의
    #   - 'waiting' 상태가 아닌 완료된 세트만 조회합니다.
    #   - 시스템 기본 운동(e_from_user = 0)을 기준으로 최신 5일치 d_id를 가져옵니다.
    # ───────────────────────────────────────────────────────────────
    SQL = """
        WITH latest_day_ids AS (
            SELECT DISTINCT d.d_id
            FROM day_exercise d
            JOIN setrep   s ON d.de_id = s.de_id
            JOIN exercise e ON d.e_id  = e.e_id
            WHERE e.e_from_user = 0
            AND s.s_status    != 'waiting'
            ORDER BY d.d_id DESC
            LIMIT 5
        )
        SELECT da.d_date, d.d_id,                 
            b.b_name, b.b_text_id, 
            s.s_kind, s.s_reps, s.s_rpe, s.s_time, s.s_weight,
            e.e_name, e.e_info_type, e.e_text_id,
            e.t_id
        FROM latest_day_ids l
        JOIN day_exercise d ON l.d_id = d.d_id
        JOIN day da ON da.d_id = d.d_id
        JOIN exercise      e ON d.e_id = e.e_id
        JOIN setrep        s ON d.de_id = s.de_id
        JOIN bodypart      b ON b.b_id = e.b_id
        WHERE e.e_from_user = 0
        AND s.s_status    != 'waiting'
        ORDER BY d.de_id, s.s_id;
    """

    # ───────────────────────────────────────────────────────────────
    # 2. DB 조회 → DataFrame으로 변환
    # ───────────────────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(SQL, conn)

    # ───────────────────────────────────────────────────────────────
    # 3. 데이터 가공 및 구조화 함수
    # ───────────────────────────────────────────────────────────────
    def kg_to_lbs(kg: float) -> int:
        """kg을 lbs로 변환하고, 소수점을 반올림합니다."""
        return int(round(kg * KG2LBS)) if kg else 0

    def build_structured_data(df: pd.DataFrame) -> list[dict]:
        """
        DataFrame을 날짜별, 운동별로 그룹화하여 Python 객체(딕셔너리 리스트)로 재구성합니다.
        이 구조는 후속 텍스트 요약 단계에서 사용됩니다.
        """
        days = []
        # d_id를 기준으로 날짜별로 그룹화
        for d_id, df_day in df.groupby("d_id", sort=False):
            d_date = df_day["d_date"].iloc[0].split(" ")[0] 
            exercise_objs, de_arr_index = [], 0
            
            # 운동(e_name) 단위로 다시 그룹화
            group_cols = ["b_name", "b_text_id", "e_name", "e_info_type", "e_text_id", "t_id"]
            for keys, g in df_day.groupby(group_cols, sort=False):
                b_name, b_text_id, e_name, e_info_type, e_text_id, t_id = keys
                
                # 각 운동에 포함된 세트 목록 생성
                sets = [{
                    "sKind"     : row["s_kind"],
                    "sReps"     : int(row["s_reps"]) if row["s_reps"] is not None else None,
                    "sRpe"      : row["s_rpe"],
                    "sStatus"   : "done",              # 'waiting'이 제외되었으므로 'done'으로 간주
                    "sTime"     : int(row["s_time"]),
                    "sWeight"   : float(row["s_weight"]) if row["s_weight"] is not None else 0,
                    "sWeightLbs": kg_to_lbs(row["s_weight"]) if row["s_weight"] is not None else 0
                } for _, row in g.iterrows()]

                # 운동 객체 생성
                exercise_objs.append({
                    "bName"            : b_name,
                    "bTextId"          : b_text_id,
                    "data"             : sets,
                    "deArrIndex"       : de_arr_index,
                    "deSecondUnit"     : None,
                    "deSortIndex"      : 1000,
                    "deSupersetMainDeId": None,
                    "eInfoType"        : int(e_info_type),
                    "eName"            : e_name,
                    "eTextId"          : e_text_id,
                    "tId"              : int(t_id)
                })
                de_arr_index += 1
            
            # 최종적으로 날짜 객체에 운동 목록 추가
            days.append({"dId": int(d_id), "date": d_date, "exercises": exercise_objs})
        return days

    # ───────────────────────────────────────────────────────────────
    # 4. 텍스트 요약 생성 함수
    # ───────────────────────────────────────────────────────────────
    
    def compress_sets(sets: List[Dict]) -> str:
        """
        세트 리스트를 '7x20 / 5x60(Drop)'과 같은 압축된 문자열로 변환합니다.
        - reps: 반복 횟수
        - weight: 무게 (kg)
        - kind: 세트 종류 (1: 웜업, 2: 드롭, 3: 실패)
        """
        kind_token = {1: "w", 2: "d", 3: "f"}
        out = []
        for s in sets:
            reps   = s.get("reps")
            weight = s.get("weight")
            token  = kind_token.get(s.get("kind"))
            rpe = s.get("rpe")

            # 무게(kg)가 정수이면 소수점 없이 표시 (예: 60.0 → 60)
            w_disp = int(weight) if weight is not None and float(weight).is_integer() else weight
            
            # reps와 weight를 조합하여 기본 문자열 생성
            base = f"{reps}" if w_disp == 0 else f"{reps}x{w_disp}"
            
            # kind 토큰이 있으면 괄호와 함께 추가
            suffix1 = f"{token}" if token else ""
            
            # RPE가 있는 경우에만 표시 (nan 값 제외)
            suffix2 = ""
            if pd.notna(rpe) and rpe:
                rpe_disp = int(rpe) if float(rpe).is_integer() else rpe
                suffix2 = f" (rpe-{rpe_disp})"

            out.append(base + suffix1 + suffix2)

        return " / ".join(out)

    def text_summary(day: Dict, order: int) -> str:
        """
        하루치 운동 데이터를 받아 전체 텍스트 요약을 생성합니다.
        """
        header = f"최근 {order}회차"
        lines  = [header]
        for ex in day["exercises"]:
            # 부위, 운동 이름, 세트 수, 세트 상세 정보 포함
            line = (
                f"{ex['bName']:<3}- {ex['eName']} ({ex['eTextId']}) "
                f"{len(ex['data'])}세트: "
                f"{compress_sets([{'reps':d['sReps'], 'weight':d['sWeight'],'kind': d['sKind'], 'rpe': d['sRpe']} for d in ex['data']])}"
            )
            lines.append(line)
        return "\n".join(lines)

    # ───────────────────────────────────────────────────────────────
    # 5. 메인 로직: 데이터 처리 및 텍스트 요약 생성
    # ───────────────────────────────────────────────────────────────
    
    # DB에서 가져온 데이터를 처리하기 쉬운 구조로 변환
    structured_data = build_structured_data(df)
    
    # dId(날짜 ID)를 기준으로 내림차순 정렬 (최신순)
    workout_days = sorted(structured_data, key=lambda d: d["dId"], reverse=True)

    # 각 날짜별로 텍스트 요약 생성
    texts = []
    for idx, day in enumerate(workout_days, 1):
        texts.append(text_summary(day, idx))
        
    return texts

# ───────────────────────────────────────────────────────────────
# 스크립트 직접 실행 시 결과 출력
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    workout_texts = get_latest_workout_texts()
    for text in workout_texts:
        print(text)
        print()