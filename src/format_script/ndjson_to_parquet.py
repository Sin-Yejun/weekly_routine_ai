import duckdb
duckdb.sql("""
COPY (
  SELECT * FROM read_ndjson_auto('data/workout_session.ndjson')
  WHERE duration BETWEEN 10 AND 300
) TO 'data/workout_session.parquet' (FORMAT PARQUET, COMPRESSION ZSTD, OVERWRITE_OR_IGNORE 1);
""")