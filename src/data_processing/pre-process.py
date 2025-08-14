import json
from pathlib import Path
from typing import Any, Dict, List, Union
from datetime import date, datetime
import polars as pl
from tqdm import tqdm

# Load mapping files for bName and eName translation
BODYPART_MAP_PATH = Path("data/multilingual-pack/bodypart_name_multi.json")
EXERCISE_MAP_PATH = Path("data/multilingual-pack/exercise_list_multi.json")

with BODYPART_MAP_PATH.open("r", encoding="utf-8") as f:
    bodypart_data = json.load(f)
bodypart_map = {item["code"]: item["en"] for item in bodypart_data}

with EXERCISE_MAP_PATH.open("r", encoding="utf-8") as f:
    exercise_data = json.load(f)
exercise_map = {item["code"]: item["en"] for item in exercise_data}


PARQUET_PATH = Path("data/parquet/workout_session.parquet")

def json_serializable(obj):
    """JSON 직렬화를 위한 커스텀 인코더"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

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
            return json.loads(x)
        except Exception:
            return x
    return x

def clean_sets_data(sets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    sets 데이터에서 불필요한 필드들을 제거합니다.
    weightLbs, state, kindof 필드를 제거하고 필수 필드만 유지합니다.
    """
    cleaned_sets = []
    for set_data in sets:
        if isinstance(set_data, dict):
            # 필요한 필드만 유지
            cleaned_set = {
                "weight": set_data.get("weight", 0),
                "reps": set_data.get("reps", 0),
                "time": set_data.get("time", 0)
            }
            cleaned_sets.append(cleaned_set)
    return cleaned_sets

def parse_session_data(raw: Union[str, list, None]) -> List[Dict[str, Any]]:
    """
    한 행의 session_data를 파싱:
    - raw가 문자열이면 json.loads
    - 내부 각 항목의 'sets'를 다시 json.loads하여 진짜 리스트로 변환
    - bName과 eName을 영어로 변환
    """
    if raw is None:
        return []

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")

    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, list):
        return []

    cleaned = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        obj = dict(obj)
        
        # bName과 eName을 영어로 변환
        if "bTextId" in obj and obj["bTextId"] in bodypart_map:
            obj["bName"] = bodypart_map[obj["bTextId"]]
        if "eTextId" in obj and obj["eTextId"] in exercise_map:
            obj["eName"] = exercise_map[obj["eTextId"]]

        if "sets" in obj:
            parsed_sets = parse_sets_field(obj["sets"])
            # sets 데이터 정리
            if isinstance(parsed_sets, list):
                obj["sets"] = clean_sets_data(parsed_sets)
            else:
                obj["sets"] = parsed_sets
        cleaned.append(obj)
    return cleaned

def fetch_recent_user_workouts(path: Path, user_id: str, limit: int = 3) -> pl.DataFrame:
    """
    특정 사용자의 가장 최근 운동 세션을 가져옵니다.
    """
    columns_to_select = ["user_id", "id", "date", "session_data", "duration"]

    lf = (
        pl.scan_parquet(str(path))
        .select(columns_to_select)
        .filter(pl.col("user_id") == user_id)
        .sort("date", descending=True)
    )

    return lf.collect(engine="streaming")

def get_all_user_ids(path: Path) -> List[str]:
    """
    Parquet 파일에서 모든 고유 사용자 ID를 가져옵니다.
    """
    df = pl.read_parquet(str(path))
    return df["user_id"].unique().to_list()

def process_user(user_id: str, output_dir: Path):
    """A single user's data processing and saving logic."""
    df = fetch_recent_user_workouts(PARQUET_PATH, user_id=user_id, limit=3)

    if df.is_empty():
        # print(f"사용자 {user_id}에 대한 데이터가 없습니다.")
        return

    records = df.to_dicts()

    for record in records:
        record["session_data"] = parse_session_data(record.get("session_data"))
    
    save_path = output_dir / f"{user_id}.json"
    
    txt = json.dumps(records, ensure_ascii=False, indent=2, default=json_serializable)
    save_path.write_text(txt, encoding="utf-8")
    # print(f"사용자 {user_id}의 최근 운동 기록을 {save_path}에 저장했습니다.")

def main() -> None:
    """
    모든 사용자의 최근 운동 기록을 가져와서 JSON 파일로 저장합니다.
    """
    output_dir = Path("data/user_workout_history")
    output_dir.mkdir(exist_ok=True, parents=True)

    user_ids = get_all_user_ids(PARQUET_PATH)
    
    print(f"총 {len(user_ids)}명의 사용자에 대해 처리를 시작합니다.")

    for user_id in tqdm(user_ids, desc="사용자 데이터 처리 중"):
        try:
            process_user(user_id, output_dir)
        except Exception as e:
            print(f"사용자 {user_id} 처리 중 오류 발생: {e}")
    
    print(f"\n모든 사용자 처리가 완료되었습니다. 결과는 {output_dir}에 저장되었습니다.")

if __name__ == "__main__":
    main()