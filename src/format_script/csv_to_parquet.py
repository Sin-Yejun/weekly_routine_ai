# pip install pandas pyarrow
import pandas as pd

csv_path = "data/02_processed/weekly_streak_dataset.csv"
parquet_path = "data/02_processed/parquet/weekly_streak_dataset.parquet"

df = pd.read_csv(csv_path)  # 필요시 dtype={"colA": "int64"} 등 지정
df.to_parquet(parquet_path, index=False, compression="snappy")  # snappy/zstd/gzip