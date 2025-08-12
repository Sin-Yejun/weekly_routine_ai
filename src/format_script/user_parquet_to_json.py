import os, json
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
import pandas as pd

def convert_workout_data_to_json(user_id: int, output_path: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    parquet_path = os.path.join(project_root, 'data', 'parquet', 'user.parquet')

    if not os.path.exists(parquet_path):
        print(f"Error: Parquet file not found at {parquet_path}")
        return

    # 1) dataset로 로드 후, 최상위 struct 컬럼 이름 자동 탐지 (예: 'u')
    user_ds = ds.dataset(parquet_path, format="parquet")
    struct_cols = [f.name for f in user_ds.schema if pa.types.is_struct(f.type)]
    if not struct_cols:
        print("Error: No struct column found in user.parquet")
        return
    ucol = struct_cols[0]  # 보통 1개

    # 2) struct 필드(id)로 필터 푸시다운 + struct 컬럼만 읽기 → flatten
    try:
        tbl = user_ds.to_table(
            filter=ds.field(ucol).struct_field("id") == user_id,
            columns=[ucol]
        ).flatten()
    except Exception:
        # 일부 환경에서 struct_field 필터가 안 먹으면 전체 읽고 판다스에서 필터
        tbl = user_ds.to_table(columns=[ucol]).flatten()

    # 3) 컬럼명 접두사 제거 (예: 'u.id' -> 'id')
    df = tbl.to_pandas()
    df.columns = [c.split(".")[-1] for c in df.columns]

    # 보수적 필터 (혹시 2단계가 실패했을 경우 대비)
    if "id" not in df.columns:
        print(f"Error: 'id' column not found. Columns={list(df.columns)}")
        return
    df = df[df["id"] == user_id]

    if df.empty:
        print(f"Error: User with ID {user_id} not found in {parquet_path}")
        return
    
    # NaN → None 변환
    df = df.where(pd.notnull(df), -1)

    # 4) JSON 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

    print(f"Successfully converted data for user {user_id} to {output_path}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    user_id = 9
    output_file_path = os.path.join(project_root, 'data', 'json', f'user_{user_id}_info.json')
    convert_workout_data_to_json(user_id, output_file_path)


