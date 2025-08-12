import os
import pyarrow.parquet as pq
user_parquet_path = 'data/parquet/user.parquet'
print(pq.read_schema(user_parquet_path))
