
import pandas as pd

file_path = "/Users/yejunsin/Documents/weekly_routine_ai/data/parquet/user.parquet"

try:
    df = pd.read_parquet(file_path)
    filtered_df = df[df['frequency'] > df['workout_days']]
    count = len(filtered_df)
    print(f"Number of entries where frequency > workout_days: {count}")
except FileNotFoundError:
    print(f"Error: The file {file_path} was not found.")
except KeyError as e:
    print(f"Error: Missing expected column - {e}. Please ensure 'frequency' and 'workout_days' columns exist.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
