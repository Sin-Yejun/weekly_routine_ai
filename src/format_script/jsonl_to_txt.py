import json

def jsonl_to_txt(jsonl_file_path, txt_file_path, line_number=0):
    """
    Reads a specific line from a JSONL file, parses it as JSON, and saves it as a formatted string to a text file.

    Args:
        jsonl_file_path (str): The path to the input JSONL file.
        txt_file_path (str): The path to the output text file.
        line_number (int): The line number to convert (0-indexed).
    """
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as jsonl_file:
            for i, line in enumerate(jsonl_file):
                if i == line_number:
                    data = json.loads(line)
                    with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
                        if 'input' in data and 'output' in data:
                            txt_file.write("input\n")
                            txt_file.write(data['input'] + '\n')
                            txt_file.write("output\n")
                            txt_file.write(data['output'] + '\n')
                        else:
                            txt_file.write(json.dumps(data, indent=4, ensure_ascii=False))
                    print(f"Successfully converted line {line_number} from '{jsonl_file_path}' to '{txt_file_path}'")
                    return
        print(f"Error: Line {line_number} not found in '{jsonl_file_path}'")
    except FileNotFoundError:
        print(f"Error: Input file not found at '{jsonl_file_path}'")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from line {line_number} of '{jsonl_file_path}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # NOTE: You can change these file paths and the line number as needed.
    INPUT_JSONL_FILE = 'data/finetuning_data_v4.jsonl'
    OUTPUT_TXT_FILE = 'data/example.txt'
    LINE_TO_CONVERT = 0  # The first line

    jsonl_to_txt(INPUT_JSONL_FILE, OUTPUT_TXT_FILE, LINE_TO_CONVERT)
