
import json
import pandas as pd
from pathlib import Path
import numpy as np

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE_PATH = BASE_DIR / 'data' / 'finetuning_data_v4.jsonl'

def analyze_lengths_full_spectrum():
    """
    Reads a JSONL file and provides a detailed analysis of the 'output' length distribution.
    """
    lengths = []
    print(f"Analyzing file: {INPUT_FILE_PATH}")
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
    print("\n--- Overall Output Length Statistics ---")
    print(s.describe(percentiles=[.01, .05, .1, .25, .5, .75, .9, .95, .99, .995, .999]))

    # --- Full Distribution Histogram ---
    print("\n--- Full Distribution Histogram ---")
    if not s.empty:
        # Determine bin size dynamically
        num_bins = 20  # Adjust number of bins as needed
        min_val, max_val = s.min(), s.max()
        if min_val == max_val:
            bin_size = 1
        else:
            bin_size = (max_val - min_val) / num_bins
            bin_size = max(1, int(bin_size))

        bins = np.arange(int(min_val), int(max_val) + bin_size, bin_size)
        counts, bin_edges = np.histogram(s, bins=bins)
        max_count = counts.max()
        
        print(f"\n{len(s)} records in total.")
        print(f"Min length: {min_val}, Max length: {max_val}")
        print("\n[Full Range Histogram]")
        
        for i in range(len(counts)):
            bin_start, bin_end, count = int(bin_edges[i]), int(bin_edges[i+1]), counts[i]
            if count == 0: continue
            bar = '#' * int(60 * count / max_count if max_count > 0 else 0)
            print(f"[{bin_start: >5} - {bin_end: >5}] | {bar} ({count})")
    else:
        print("No data to display in histogram.")

if __name__ == "__main__":
    analyze_lengths_full_spectrum()
