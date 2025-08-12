# pip install polars pyarrow (필요 시)
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
import polars as pl

PARQUET_PATH = Path("data/parquet/workout_session.parquet")
LIMIT = 3          # 전부 읽을 땐 None 로 변경
SAVE_PATH = Path("data/merged_workout.json")

def parse_sets_field(x: Any) -> Any:
    """
    session_data 내부 각 오브젝트의 'sets' 필드는 문자열(JSON)로 들어있을 수 있다.
    - 문자열이면 json.loads로 리스트로 변환
    - 이미 리스트면 그대로 반환
    - 실패 시 원본 유지
    """
    if isinstance(x, str):
        x = x.strip()
        try:
            return json.loads(x)  # "[{...}, {...}]" → [{...}, {...}]
        except Exception:
            return x
    return x

def parse_session_data(raw: Union[str, list, None]) -> List[Dict[str, Any]]:
    """
    한 행의 session_data를 파싱:
    - raw가 문자열이면 json.loads
    - 내부 각 항목의 'sets'를 다시 json.loads하여 진짜 리스트로 변환
    """
    if raw is None:
        return []

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")

    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, list):
        raise ValueError("session_data의 최상위 구조는 리스트여야 합니다.")

    cleaned = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        obj = dict(obj)  # 얕은 복사
        if "sets" in obj:
            obj["sets"] = parse_sets_field(obj["sets"])
        cleaned.append(obj)
    return cleaned

def fetch_rows_from_parquet(path: Path, limit: Union[int, None] = None) -> List[Tuple[int, Any]]:
    """
    Parquet에서 duration, session_data 컬럼만 읽어 (duration, session_data) 튜플 리스트 반환.
    limit가 None이면 전체, 숫자면 앞에서부터 limit개.
    """
    lf = pl.scan_parquet(str(path)).select(["duration", "session_data"])
    if limit is not None:
        lf = lf.limit(limit)

    rows: List[Tuple[int, Any]] = []
    # streaming=True 로 메모리 절약
    for d, s in lf.collect(streaming=True).iter_rows():
        # duration이 None인 경우 대비
        d = 0 if d is None else int(d)
        rows.append((d, s))
    return rows

def build_pretty_json(rows: List[Tuple[int, Any]]) -> Dict[str, Any]:
    """
    여러 행을 받아 '예쁜' JSON으로 변환.
    - 모든 duration이 같으면: {"duration": <값>, "items": [모든 운동 합침]}
    - 다르면: {"sessions": [{"duration": d, "items": [...]}, ...]}
    """
    parsed = []
    durations = set()

    for duration, session_data in rows:
        items = parse_session_data(session_data)
        parsed.append({"duration": duration, "items": items})
        durations.add(duration)

    if len(parsed) == 0:
        return {"duration": 0, "items": []}

    if len(parsed) == 1:
        return parsed[0]

    if len(durations) == 1:
        all_items: List[Dict[str, Any]] = []
        for p in parsed:
            all_items.extend(p["items"])
        return {"duration": parsed[0]["duration"], "items": all_items}

    return {"sessions": parsed}

def main() -> None:
    rows = fetch_rows_from_parquet(PARQUET_PATH, limit=LIMIT)
    result = build_pretty_json(rows)
    txt = json.dumps(result, ensure_ascii=False, indent=2)
    print(txt)
    SAVE_PATH.write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
