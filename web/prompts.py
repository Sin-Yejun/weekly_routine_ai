common_prompt = '''## [Task]
Return a weekly bodybuilding plan as MINIFIED JSON only.

## [User Info]
- Gender: {gender}
- Weight: {weight}kg
- Training Level: {level}
- Weekly Workout Frequency: {freq}
- Workout Duration: {duration} minutes
- Workout Intensity: {intensity}

## Split
- Name: {split_name}; Days: {split_days}.

## Equipment priority rule:
{level_guide}

## CATEGORY RULE (HARD CONSTRAINT):
- For each day, you MUST output **NO MORE THAN ONE exercise per category**
- If a violation occurs, the output is INVALID. Re-check and regenerate until the rule is satisfied.
- Exception: The '(Uncategorized)' group may allow multiple exercises.

## Content rules
- NO DUPLICATE EXERCISES IN THE WEEK.
- IGNORE CATALOG ORDERING: Treat all catalog items as equally valid; never always default to the first option.

## Importance Weights
- Chest: Upper 3, Middle 3, Lower 2  
- Back: Upper 3, Lower 3, Lats 3  
- Shoulders: Anterior 2, Lateral 2, Posterior 2, Traps 1  
- Arms: Biceps 2, Triceps 2, Forearms 1  
- Core: Abs 1  
- Legs: Glutes 3, Quads 3, Hamstrings 3, Adductors 2, Abductors 2, Calves 1
- Prioritize exercises that target higher-importance muscle groups. Aim to achieve a higher total activation score for muscle groups with a weight of 3, and a moderate score for groups with a weight of 2. Ensure lower-importance groups are not excluded so that the overall routine remains well-balanced.

{split_rules}

## Catalog
# The catalog is grouped by Day, then by Tool Type, then by Category.
# Each item = [bName, eName, MG_num, {{"micro":["part(score)", ...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (NO WHITESPACES / NO NEW LINES), matching:
{{"days":[[[bodypart,ename],...],...]}}
'''

SPLIT_RULES = {
    2: """### 2 DAYS — UPPER / LOWER
- UPPER: MUST Cover Chest (Upper/Middle/Lower), Back (Upper/Lower/Lats), Shoulders (Deltoids, Traps), Arms (all); optional Abs.
- LOWER: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    3: """### 3 DAYS — PUSH / PULL / LEGS
- PUSH: MUST Cover Chest(Upper, Middle, Lower), add Triceps accessory; optional Deltoids.
- PULL: MUST Cover Back(Upper, Lower, Lats), add Biceps accessory; optional Deltoids.
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    4: """### 4 DAYS — CHEST / BACK / SHOULDER / LEGS
- CHEST: MUST Cover Chest(Upper, Middle, Lower); add Triceps accessory.
- BACK: MUST Cover Back(Upper, Lower, Lats); add Biceps accessory.
- SHOULDER:  MUST Cover SHOULDER(Posterior, Anterior, Leteral, Traps).
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    5: """### 5 DAYS — CHEST / BACK / LEGS / SHOULDER / ARMS
- CHEST: MUST Cover Upper, Middle, Lower Chest.
- BACK: MUST Cover Back(Upper, Lower, Lats).
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.
- SHOULDER: MUST Cover SHOULDER(Posterior, Anterior, Leteral, Traps).
- ARMS: MUST Cover Biceps, Triceps, Forearms""",

    "FB_2": """### 2 DAYS — FULL BODY (ROTATING FOCUS)
- Each day is a full-body workout with a different primary focus:
  - DAY 1: Focus **Chest & Shoulders**; include Back, Legs; optional Arms/Abs.
  - DAY 2: Focus **Legs & Back**; include Chest, Shoulders; optional Abs.
- HARD CONSTRAINTS (PER DAY):
  - Must include at least one '(main)' for **CHEST**, **BACK**, **LEGS**.
  - Respect the CATEGORY RULE (max 1 per category per day).
- HARD CONSTRAINTS (WEEK):
  - Do NOT repeat the same exercise in the week.
  - Ensure **Arms OR Abs** appears at least once across the 2 days.
""",

    "FB_3": """### 3 DAYS — FULL BODY (ROTATING FOCUS)
- Each day is a full-body workout, but emphasize different regions:
  - DAY 1: Focus on **Chest & Shoulders**; include Back, Legs, and optional Arms/Abs.
  - DAY 2: Focus on **Back & Legs**; include Chest, Shoulders, and optional Abs.
  - DAY 3: Focus on **Shoulders & Arms**; include Chest, Back, and optional Abs.
- HARD CONSTRAINTS:
  - Each day MUST include at least one '(main)' exercise for Chest, Back, and Legs.
  - Do NOT repeat the same exercise within the week.
  - Ensure Arms and Abs appear at least once across all days.""",

    "FB_4": """### 4 DAYS — FULL BODY (ROTATING FOCUS)
- Each day is a full-body workout; primary focus rotates:
  - DAY 1: **Chest** focus (add Shoulder/Triceps accessories).
  - DAY 2: **Back** focus (add Biceps/Rear Delts accessories).
  - DAY 3: **Legs** focus (add Calves/Abductors/Adductors accessories).
  - DAY 4: **Shoulders** focus (balance Chest/Back accessories).
- HARD CONSTRAINTS (PER DAY):
  - Must include at least one '(main)' for **CHEST**, **BACK**, **LEGS**.
  - Respect the CATEGORY RULE (max 1 per category per day).
- HARD CONSTRAINTS (WEEK):
  - No duplicate exercises within the 4-day plan.
  - Distribute **Arms** and **Abs** so that each appears ≥1 time in the week.
  - Manage fatigue by varying main lift selection and accessory volume.
""",

    "FB_5": """### 5 DAYS — FULL BODY (ROTATING FOCUS)
- Each day is full-body; primary focus rotates through all major groups:
  - DAY 1: **Chest** focus
  - DAY 2: **Back** focus
  - DAY 3: **Legs** focus
  - DAY 4: **Shoulders** focus
  - DAY 5: **Arms** focus (Biceps/Triceps; forearms optional)
- HARD CONSTRAINTS (PER DAY):
  - Must include at least one '(main)' for **CHEST**, **BACK**, **LEGS**.
  - Respect the CATEGORY RULE (max 1 per category per day).
- HARD CONSTRAINTS (WEEK):
  - No duplicate exercises within the 5-day plan.
  - Spread **Abs** across 1–2 days (not every day) to aid recovery.
  - Rotate main lifts (e.g., incline vs flat for Chest; vertical vs horizontal pulls for Back; squat/hinge alternation for Legs).
"""
}


LEVEL_GUIDE = {
    "Beginner": "BEGINNER: BODYWEIGHT focused, MACHINE support, minimal FREE WEIGHT",
    "Novice": "NOVICE: MACHINE focused, FREE WEIGHT support, BODYWEIGHT for warm-up",
    "Intermediate": "INTERMEDIATE: FREE WEIGHT focused, MACHINE support, limited BODYWEIGHT",
    "Advanced": "ADVANCED: FREE WEIGHT dominant, few MACHINE, almost no BODYWEIGHT",
    "Elite": "ELITE: FREE WEIGHT dominant, includes advanced variations, minimal MACHINE"
}

detail_prompt_abstract = '''## [Task]
You are an expert personal trainer. Based on the user's profile and the provided list of exercises, create a detailed weekly workout plan.
Return a MINIFIED JSON object.

## [User Info]
- Gender: {gender}
- Bodyweight: {weight}kg
- Training Level: {level}
- Workout Intensity: {intensity}

## [Exercises for the Week]
Each exercise includes an `eInfoType` that dictates the performance metric for each set.
{exercise_list_with_einfotype_json}

## [Instructions]
1.  For each exercise, create 3-5 sets. Order exercises logically within each day (e.g., compound movements first).
2.  For each set, provide `[reps, weight, time]` based on the `eInfoType`:
    - **eInfoType 1 (Time-based)**: `[0, 0, time_in_seconds]`
    - **eInfoType 2 (Rep-based)**: `[reps, 0, 0]`
    - **eInfoType 5 (Weight + Time)**: `[0, weight_in_kg, time_in_seconds]`
    - **eInfoType 6 (Weight + Reps)**: `[reps, weight_in_kg, 0]`
3.  `weight` should be a number in kg, in multiples of 5 where appropriate. Use 0 for bodyweight exercises. Base weights on the user's profile.

## [Output]
Return a single MINIFIED JSON object. Each day is an array of exercises. Each exercise is an array: `["eName", [set1_details], [set2_details], ...]`. Each set detail is an array: `[reps, weight, time]`.

Example Output:
{{"days":[
      [
        ["Barbell Bench Press",[10,80,0],[8,85,0],[6,90,0],[3,100,0]],
        ["Dumbbell Fly",[12,20,0],[10,25,0],[8,30,0]]
      ],
      [
        ["Treadmill",[0,0,1800]]
      ]
    ]}}
'''

