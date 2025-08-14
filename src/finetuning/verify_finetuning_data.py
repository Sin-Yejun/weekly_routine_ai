
# -*- coding: utf-8 -*-
import json
import logging
import re
from pathlib import Path

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
FINETUNING_FILE_PATH = DATA_DIR / 'finetuning_data.jsonl'

def verify_finetuning_data(limit: int = 5):
    """
    Verifies the integrity and structure of the finetuning_data.jsonl file.

    Checks:
    1. If each line is a valid JSON.
    2. If each JSON object has 'input' and 'output' keys.
    3. If the 'output' string is valid JSON.
    4. If the length of the 'output' array matches the 'frequency' in the 'input' prompt.
    """
    if not FINETUNING_FILE_PATH.exists():
        logging.error(f"Verification failed: File not found at {FINETUNING_FILE_PATH}")
        return

    total_lines = 0
    valid_records = 0
    error_records = 0
    mismatch_records = 0
    
    logging.info(f"Starting verification for {FINETUNING_FILE_PATH}...")

    with open(FINETUNING_FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            total_lines += 1
            line_num = i + 1

            # 1. Check for valid JSON format
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logging.error(f"Line {line_num}: Invalid JSON format.")
                error_records += 1
                continue

            # 2. Check for required keys
            if 'input' not in record or 'output' not in record:
                logging.error(f"Line {line_num}: Missing 'input' or 'output' key.")
                error_records += 1
                continue

            # 3. Check if 'output' is a valid JSON string
            try:
                output_data = json.loads(record['output'])
            except (json.JSONDecodeError, TypeError):
                logging.error(f"Line {line_num}: The 'output' field is not a valid JSON string.")
                error_records += 1
                continue
            
            # 4. Cross-verify frequency from input with length of output
            try:
                # Extract frequency from the input prompt
                match = re.search(r"- The JSON array length \*\*MUST equal (\d+)\*\*", record['input'])
                if not match:
                    match = re.search(r"weekly frequency \((\d+) days\)", record['input'])
                
                if match:
                    frequency_in_prompt = int(match.group(1))
                    output_length = len(output_data)
                    
                    if frequency_in_prompt != output_length:
                        logging.warning(
                            f"Line {line_num}: Mismatch! Frequency in prompt is {frequency_in_prompt}, "
                            f"but length of output array is {output_length}."
                        )
                        mismatch_records += 1
                else:
                    logging.warning(f"Line {line_num}: Could not find frequency in the input prompt to verify.")

            except Exception as e:
                logging.error(f"Line {line_num}: An unexpected error occurred during verification: {e}")
                error_records += 1
                continue

            # If all checks pass
            valid_records += 1
            
            # Print some samples
            if valid_records <= limit:
                logging.info(f"-- Sample Record #{valid_records} (Line {line_num}) --")
                print(f"Input Prompt (first 100 chars): {record['input'][:100]}...")
                print(f"Output Data (first 100 chars): {record['output'][:100]}...")
                print("-" * 20)

    # --- Final Summary ---
    logging.info("--- Verification Complete ---")
    print(f"Total lines checked: {total_lines}")
    print(f"\033[92mValid records: {valid_records}\033[0m")
    print(f"\033[91mRecords with errors (format/keys): {error_records}\033[0m")
    print(f"\033[93mRecords with frequency/output length mismatch: {mismatch_records}\033[0m")

if __name__ == "__main__":
    verify_finetuning_data()
