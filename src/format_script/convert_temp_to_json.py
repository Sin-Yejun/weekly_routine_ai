
import json
import os

# Get the absolute path of the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the absolute path to the project root (assuming the script is in src/format_script)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

# Define the input and output file paths relative to the project root
input_file_rel_path = 'data/02_processed/temp.txt'
output_file_rel_path = 'data/02_processed/beginner_exercises.json'

input_file_abs_path = os.path.join(project_root, input_file_rel_path)
output_file_abs_path = os.path.join(project_root, output_file_rel_path)

# Read the exercise names from the input file
try:
    with open(input_file_abs_path, 'r', encoding='utf-8') as f:
        exercises = [line.strip() for line in f.readlines() if line.strip()]

    # Create the desired dictionary structure
    data = {
        "MBeginner": exercises
    }

    # Write the dictionary to the output JSON file
    with open(output_file_abs_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Successfully created {output_file_abs_path}")

except FileNotFoundError:
    print(f"Error: Input file not found at {input_file_abs_path}")
except Exception as e:
    print(f"An error occurred: {e}")
