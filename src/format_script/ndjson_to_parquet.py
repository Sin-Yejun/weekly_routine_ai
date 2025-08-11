import duckdb
duckdb.sql("""
COPY (
  SELECT * FROM read_ndjson_auto('data/workout_session.ndjson')
) TO 'data/workout_session.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
""")