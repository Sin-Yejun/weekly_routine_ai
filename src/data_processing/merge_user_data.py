import pandas as pd
import json

def merge_data():
    # Load the CSV file into a pandas DataFrame
    csv_file_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/analysis_results/user_frequency_sliding.csv'
    df = pd.read_csv(csv_file_path)

    # Create a dictionary for quick lookup
    lookup = df.set_index('user_id')[['frequency', 'assigned_random']].to_dict('index')

    # Process the ndjson file
    ndjson_file_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/json/user.ndjson'
    output_lines = []
    with open(ndjson_file_path, 'r') as f:
        for line in f:
            user_data = json.loads(line)
            user_id = user_data.get('id')
            if user_id in lookup:
                user_data['frequency'] = lookup[user_id]['frequency']
                user_data['assigned_random'] = lookup[user_id]['assigned_random']
            output_lines.append(json.dumps(user_data))

    # Write the updated data back to the ndjson file
    with open(ndjson_file_path, 'w') as f:
        for line in output_lines:
            f.write(line + '\n')

if __name__ == '__main__':
    merge_data()
