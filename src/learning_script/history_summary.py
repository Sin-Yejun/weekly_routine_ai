# -*- coding: utf-8 -*-
"""
weekly_streak_dataset.parquet의 prev_weeks를 사람이 읽기 좋은 텍스트로 변환.

- prev_weeks 예시 원소:
  { "week": 1, "week_start": "2025-08-25", "weekly_exercises": [...] }

- 각 weekly_exercises는 [ { "_type":"session_header", ... }, exercise1, exercise2, ... , { "_type":"session_header", ... }, ... ]
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import polars as pl

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
PARQUET_PATH = Path("data/02_processed/parquet/weekly_streak_dataset.parquet")

# multilingual pack (영문 매핑 사용)
BODYPART_MAP_PATH = Path("data/03_core_assets/multilingual-pack/bodypart_name_multi.json")
EXERCISE_MAP_PATH = Path("data/03_core_assets/multilingual-pack/exercise_list_multi.json")

with BODYPART_MAP_PATH.open("r", encoding="utf-8") as f:
    _bodypart_data = json.load(f)
BODYPART_MAP = {item["code"]: item["en"] for item in _bodypart_data}

with EXERCISE_MAP_PATH.open("r", encoding="utf-8") as f:
    _exercise_data = json.load(f)
EXERCISE_MAP = {item["code"]: item["en"] for item in _exercise_data}

# ── 유틸 ──────────────────────────────────────────────────────────────────────
def _to_pyobj(x: Any) -> Any:
    """JSON이 문자열/바이너리여도 파이썬 객체로 변환."""
    if isinstance(x, (list, dict)) or x is None:
        return x
    if isinstance(x, (bytes, bytearray, memoryview)):
        try:
            return json.loads(bytes(x).decode("utf-8"))
        except Exception:
            return None
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return None
    return None

def _parse_sets_field(x: Any) -> Any:
    """세트 필드가 문자열(JSON)인 경우 리스트로 변환."""
    if isinstance(x, str):
        s = x.strip()
        try:
            return json.loads(s)
        except Exception:
            return x
    return x

def _compress_sets(sets: List[Dict]) -> str:
    """세트 리스트를 '7x20 / 5x60 / 1800s' 식으로 압축."""
    if not sets:
        return ""
    out: List[str] = []
    for s in sets:
        if not isinstance(s, dict):
            continue
        reps   = s.get("reps")
        weight = s.get("weight")
        time   = s.get("time")

        if time and isinstance(time, (int, float)) and time > 0:
            out.append(f"{int(time)}s")
            continue

        # 정수 무게는 소수점 제거
        w_disp = None
        if isinstance(weight, (int, float)):
            w_disp = int(weight) if float(weight).is_integer() else weight

        base = f"{reps}" if reps is not None else ""
        if w_disp not in (None, 0, 0.0):
            base += f"x{w_disp}"
        out.append(base or "0")
    return " / ".join(out)

def _exercise_line(ex: Dict[str, Any]) -> str:
    """운동 1개를 텍스트 한 줄로."""
    # 이름 매핑
    b_name = ex.get("bTextId")[4:]
    if not b_name and (bid := ex.get("bTextId")):
        b_name = BODYPART_MAP.get(bid, bid)

    e_name = ex.get("eName")
    etid   = ex.get("eTextId")
    if not e_name and etid:
        if etid.startswith("CUSTOM"):
            custom_id = etid.replace("CUSTOM_", "").replace("CUSTOM", "")
            e_name = f"CUSTOM_WORKOUT_{custom_id}" if custom_id else "CUSTOM_WORKOUT"
        else:
            e_name = EXERCISE_MAP.get(etid, etid)

    # sets 정규화
    sets_obj = _parse_sets_field(ex.get("sets"))
    if not isinstance(sets_obj, list):
        sets_obj = []
    num_sets = len(sets_obj)
    comp = _compress_sets(sets_obj)

    return f"{(b_name or 'N/A')},{(etid or 'N/A')},{num_sets}sets: {comp}"

def _summarize_weekly_exercises(weekly_exercises: Any) -> List[str]:
    """
    weekly_exercises 배열을 읽어 세션 단위로 텍스트 블록 생성.
    - session_header 등장 시: 'Session #k - Duration: Xm'
    - 뒤따르는 exercise 항목을 요약 라인으로
    """
    we = _to_pyobj(weekly_exercises)
    if not isinstance(we, list):
        return ["(no data)"]

    lines: List[str] = []
    session_idx = 0
    for item in we:
        if isinstance(item, dict) and item.get("_type") == "session_header":
            session_idx += 1
            dur = item.get("duration")
            dur_str = f" - Duration: {int(dur)}min" if isinstance(dur, (int, float)) else ""
            wkday = item.get("workout_day")
            wkday_str = f" ({wkday})" if wkday else ""
            lines.append(f"Day #{session_idx}")
        elif isinstance(item, dict):
            lines.append(_exercise_line(item))
        # 기타 타입은 무시
    return lines if lines else ["(empty)"]

# ── 메인 API ──────────────────────────────────────────────────────────────────
def get_prev_weeks_texts(
    limit_rows: int = 1,
    user_id: Optional[int] = None,
    max_prev: int = 4
) -> List[str]:
    """
    weekly_streak_dataset.parquet에서 prev_weeks를 텍스트로 요약.
    - limit_rows: 상위 몇 행(최신 week_start 기준)까지 출력할지
    - user_id: 특정 사용자만 필터(없으면 전체 중 최신부터)
    - max_prev: prev_weeks 중 앞의 몇 개만 사용할지(기본 4)
    """
    # 필요한 컬럼만 스캔 → 성능
    lf = pl.scan_parquet(str(PARQUET_PATH)).select(
        "user_id", "week_start", "prev_weeks"
    )
    if user_id is not None:
        lf = lf.filter(pl.col("user_id") == user_id)

    # 최신 week_start 우선
    df = lf.sort("week_start", descending=True).limit(limit_rows).collect()

    texts: List[str] = []
    for row in df.iter_rows(named=True):
        uid = row["user_id"]
        wks = row["week_start"]
        prev_weeks = _to_pyobj(row.get("prev_weeks"))

        header = f"[user {uid}] Anchor week_start={wks}"
        lines  = [header]

        if isinstance(prev_weeks, list) and prev_weeks:
            # prev_weeks는 [{week:1, week_start:..., weekly_exercises:[...]}] 형태
            # 최신→과거 순으로 최대 max_prev개만
            for item in prev_weeks[:max_prev]:
                if not isinstance(item, dict):
                    continue
                wk_no = item.get("week") or "?"
                wk_start = item.get("week_start")
                lines.append(f"\nPrev Week #{wk_no}")
                for ln in _summarize_weekly_exercises(item.get("weekly_exercises")):
                    lines.append(ln)
        else:
            lines.append("(no prev_weeks)")

        texts.append("\n".join(lines))

    return texts

# ── 스크립트 실행 예시 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 최신 3행의 prev_weeks 요약을 출력 (사용자 지정 가능)
    out = get_prev_weeks_texts(limit_rows=1, user_id=3236, max_prev=4)
    for t in out:
        print(t)
        print("-" * 80)
