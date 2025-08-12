import json
import os
from typing import List, Dict

def compress_sets(sets: List[Dict]) -> str:
    """
    Converts a list of sets into a compressed string format.
    Example: 12x50 / 10x60 / 8x70
    """
    out = []
    for s in sets:
        reps = s.get("sReps")
        weight = s.get("sWeight")
        time = s.get("sTime")

        # Handle weight-based exercises
        if reps is not None and weight is not None and time == 0:
            w_disp = int(weight) if float(weight).is_integer() else weight
            base = f"{reps}" if w_disp == 0 else f"{reps}x{w_disp}"
            out.append(base)
        # Handle bodyweight exercises (reps only)
        elif reps is not None and reps > 0 and weight == 0 and time == 0:
            out.append(f"{reps}")
        # Handle time-based exercises
        elif time is not None and time > 0 and reps == 0 and weight == 0:
            out.append(f"{time}s")

    return " / ".join(out)

def generate_workout_summary_from_json(json_path: str):
    """
    Reads workout data from a JSON file and prints a detailed text summary.

    Args:
        json_path (str): The path to the input JSON file.
    """
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        daily_workouts = json.load(f)

    filtered_workouts = [
        day for day in daily_workouts if 30 <= day.get('duration', 0) <= 120
    ]
    cnt = 1
    for day in filtered_workouts[:10]:
        duration_in_minutes = day.get('duration', 0)
        header = f"Recent Workout #{cnt} (Duration: {duration_in_minutes:.0f} mins)"
        lines = [header]
        for ex in day["exercises"]:
            sets_data = ex.get('data', [])
            sets_summary = compress_sets(sets_data)
            line = (
                f"{ex.get('bName', ''):<3}- {ex.get('eName', '')} ({ex.get('eTextId', '')}) "
                f"{len(sets_data)}sets: {sets_summary}"
            )
            lines.append(line)
        cnt += 1
        print("\n".join(lines))
        print() # Add a blank line for separation


if __name__ == '__main__':
    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir)) # Go up two levels

    # Define the input JSON file path
    user_id = 123180
    input_json_path = os.path.join(project_root, 'data', 'json', f'user_{user_id}_workout_history.json')

    # Generate and print the summary
    generate_workout_summary_from_json(input_json_path)