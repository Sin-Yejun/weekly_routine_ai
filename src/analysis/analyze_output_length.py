import json
import pandas as pd
from pathlib import Path
import numpy as np

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE_PATH = BASE_DIR / 'data' / 'finetuning_data_v4.jsonl'

def analyze_lengths_full_spectrum():
    """
    Reads a JSONL file and provides a detailed analysis of both the lower
    and upper ends of the 'output' length distribution.
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

    # --- Detailed Analysis of Lower Distribution ---
    print("\n--- Lower Distribution Details (Lengths < 1000) ---")
    lower_s = s[s < 1000]
    if not lower_s.empty:
        print(f"\n{len(lower_s)} records (out of {len(s)}) have length < 1000.")
        print("\n[Low-End Histogram (lengths < 1000)]")
        bins = np.arange(0, min(1000, lower_s.max() + 50), 50)
        counts, bin_edges = np.histogram(lower_s, bins=bins)
        max_count = counts.max()
        for i in range(len(counts)):
            bin_start, bin_end, count = int(bin_edges[i]), int(bin_edges[i+1]), counts[i]
            if count == 0: continue
            bar = '█' * int(60 * count / max_count if max_count > 0 else 0)
            print(f"[{bin_start: >4} - {bin_end: >4}] | {bar} ({count})")
    else:
        print("No data points with length < 1000.")

    # --- Detailed Analysis of Upper Distribution ---
    print("\n--- Upper Distribution Details (Lengths > 2200) ---")
    upper_s = s[s > 2200]
    if not upper_s.empty:
        print(f"\n{len(upper_s)} records (out of {len(s)}) have length > 2200.")
        print("\n[High-End Percentiles]")
        print(upper_s.describe(percentiles=[.1, .2, .3, .4, .5, .6, .7, .8, .9, .95, .99]))
        print("\n[High-End Histogram (lengths > 2200)]")
        bins = np.arange(int(upper_s.min()), int(upper_s.max()) + 200, 200)
        counts, bin_edges = np.histogram(upper_s, bins=bins)
        max_count = counts.max()
        for i in range(len(counts)):
            bin_start, bin_end, count = int(bin_edges[i]), int(bin_edges[i+1]), counts[i]
            if count == 0: continue
            bar = '█' * int(60 * count / max_count if max_count > 0 else 0)
            print(f"[{bin_start: >5} - {bin_end: >5}] | {bar} ({count})")
    else:
        print("No data points with length > 2200.")

if __name__ == "__main__":
    analyze_lengths_full_spectrum()
