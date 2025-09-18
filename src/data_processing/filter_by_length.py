import json
import pandas as pd
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE_PATH = BASE_DIR / 'data' / 'finetuning_data_v5.jsonl'
OUTPUT_FILE_PATH = BASE_DIR / 'data' / 'finetuning_data_v5_filtered.jsonl'
LOWER_PERCENTILE = 0.05
HIGHER_PERCENTILE = 0.95

def filter_data_by_percentile():
    """
    Filters a JSONL file based on the percentile of the 'output' field length.
    """
    lengths = []
    print(f"Analyzing file to determine percentile thresholds: {INPUT_FILE_PATH}")
    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if 'output' in data:
                        lengths.append(len(data['output']))
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON for line: {line.strip()}")
                    continue
    except FileNotFoundError:
        print(f"Error: Input file not found at {INPUT_FILE_PATH}")
        return

    if not lengths:
        print("No 'output' fields found or file is empty.")
        return

    s = pd.Series(lengths)
    min_len = int(s.quantile(LOWER_PERCENTILE))
    max_len = int(s.quantile(HIGHER_PERCENTILE))

    print(f"Calculated thresholds:")
    print(f"- {LOWER_PERCENTILE*100:.0f}th percentile (min length): {min_len}")
    print(f"- {HIGHER_PERCENTILE*100:.0f}th percentile (max length): {max_len}")

    # Now, filter the file based on these thresholds
    count_in = 0
    count_out = 0
    print(f"\nFiltering file: {INPUT_FILE_PATH}")
    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as infile, \
             open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                count_in += 1
                try:
                    data = json.loads(line)
                    if 'output' in data:
                        length = len(data['output'])
                        if min_len <= length <= max_len:
                            outfile.write(line)
                            count_out += 1
                except json.JSONDecodeError:
                    # This warning was already printed in the first pass
                    pass
    except FileNotFoundError:
        # This error was already checked in the first pass
        pass

    print(f"\nFiltering complete.")
    print(f"Original records: {count_in}")
    print(f"Filtered records: {count_out}")
    print(f"Records removed: {count_in - count_out}")
    print(f"Filtered data saved to: {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    filter_data_by_percentile()