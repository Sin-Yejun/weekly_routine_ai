# -*- coding: utf-8 -*-
import json
from pathlib import Path
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = BASE_DIR / 'data' / 'finetuning_data.jsonl'

def view_first_record_output():
    """
    Reads the first line of the finetuning data file,
    parses it, and prints the 'output' field in a readable format.
    """
    logging.info(f"Attempting to read the first record from: {OUTPUT_PATH}")

    if not OUTPUT_PATH.exists():
        logging.error(f"Error: Output file not found at {OUTPUT_PATH}")
        logging.error("Please run 'create_finetuning_data.py' first to generate the data.")
        return

    with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
        try:
            first_line = f.readline()
            if not first_line:
                logging.warning("File is empty. No records to display.")
                return

            # The line itself is a JSON string
            record = json.loads(first_line)
            
            # The 'output' field is a JSON string within the record
            output_str = record.get("output")
            
            if output_str is None:
                logging.error("The first record does not contain an 'output' field.")
                return
                
            # Parse the nested JSON string to get the actual object
            output_data = json.loads(output_str)

            print("\n--- Finetuning Record Output (First Entry) ---")
            print(json.dumps(output_data, ensure_ascii=False))
            print("\n-------------------------------------------------")
            
            logging.info("Successfully displayed the output of the first record.")

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from the file: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    view_first_record_output()
