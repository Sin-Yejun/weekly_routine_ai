
import json
from pathlib import Path
import sys

# Add the src directory to the Python path
src_path = Path(__file__).resolve().parent.parent
sys.path.append(str(src_path))

from learning_script.user_info import get_user_frequency

# Get the project root for file access
project_root = src_path.parent

def generate_weekly_workout_from_history(user_id: int):
    """
    Generates a weekly workout plan based on the user's most recent
    workout history, filtered by their weekly workout frequency.

    Args:
        user_id: The ID of the user.
    """
    try:
        # 1. Get the user's weekly workout frequency
        frequency = get_user_frequency(user_id)
    except Exception as e:
        print(f"Error getting user frequency: {e}")
        # Default to a frequency of 3 if the user profile can't be read
        frequency = 3

    # 2. Define the path to the recent workouts data file
    input_path = project_root / f"data/user_{user_id}_recent_workouts.json"

    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        print("Please run the pre-processing script first.")
        return

    # 3. Read and parse the recent workouts JSON
    with open(input_path, "r", encoding="utf-8") as f:
        recent_workouts = json.load(f)

    # 4. The data is pre-sorted by date, so we can just take the top 'n' records
    # where n is the frequency.
    weekly_workout_plan = recent_workouts[:frequency]

    # 5. Remove specified keys from each workout session
    keys_to_remove = ["user_id", "id", "date"]
    for session in weekly_workout_plan:
        for key in keys_to_remove:
            session.pop(key, None) # Use .pop(key, None) to avoid KeyError if key is missing

    # 6. Print the resulting JSON to standard output
    print(json.dumps(weekly_workout_plan, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    # Using a hardcoded user_id for this example
    USER_ID = 29827
    generate_weekly_workout_from_history(USER_ID)
