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
- For each day, you MUST output **NO MORE THAN ONE exercise per category (Benchpress, LUNGE, Push Ups, Deadlift...)**
- If a violation occurs, the output is INVALID. Re-check and regenerate until the rule is satisfied.
- Exception: The '(Uncategorized)' group may allow multiple exercises.

## Content rules
- NO DUPLICATE EXERCISES IN THE WEEK.
- IGNORE CATALOG ORDERING: Treat all catalog items as equally valid; never always default to the first option.

## Importance Weights
- Chest: Upper 3, Middle 3, Lower 2  
- Back: Upper 3, Lower 3, Lats 3  
- Shoulders: Anterior 2, Lateral 2, Posterior 2, Traps 1  
- Abs: Upper Abs 2, Lower Abs 2, Obliques 1, Core 1
- Arm: Biceps 2, Triceps 2, Forearms 1  
- Legs: Glutes 3, Quads 3, Hamstrings 3, Adductors 2, Abductors 2, Calves 1
- Prioritize exercises that target higher-importance muscle groups. Aim to achieve a higher total activation score for muscle groups with a weight of 3, and a moderate score for groups with a weight of 2. Ensure lower-importance groups are not excluded so that the overall routine remains well-balanced.

{split_rules}

## Catalog
# The catalog is grouped by Day, then by Tool Type, then by Category.
# Each item = [bName, eName, MG_num, {{"micro":["part(score)", ...]}}]
{catalog_json}

## Output
Return exactly one MINIFIED JSON object only (NO WHITESPACES / NO NEW LINES), matching:
{{"days":[[[bodypart,ename],...],...]}}
'''

SPLIT_RULES = {
    2: """### 2 DAYS — UPPER / LOWER
- UPPER: MUST Cover Chest (Upper, Middle, Lower), Back (Upper, Lats, Lower), Shoulders (Deltoids, Traps), Arms (all); optional Abs.
- LOWER: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    3: """### 3 DAYS — PUSH / PULL / LEGS
- PUSH: MUST Cover Chest(Upper, Middle, Lower), add Triceps accessory; optional Deltoids.
- PULL: MUST Cover Back(Upper, Lats, Lower), add Biceps accessory; optional Deltoids.
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    4: """### 4 DAYS — CHEST / BACK / SHOULDER / LEGS
- CHEST: MUST Cover Chest(Upper, Middle, Lower); add Triceps accessory.
- BACK: MUST Cover Back(Upper, Lats, Lower); add Biceps accessory.
- SHOULDER:  MUST Cover SHOULDER(Posterior, Anterior, Leteral, Traps).
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    5: """### 5 DAYS — CHEST / BACK / LEGS / SHOULDER / ARM+ABS
- CHEST: MUST Cover Upper, Middle, Lower Chest.
- BACK: MUST Cover Back(Upper, Lats, Lower).
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.
- SHOULDER: MUST Cover SHOULDER(Posterior, Anterior, Leteral, Traps).
- ARM+ABS: MUST Cover Biceps, Triceps, Forearms, Upper Abs, Lower Abs, Obliques, and Core. COMPOSE ARM HALF, ABS HALF.""",

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
You are a certified personal trainer. Based on the user's profile and the given exercises, generate a detailed weekly workout plan that reflects realistic set progression.
Return ONLY a MINIFIED JSON object (NO WHITESPACES / NO NEWLINES).

## [User Profile]
- Gender: {gender}
- Bodyweight: {weight}kg
- Training Level: {level}
- Workout Intensity: {intensity}

## [Weekly Exercise List]
Each exercise includes its `eInfoType` (performance metric) and `tool`.
{exercise_list_with_einfotype_json}

## [Loads]
- Training Max (TM): BP={TM_BP}, SQ={TM_SQ}, DL={TM_DL}, OHP={TM_OHP} (kg).
  
## [Programming Rules]

### Set Count by Level
{level_sets}

### Reps Range (HARD CONSTRAINT)
- All sets must have reps between **8 and 15** inclusive.
- Typical pattern by level:
{level_pattern}

### Warm-up & Working Set Logic
- The first 2 sets are warm-ups designed to prepare the body, not to cause fatigue. The remaining sets are working sets for muscle growth.
- **Set 1 (Activation & Mobility):** Use the **empty bar (20kg) for Barbell**; otherwise ~20–30% of TM. Goal: mobility, pattern check, neural priming.
- **Set 2 (Ramp-up):** Increase weight to **40–60% of TM**. Goal: load signaling, blood flow, neural readiness.
- **Sets 3+ (Working Sets):** Use **level-specific ranges** (see below), typically **65–85% of TM**. Weight may rise as reps slightly drop. Keep a clear logical progression from light→medium→heavy.

### Load Calculation (% of Training Max)
Use the user's estimated TM (based on bodyweight × level coefficient):
- **Warm-ups:** Set1 = **empty bar 20kg (Barbell)** or ~20–30% TM; Set2 = **40–60% TM**
- **Working sets (by level):**
{level_working_sets}
- Rounding Rule: **all weights are integers**, rounded to nearest **5 kg** (or **2 kg** if Dumbbell).

### Example Set Structures (AUTO-CALCULATED; COPY THIS SHAPE)
# Barbell/Machine/Cable (5kg rounding; Set1 uses empty bar 20kg for Barbell)
- Bench Press: {BP_example}
- Squat: {SQ_example}
- Deadlift: {DL_example}
- Overhead Press: {OHP_example}

# Dumbbell (per hand; 2kg rounding; upper BP-based TM, lower SQ-based TM)
- Upper-body ref: {BP_example_db}
- Lower-body ref: {SQ_example_db}

### Output Format
Return **one MINIFIED JSON object** only (no spaces, no newlines):
{{"days":[[["eName",[reps,weight,time],...],...],[...]]}}
'''

LEVEL_SETS = {
    "Beginner": "- Beginner: 4 sets",
    "Novice": "- Novice: 5 sets",
    "Intermediate": "- Intermediate: 6 sets",
    "Advanced": "- Advanced: 6 sets",
    "Elite": "- Elite: 6 sets"
}

LEVEL_PATTERN = {
    "Beginner": "- Beginner: [15,12,10,8]",
    "Novice": "- Novice: [15,12,10,9,8]",
    "Intermediate": "- Intermediate: [15,12,10,10,8,8]",
    "Advanced": "- Advanced: [15,12,10,10,8,8]",
    "Elite": "- Elite: [15,12,10,10,8,8]"
}

LEVEL_WORKING_SETS = {
    "Beginner": "- Beginner: 65–70% of TM",
    "Novice": "- Novice: 70% of TM",
    "Intermediate": "- Intermediate: 70–75% of TM",
    "Advanced": "- Advanced: 75–80% of TM",
    "Elite": "- Elite: 80–85% of TM"
}

DUMBBELL_GUIDE = {
    "Beginner": "- Beginner: total 30–40% of TM",
    "Novice": "- Novice: total 40–50% of TM",
    "Intermediate": "- Intermediate: total 50–60% of TM",
    "Advanced": "- Advanced: total 60–70% of TM",
    "Elite": "- Elite: total 70–80% of TM"
}