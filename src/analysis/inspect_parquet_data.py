# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
INPUT_PARQUET_PATH = DATA_DIR / '02_processed' / 'parquet' / 'weekly_streak_dataset.parquet'

def inspect_parquet_data():
    """Loads the parquet file and prints summary information to debug data issues."""
    logging.info(f"Inspecting file: {INPUT_PARQUET_PATH}")

    try:
        df = pd.read_parquet(INPUT_PARQUET_PATH)
    except FileNotFoundError:
        logging.error(f"File not found at: {INPUT_PARQUET_PATH}")
        return
    except Exception as e:
        logging.error(f"An error occurred while reading the parquet file: {e}")
        return

    print("\n--- DataFrame Info ---")
    df.info()

    print("\n--- DataFrame Columns ---")
    print(df.columns.tolist())

    print("\n--- First 5 Rows ---")
    print(df.head())

    if 'week_level' in df.columns:
        print("\n--- Value Counts for 'week_level' ---")
        print(df['week_level'].value_counts(dropna=False))
    else:
        logging.warning("Column 'week_level' not found in the DataFrame.")

    if 'gender' in df.columns:
        print("\n--- Value Counts for 'gender' ---")
        print(df['gender'].value_counts(dropna=False))
    else:
        logging.warning("Column 'gender' not found in the DataFrame.")

if __name__ == "__main__":
    inspect_parquet_data()
