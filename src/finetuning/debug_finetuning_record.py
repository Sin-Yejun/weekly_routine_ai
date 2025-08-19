# -*- coding: utf-8 -*-
import json
import logging
import re
import argparse
from pathlib import Path

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
FINETUNING_FILE_PATH = '/Users/yejunsin/Documents/weekly_routine_ai/data/finetuning_data_v2.jsonl'

def debug_specific_record(line_number: int):
    """
    Reads a specific line from the .jsonl file and prints detailed debugging info.
    """
    # if not FINETUNING_FILE_PATH.exists():
    #     logging.error(f"Debug failed: File not found at {FINETUNING_FILE_PATH}")
    #     return

    logging.info(f"Attempting to read line {line_number} from {FINETUNING_FILE_PATH}...")

    with open(FINETUNING_FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i + 1 == line_number:
                print(f"\n--- Debugging Record from Line {line_number} ---")
                
                # 1. Check for valid JSON format
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    logging.error(f"Could not parse JSON on line {line_number}: {e}")
                    print(f"Raw Line Content:\n{line}")
                    return

                # 2. Extract input and output
                input_prompt = record.get('input', '[INPUT KEY NOT FOUND]')
                output_str = record.get('output', '[OUTPUT KEY NOT FOUND]')

                # 3. Calculate output length
                output_length = -1
                try:
                    output_data = json.loads(output_str)
                    output_length = len(output_data)
                except (json.JSONDecodeError, TypeError):
                    logging.error("Could not parse the 'output' field string into a list.")

                # 4. Attempt to find frequency with regex
                freq_pattern_1 = r"- The JSON array length MUST equal (\\d+)"
                freq_pattern_2 = r"weekly frequency \({(\d+)} days\)"
                
                match_1 = re.search(freq_pattern_1, input_prompt)
                match_2 = re.search(freq_pattern_2, input_prompt)

                found_frequency = None
                if match_1:
                    found_frequency = int(match_1.group(1))
                elif match_2:
                    found_frequency = int(match_2.group(1))

                # 5. Print all findings
                print("\033[94m1. Calculated Length of 'output' data:\033[0m")
                print(f"   - Length: {output_length}\n")
                
                print("\033[94m2. Regex Search for 'frequency' in 'input' prompt:\033[0m")
                print(f"   - Pattern 1 (MUST equal...): {'Found:' + str(found_frequency) if match_1 else 'Not Found'}")
                print(f"   - Pattern 2 (weekly frequency...): {'Found:' + str(found_frequency) if match_2 else 'Not Found'}\n")

                print("\033[94m3. Full 'input' Prompt Content:\033[0m")
                print("-" * 40)
                print(input_prompt)
                print("-" * 40)
                
                return # Exit after finding and processing the line

    logging.error(f"Could not find line {line_number}. The file has {i + 1} lines in total.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug a specific record in the finetuning data file.")
    parser.add_argument("line_number", type=int, help="The line number of the record to inspect.")
    
    args = parser.parse_args()
    
    debug_specific_record(args.line_number)
