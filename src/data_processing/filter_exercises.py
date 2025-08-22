import json

def filter_and_save_exercises():
    """
    Filters the AI exercise list based on the post-processed list and saves the result to a new file.
    """
    try:
        # Load the AI exercise list
        with open('/Users/yejunsin/Documents/weekly_routine_ai/data/03_core_assets/ai_exercise_list.json', 'r', encoding='utf-8') as f:
            ai_list = json.load(f)

        # Load the post-processed exercise list
        with open('/Users/yejunsin/Documents/weekly_routine_ai/data/03_core_assets/multilingual-pack/post_process_en.json', 'r', encoding='utf-8') as f:
            post_process_list = json.load(f)

        # Create a set of the e_text_ids from the post-processed list for efficient lookup
        post_process_ids = {exercise['e_text_id'] for exercise in post_process_list}

        print(f"Length of ai_list: {len(ai_list)}")
        print(f"Length of post_process_list: {len(post_process_list)}")
        print(f"Length of post_process_ids set: {len(post_process_ids)}")

        # Filter the ai_list
        filtered_list = [exercise for exercise in ai_list if exercise['code'] in post_process_ids]

        # Define the output file path
        output_file_path = '/Users/yejunsin/Documents/weekly_routine_ai/data/03_core_assets/filtered_ai_exercise_list.json'

        # Save the filtered list to a new JSON file
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_list, f, ensure_ascii=False, indent=4)

        print(f"Successfully filtered {len(filtered_list)} exercises and saved to {output_file_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}. Please check if the file paths are correct.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    filter_and_save_exercises()