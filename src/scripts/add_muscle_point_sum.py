'''
This script processes a JSON file to calculate the sum of "musle_point" arrays and verify array lengths.
'''
import json

def process_json_file(input_path, output_path):
    """
    Reads a JSON file, calculates the sum of 'musle_point' arrays,
    adds it as 'musle_point_sum', and verifies array lengths against 'MG_num'.

    Args:
        input_path (str): Path to the input JSON file.
        output_path (str): Path to save the updated JSON file.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("Error: JSON data is not a list of objects.")
            return

        for i, item in enumerate(data):
            if 'musle_point' in item and isinstance(item['musle_point'], list):
                # Calculate the sum of musle_point
                muscle_point_sum = sum(item['musle_point'])
                # Add musle_point_sum to the item
                item['musle_point_sum'] = muscle_point_sum

                # Verify array lengths
                if 'MG_num' in item:
                    mg_num = item['MG_num']
                    muscle_point_len = len(item['musle_point'])
                    if mg_num != muscle_point_len:
                        print(f"Warning: Item {i}: MG_num ({mg_num}) does not match musle_point length ({muscle_point_len}).")
                else:
                    print(f"Warning: Item {i}: 'MG_num' not found.")
            else:
                print(f"Warning: Item {i}: 'musle_point' array not found or is not a list.")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Processing complete. Output saved to '{output_path}'")

    except FileNotFoundError:
        print(f"Error: File not found at '{input_path}'")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{input_path}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    input_file = 'data/02_processed/processed_query_result_200.json'
    output_file = 'data/02_processed/processed_query_result_200_updated.json'
    process_json_file(input_file, output_file)
