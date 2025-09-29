common_prompt = '''## [Task]
Return a weekly bodybuilding plan as strict JSON only.

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

## Importance Weights
- Chest: Upper 3, Middle 3, Lower 2  
- Back: Upper 3, Lower 3, Lats 3  
- Shoulders: Anterior 2, Lateral 2, Posterior 2, Traps 1  
- Arms: Biceps 2, Triceps 2, Forearms 1  
- Core: Abs 1  
- Legs: Glutes 3, Quads 3, Hamstrings 3, Adductors 2, Abductors 2, Calves 1
- Prioritize exercises that target higher-importance muscle groups. Aim to achieve a higher total activation score for muscle groups with a weight of 3, and a moderate score for groups with a weight of 2. Ensure lower-importance groups are not excluded so that the overall routine remains well-balanced.

- MOVEMENT GROUP RULE: STRICTLY MAX 2 exercise from each group per day.  
    (Bench Press, Row, Squat, Lunge, Deadlift, Push Ups)  

## Content rules
- NO DUPLICATE EXERCISES IN THE WEEK.
- Base Movement Uniqueness: Do not include exercises that are variations of the same core movement. A core movement is identified by the main action in the exercise name, after removing any tool-related prefixes (e.g., 'Barbell', 'Dumbbell'). For example, if one variation of a core movement is selected, do not select another variation of that same core movement even if it uses different equipment. Prefixes to ignore when identifying the core movement include: Barbell, Dumbbell, Kettlebell, EZ Bar.
- IGNORE CATALOG ORDERING: Treat all catalog items as equally valid; never always default to the first option.

## Equipment priority rule:
{level_guide}

{split_rules}

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":["part(score)", ...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (NO SPACES / NEW LINES), matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
'''

SPLIT_RULES = {
    2: """### 2 DAYS — UPPER / LOWER
- UPPER: MUST Cover Chest (Upper/Middle/Lower), Back (Upper/Lower/Lats), Shoulders (Deltoids, Traps), Arms (all); optional Abs.
- LOWER: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    3: """### 3 DAYS — PUSH / PULL / LEGS
- PUSH: MUST Cover Chest(Upper, Middle, Lower), add Triceps accessory; optional Deltiods.
- PULL: MUST Cover Back(Upper, Lower, Lats), add Biceps accessory; optional Deltiods.
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    4: """### 4 DAYS — CHEST / BACK / SHOULDER / LEGS
- CHEST: MUST Cover Chest(Upper, Middle, Lower); add Triceps accessory.
- BACK: MUST Cover Back(Upper, Lower, Lats); add Biceps accessory.
- SHOULDER:  MUST Cover SHOULDER(Anterior, Leteral, Posterior, Traps).
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.""",

    5: """### 5 DAYS — CHEST / BACK / LEGS / SHOULDER / ARMS
- CHEST: MUST Cover Upper, Middle, Lower Chest.
- BACK: MUST Cover Back(Upper, Lower, Lats).
- LEGS: MUST Cover Quads, Glutes, Hamstrings, Adductors, Abductors, add Calves accessory.
- SHOULDER: MUST Cover SHOULDER(Anterior, Leteral, Posterior, Traps).
- ARMS: MUST Cover Biceps, Triceps, Forearms"""
}


LEVEL_GUIDE = {
    "Beginner": "BEGINNER: BODYWEIGHT focused, MACHINE support, minimal FREE WEIGHT",
    "Novice": "NOVICE: MACHINE focused, FREE WEIGHT support, BODYWEIGHT for warm-up",
    "Intermediate": "INTERMEDIATE: FREE WEIGHT focused, MACHINE support, limited BODYWEIGHT",
    "Advanced": "ADVANCED: FREE WEIGHT dominant, few MACHINE, almost no BODYWEIGHT",
    "Elite": "ELITE: FREE WEIGHT dominant, includes advanced variations, minimal MACHINE"
}
