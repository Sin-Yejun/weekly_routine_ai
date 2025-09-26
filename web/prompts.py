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

## Content rules
- NO DUPLICATE EXERCISES IN THE WEEK.
- IGNORE CATALOG ORDERING: Treat all catalog items as equally valid; never always default to the first option.
- Movement group rule (max 1 per day). The groups are:
    • Press = chest/shoulder pressing (bench/shoulder press)
    • Row = horizontal pulling (barbell/dumbbell/cable/machine rows)
    • Pull Up = vertical pulling (pull-up/chin-up/lat pulldown)
    • Squat = squat patterns (back/front/sumo/goblet/etc.)
    • Lunge = lunges/split-squats/step-ups
    • Raise = raise patterns (lateral/front/rear raises)
    • Deadlift = hinge patterns (conventional/romanian/stiff-leg/sumo)
    • Push Up = push-up variations (incline/decline/knee/standard)
- If one exercise from a group is chosen, no other from that group can be added that day.

## Equipment priority rule:
{level_guide}

{split_rules}

## Procedure (follow EXACTLY)
1) For each day, create a balanced routine that includes exercises for all the specified muscle groups listed next to the day's name.
2) Candidate build per day: filter Catalog by the day's split mapping; enforce movement group rule and equipment priority for {level}.
3) Primary selection: choose compounds first (MG_num high), then accessories (MG=3), then isolations (MG<=2), while meeting the split-specific rules above.
4) Micro coverage check: ensure ≥2 distinct micro regions per day; adjust if needed without breaking step 2.
5) Strict ordering: sort MG_num descending; no isolation (MG<=2) before any MG>=3. Tie-breakers when MG is equal: (a) Chest/Back before Shoulders/Arms/Calves, (b) bilateral before unilateral (unless unilateral novelty is intended), (c) free-weight > machine > cable > bodyweight (when safe for {level}), (d) prefer exercises not yet used this week.
6) Integrity loop: re-check uniqueness, movement group ≤1/day, equipment priority mix, micro coverage; replace offending items and re-sort until all checks pass.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (NO SPACES / NEW LINES), matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
'''

SPLIT_RULES = {
    2: """### 2 DAYS — UPPER / LOWER
- UPPER: Cover Chest (Upper/Middle + ≥1 fly/isolation), Back (≥1 Pull Up + ≥1 Row), Shoulders (Anterior + Lateral), Arms (≥1 Biceps + ≥1 Triceps). Abs optional.
- LOWER: Include ≥1 Squat AND ≥1 Deadlift (hinge). Cover Quads + Glutes + Hamstrings; optionally Calves or Adductors isolation.""",

    3: """### 3 DAYS — PUSH / PULL / LEGS
- PUSH: Chest must include an Upper or Middle Press + ≥1 Fly/Isolation; Shoulders include Anterior + Lateral; add ≥1 Triceps. Avoid 2+ presses in the same day.
- PULL: Include ≥1 Pull Up (vertical, Lats) AND ≥1 Row (horizontal, Upper Back). Add optional Posterior Deltoid or Lower Back; include ≥1 Biceps.
- LEGS: Include ≥1 Squat AND ≥1 Deadlift (hinge). Cover Quads + Glutes + Hamstrings; optionally Calves or Adductors.""",

    4: """### 4 DAYS — CHEST / BACK / SHOULDER / LEGS
- CHEST: ≥1 Press (Bench/Incline) + ≥1 Fly/Isolation. Cover Upper + Middle; optionally Lower chest. Add 1 Triceps accessory if appropriate.
- BACK: ≥1 Pull Up + ≥1 Row. Cover Upper Back + Lats; optionally Lower Back or Biceps accessory.
- SHOULDER: Include Anterior + Lateral + ≥1 Posterior Deltoid movement; optional Traps accessory.
- LEGS: ≥1 Squat + ≥1 Deadlift; cover Quads + Glutes + Hamstrings; optionally Calves or Adductors.""",

    5: """### 5 DAYS — CHEST / BACK / LEGS / SHOULDER / ARMS
- CHEST: ≥1 Press + ≥1 Fly; cover Upper + Middle; optionally Lower chest.
- BACK: ≥1 Pull Up + ≥1 Row; cover Upper Back + Lats; optionally Posterior Deltoid or Traps.
- LEGS: ≥1 Squat + ≥1 Deadlift; cover Quads + Glutes + Hamstrings; optionally Calves or Adductors.
- SHOULDER: Anterior + Lateral + ≥1 Posterior Deltoid; optional Traps accessory.
- ARMS: ≥1 Biceps + ≥1 Triceps; optional Forearms; ensure curl/extension variants are not redundant."""
}


LEVEL_GUIDE = {
    "Beginner": """BEGINNER: MAJORITY BODYWEIGHT; ADD 1–2 MACHINE SUPPORTS IF NEEDED; AVOID FREE WEIGHT EXCEPT VERY SIMPLE OPTIONS.""",
    "Novice": """NOVICE: MAJORITY MACHINE; ADD 1–2 FREE WEIGHT AS ACCESSORY; BODYWEIGHT FOR WARM-UP/EASY VARIATIONS.""",
    "Intermediate": """INTERMEDIATE: MAJORITY FREE WEIGHT; ADD 1–2 MACHINE ACCESSORIES; BODYWEIGHT ONLY IF PURPOSEFUL.""",
    "Advanced": """ADVANCED: MAJORITY FREE WEIGHT; MACHINE ONLY FOR ACCESSORY/ISOLATION. INCLUDE COMPLEX COMPOUNDS.""",
    "Elite": """ELITE: FREE WEIGHT DOMINANCE; INCLUDE HIGH-SKILL LIFTS AND ADVANCED VARIATIONS; MINIMAL MACHINE OR BODYWEIGHT EXCEPT FOR TARGETED ISOLATION."""
}
