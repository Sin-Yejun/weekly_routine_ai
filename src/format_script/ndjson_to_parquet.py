import duckdb
file_name = "user"
duckdb.sql(f"""
COPY (
  SELECT * FROM read_ndjson_auto('data/json/{file_name}.ndjson')
) TO 'data/parquet/{file_name}.parquet' (FORMAT PARQUET, COMPRESSION ZSTD, OVERWRITE_OR_IGNORE 1);
""")

print(f"✅ Parquet 생성 완료: data/parquet/{file_name}.parquet")