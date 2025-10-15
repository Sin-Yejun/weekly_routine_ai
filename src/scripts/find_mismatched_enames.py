'''
This script finds and prints the 'eName' for given indices in a JSON file.
'''
import json

def find_mismatched_enames(json_path, indices):
    """
    Finds and prints the 'eName' for given indices in a JSON file.

    Args:
        json_path (str): Path to the JSON file.
        indices (list): A list of integers representing the indices to check.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("Error: JSON data is not a list of objects.")
            return

        print("eName of items with mismatched lengths:")
        for index in indices:
            if 0 <= index < len(data):
                item = data[index]
                eName = item.get('eName', 'eName not found')
                mg_num = item.get('MG_num', 'N/A')
                musle_point_len = len(item.get('musle_point', []))
                print(f"  - Item {index}: eName='{eName}', MG_num={mg_num}, musle_point_len={musle_point_len}")
            else:
                print(f"Warning: Index {index} is out of bounds.")

    except FileNotFoundError:
        print(f"Error: File not found at '{json_path}'")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{json_path}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    input_file = 'data/02_processed/processed_query_result_200.json'
    mismatched_indices = [46, 48, 159]
    find_mismatched_enames(input_file, mismatched_indices)
