from pathlib import Path
import pandas as pd

PARQUET_PATH = Path("data/02_processed/parquet/weekly_streak_dataset.parquet")
# "user_id","week_start","streak_no","freq","sessions_cnt","week_level","gender","weight","session_ids","weekly_exercises","avg_duration_min","duration_bucket"
def get_user_profile_text() -> str:
    """
    Generates a text summary of the user's profile from the user.parquet file.
    """
    df = pd.read_parquet(PARQUET_PATH)
    # Assuming a single user record in the parquet file
    row = df.iloc[0]

    # --- Preprocessing & Mapping ---
    frequency = int(row.freq)
    
    # --- Final Text ---
    return (
        f"- Gender: {row.gender}\n"
        f"- Weight: {row.weight}kg\n"
        f"- Training Level: {row.week_level}\n"
        f"- Weekly Workout Frequency: {frequency}\n"
        f"- Workout Duration: {row.duration_bucket} minutes\n" # 30 / 45 / 60 / 75 / 90+
        f"- Workout Intensity: Normal" # Easy / Normal / Hard
    )

def get_user_frequency(user_id: int = None) -> int:
    """
    Returns the user's weekly workout frequency.
    If user_id is provided, returns frequency for that user.
    If user_id is None, returns frequency for the first user in the parquet file.
    """
    df = pd.read_parquet(PARQUET_PATH)
    if user_id is not None:
        user_df = df[df["user_id"] == user_id]
        if user_df.empty:
            raise ValueError(f"User with ID {user_id} not found in user.parquet")
        frequency = user_df["freq"].iloc[0]
    else:
        # Assuming a single user record or taking the first one if no user_id is specified
        frequency = df["freq"].iloc[0]
    return int(frequency)


# Example call
if __name__ == "__main__":
    print(get_user_profile_text())
    #print(f"Weekly workout frequency: {get_user_frequency(197)}")
    #print(get_user_frequency(135687))  # Example user_id