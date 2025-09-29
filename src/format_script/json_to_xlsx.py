
import json
import pandas as pd
import os

# Define file paths
json_file_path = os.path.join('data', '02_processed', 'processed_query_result_filtered.json')
xlsx_file_path = os.path.join('data', '02_processed', 'processed_query_result.xlsx')

# Check if required libraries are installed
try:
    import openpyxl
except ImportError:
    print("The 'openpyxl' library is not installed. Please install it using 'pip install openpyxl'")
    exit()

# Read the JSON file
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: The file '{json_file_path}' was not found.")
    exit()
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from the file '{json_file_path}'.")
    exit()

# Extract the required columns
filtered_data = []
for item in data:
    filtered_data.append({
        'eName': item.get('eName'),
        'tool': item.get('tool_en'),
        'MG': item.get('MG'),
        'musle_point': item.get('musle_point'),

    })

# Create a DataFrame
df = pd.DataFrame(filtered_data)

# Write the DataFrame to an XLSX file
try:
    df.to_excel(xlsx_file_path, index=False)
    print(f"Successfully converted {json_file_path} to {xlsx_file_path}")
except Exception as e:
    print(f"An error occurred while writing to the XLSX file: {e}")

