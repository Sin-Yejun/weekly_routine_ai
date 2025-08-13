import duckdb
import argparse
import os

def convert_ndjson_to_parquet(input_path, output_path):
    """
    Converts an NDJSON file to a Parquet file using DuckDB.
    """
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # DuckDB query to read NDJSON and write to Parquet
    query = f"""
    COPY (
      SELECT * FROM read_ndjson_auto('{input_path}')
    ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD, OVERWRITE_OR_IGNORE 1);
    """
    
    try:
        duckdb.sql(query)
        print(f"✅ Successfully converted '{input_path}' to '{output_path}'")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert NDJSON to Parquet.")
    parser.add_argument("input_path", type=str, help="Path to the input NDJSON file.")
    parser.add_argument("output_path", type=str, help="Path for the output Parquet file.")
    
    args = parser.parse_args()
    
    convert_ndjson_to_parquet(args.input_path, args.output_path)
