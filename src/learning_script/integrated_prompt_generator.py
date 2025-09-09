import json
import os
from history_summary import get_prev_weeks_texts
from user_info import get_user_profile_text, get_user_frequency
# ## [Recent Workout History]
# {history_summary_txt}
def create_prompt():
    """
    Build an English prompt for weekly/daily routine generation.
    - No catalog size limit (list all available exercises).
    - Remove split recommendations and weight-notation sections.
    - Example Output follows the user's sample (no 'type' field).
    """
    # Recent workout history (last 10)
    txt_list = get_prev_weeks_texts(limit_rows=1, user_id=3236, max_prev=4)
    history_summary_txt = "\n\n".join(txt_list)

    # User info / frequency
    user_info_txt = get_user_profile_text() or ""
    frequency = get_user_frequency() or 3

    # Load available exercise catalog
    exercise_list = []
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        json_path = 'data/02_processed/processed_query_result.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            exercise_list = json.load(f)
    except:
        pass

    #exercise_list_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in exercise_list)
    exercise_list_text = ""

    prompt = f"""## [Task]
Generate a weekly workout routine based on user data.

## [User Info]
{user_info_txt}

## [Instructions]

## [Available Exercise Catalog]
{exercise_list_text}
"""
    return prompt

if __name__ == "__main__":
    prompt = create_prompt()
    print(prompt)