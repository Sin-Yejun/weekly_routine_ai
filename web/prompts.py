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
- For each day, you MUST output **NO MORE THAN ONE exercise per category(Dumbbell Benchpress, Push Ups, Barbell Row, Dumbbell Row, Calf Raise, Lunge, ...)**
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
{{"days":[[[bodypart,exercise_name],...],...]}}
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
- ARMS: MUST Cover Biceps, Triceps, Forearms"""
}


LEVEL_GUIDE = {
    "Beginner": "BEGINNER: BODYWEIGHT focused, MACHINE support, minimal FREE WEIGHT",
    "Novice": "NOVICE: MACHINE focused, FREE WEIGHT support, BODYWEIGHT for warm-up",
    "Intermediate": "INTERMEDIATE: FREE WEIGHT focused, MACHINE support, limited BODYWEIGHT",
    "Advanced": "ADVANCED: FREE WEIGHT dominant, few MACHINE, almost no BODYWEIGHT",
    "Elite": "ELITE: FREE WEIGHT dominant, includes advanced variations, minimal MACHINE"
}
