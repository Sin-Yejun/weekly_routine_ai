Frequency_5 = '''## [Task]
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
- Ignore catalog ordering: treat every catalog item as equally likely. Never default to the first seen option. Prefer less-common but level-appropriate options when multiple candidates fit.
- Movement group rule (max 1 per day). Groups:
    Press group = all chest/shoulder presses
    Row group = all horizontal pulling movements
    Pull Up group = all vertical pulling movements
    Squat group = all squat variations
    Lunge group = all lunge/split-squat/step-up variations
    Deadlift group = all deadlift variations
    Push Ups group = all push-up variations
    If one exercise from a group is chosen, do not add another from the same group that day.
- Micro coverage rule: Each day must include ≥2 distinct micro regions for that split. Avoid overconcentrating on a single area.
- Micro novelty rule: Include 1–2 safe, less-common micro targets per day (e.g., LOWER CHEST, POSTERIOR DELTOID, ADDUCTORS, CALVES, FOREARMS) appropriate for {level}.
- Weekly micro distribution (across 5 days):
    • CHEST: ≥2 compounds (MG>=4), include MIDDLE/UPPER press + ≥1 LOWER or fly
    • BACK: ≥1 vertical pull (LATS) + ≥1 horizontal row (UPPER BACK), optional LOWER BACK accessory
    • LEGS: ≥1 squat (MG>=4) + ≥1 hinge/deadlift (MG>=4/5), plus accessories for hamstrings/glutes/quads; optional calves/adductors
    • SHOULDER: ≥1 press, ≥1 lateral raise, ≥1 posterior delt movement
    • ARM: include at least one biceps isolation, one triceps isolation, and one optional forearm/grip
- Indirect diversity rule: If one variation of a major pattern is included, prefer a different plane, angle, or implement next—avoid duplicates.
- Anti-top-bias rule: Build a candidate list for each slot; shuffle BEFORE scoring by (1) MG_num, (2) large→small muscle groups, (3) weekly non-repetition, (4) novelty quota. Select from the top-mid, not always the top-1.

## Procedure (follow EXACTLY)
1) Candidate build: filter Catalog by split mapping, enforce group rule.
2) Primary selection by split:
    - CHEST: 2 presses, 2–3 accessories, 1 fly/novelty
    - BACK: 1 vertical pull, 1 horizontal row, 1–2 accessories, 1 lower-back
    - LEGS: 1 squat, 1 deadlift, 2 accessories, 1–2 isolations
    - SHOULDER: 1 press, 1 lateral raise, 1 posterior delt, 1 accessory
    - ARM: 1 biceps, 1 triceps, 1 forearm, 1 accessory
3) Micro coverage check: each day must cover ≥2 distinct micro regions.
4) Strict ordering by MG_num:
    - Sort MG_num descending.
    - Ensure no isolation (MG<=2) before compound/accessory (MG>=3).
    - Tie-breakers: (a) Chest/Back > Shoulders > Arms/Calves, (b) bilateral before unilateral, (c) free-weight > machine > cable > bodyweight, (d) prefer not-yet-used this week.
5) Integrity loop: re-check uniqueness, group rule, micro diversity; fix & re-sort.

## Final self-check BEFORE emit
- Per day: exercise_name values are unique.
- Per day: ≤1 per movement group.
- Per day: MG_num strictly descending; ties follow tie-breakers.
- Per day: ≥2 distinct micro regions.
- Per week: balanced micro coverage across all 5 splits.
- Exercises appropriate for {level}.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (no spaces/newlines), matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
'''

Frequency_4 = '''## [Task]
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
- Ignore catalog ordering: treat every catalog item as equally likely. Never default to the first seen option. Prefer less-common but level-appropriate options when multiple candidates fit.
- Movement group rule (max 1 per day). Definitions:
    Press group = all chest or shoulder presses
    Row group = all horizontal pulling movements (rows)
    Pull Up group = all vertical pulling movements (pull ups/chin ups/pulldowns)
    Squat group = all squat variations
    Lunge group = all lunge/split-squat/step-up variations
    Deadlift group = all deadlift variations
    Push Ups group = all push-up variations
    Dips group = all dips variations
    If one exercise from a group is chosen, do not add another from the same group that day.
- Micro coverage rule: Each day must include ≥2 distinct micro regions for that split (e.g., Chest day not only MIDDLE CHEST; Legs not only QUADS).
- Micro novelty rule: Include 1–2 safe, less-common micro targets per day (e.g., LOWER CHEST, POSTERIOR DELTOID, ADDUCTORS, CALVES) appropriate for {level}.
- Weekly micro distribution (across all days):
    • Chest: presses for MIDDLE/UPPER + ≥1 LOWER or fly
    • Back: ≥1 vertical pull (LATS) + ≥1 horizontal row (UPPER BACK), optional LOWER BACK accessory
    • Shoulders: include ANTERIOR + LATERAL + POSTERIOR, not only presses
    • Legs: cover QUADS + GLUTES + HAMSTRINGS; optional ADDUCTORS or CALVES isolation
- Indirect diversity rule: If one variation of a major pattern (press/row/squat/lunge/deadlift) is included, prefer a different plane/angle/implement next—do not add another close variant.
- Anti-top-bias rule: Build a candidate list for each slot; shuffle BEFORE scoring by (1) MG_num, (2) large→small muscle groups, (3) weekly non-repetition, (4) novelty quota. Select from the top-mid, not always the top-1.

## Procedure (follow EXACTLY)
1) Candidate build (per day):
    - Filter Catalog to the day's bName (CHEST/BACK/SHOULDER/LEG).
    - Remove items that violate the movement group rule if a group is already taken.
    - Prefer items appropriate for {level} difficulty.
2) Primary selection:
    - Pick compounds first using MG_num (higher means more compound). Target mix by day:
    • CHEST: ≥2 compounds with MG_num>=4; then MG=3 accessories; finish with ≤2 isolations (MG<=2).
    • BACK: include ≥1 vertical pull (MG>=3) and ≥1 horizontal row (MG>=3/4); optional lower-back accessory.
    • SHOULDERS: 1–2 presses (MG=3), ≥1 lateral-raise pattern, ≥1 rear-delt movement.
    • LEGS: include one squat pattern (MG>=4) AND one hinge/deadlift pattern (MG>=4/5); then MG=3 accessories; finish with 1–2 isolations (quads/hamstrings/calves).
    - Enforce movement group rule (max 1 per group) while selecting.
3) Micro coverage check:
    - Ensure the day covers ≥2 distinct micro regions; add/replace items to satisfy this without breaking step 2.
4) Strict ordering by MG_num (sorting step BEFORE emitting):
    - Map each chosen exercise to its MG_num using the Catalog.
    - Sort strictly by MG_num descending (higher→lower).
    - Hard guard: No MG<=2 item can appear before any MG>=3 item. If violated, reorder.
    - Tie-breakers when MG_num is equal:
    a) Larger primary muscle group first (Chest/Back → Shoulders → Arms/Calves)
    b) Bilateral before unilateral (unless unilateral novelty is targeted)
    c) Free-weight before machine, machine before cable, cable before bodyweight—when safety and level allow
    d) Prefer exercises not yet used this week
5) Integrity loop:
    - After sorting, re-check: unique exercise_name per day, movement group rule (≤1 per group), micro ≥2 regions.
    - If any rule is broken, replace the offending item with the best alternative and **repeat steps 3→4→5** until all checks pass.

## Final self-check BEFORE emit
- Per day: ≤1 exercise from the same movement group.
- Per day: order is strictly MG_num descending; ties follow the tie-breakers above.
- Per day: ≥2 distinct micro regions.
- Per week: broad micro distribution across all splits.
- All selections are appropriate for {level} difficulty.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (no spaces/newlines), matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
'''

Frequency_3 = '''## [Task]
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
- Ignore catalog ordering: treat every catalog item as equally likely. Never default to the first seen option. Prefer less-common but level-appropriate options when multiple candidates fit.
- Movement group rule (max 1 per day). Definitions:
    Press group = all chest or shoulder presses
    Row group = all horizontal pulling movements
    Pull Up group = all vertical pulling movements (pull ups/chin ups/pulldowns)
    Squat group = all squat variations
    Lunge group = all lunge/split-squat/step-up variations
    Deadlift group = all deadlift variations
    Push Ups group = all push-up variations
    If one exercise from a group is chosen, do not add another from the same group that day.
- Micro coverage rule: Each day must include ≥2 distinct micro regions. Avoid overconcentrating on one area.
- Micro novelty rule: Include 1–2 safe, less-common micro targets per day (e.g., LOWER CHEST, POSTERIOR DELTOID, ADDUCTORS, CALVES) appropriate for {level}.
- Weekly micro distribution:
    • PUSH: Chest must include MIDDLE/UPPER press + ≥1 isolation/fly; Shoulders must include ANTERIOR + LATERAL; add at least one triceps-focused movement if available.
    • PULL: Back must include ≥1 vertical pull (LATS) + ≥1 horizontal row (UPPER BACK), optional LOWER BACK accessory; include at least one biceps movement if available.
    • LEGS: Must include one squat pattern (MG>=4) AND one hinge/deadlift pattern (MG>=4/5). Also cover QUADS + GLUTES + HAMSTRINGS; optional ADDUCTORS or CALVES isolation.
- Indirect diversity rule: If one variation of a major pattern (press/row/squat/lunge/deadlift) is included, prefer a different plane/angle/implement next—do not add another close variant.
- Anti-top-bias rule: Build a candidate list for each slot; shuffle BEFORE scoring by (1) MG_num, (2) large→small muscle groups, (3) weekly non-repetition, (4) novelty quota. Select from the top-mid, not always the top-1.

## Procedure (follow EXACTLY)
1) Candidate build (per day): filter Catalog by split mapping above, then enforce movement group rule.
2) Primary selection: choose compounds first (MG_num high), then accessories (MG=3), then isolations (MG<=2).
3) Micro coverage check: each day must cover ≥2 micro regions; adjust if needed.
4) Strict ordering by MG_num:
    - Sort exercises MG_num descending.
    - Ensure no isolation (MG<=2) appears before compound/accessory (MG>=3).
    - Tie-breakers: (a) Chest/Back before Shoulders/Arms/Calves, (b) bilateral before unilateral, (c) free-weight > machine > cable > bodyweight, (d) prefer not-yet-used this week.
5) Integrity loop: re-check uniqueness, group rule, micro diversity; fix & re-sort until all rules pass.

## Final self-check BEFORE emit
- Per day: unique exercise_name values.
- Per day: ≤1 per movement group.
- Per day: MG_num strictly descending; ties follow tie-breakers.
- Per day: ≥2 distinct micro regions.
- Per week: balanced micro coverage across PUSH/PULL/LEGS.
- Exercises appropriate for {level}.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (no spaces/newlines), matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
'''

Frequency_2 = '''## [Task]
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
- Day bodypart mapping (use Catalog bName exactly):
    • UPPER day → "CHEST","BACK","SHOULDER","ARMS"
    • LOWER day → "LEG"
- Ignore catalog ordering: treat every catalog item as equally likely. Never default to the first seen option. Prefer less-common but level-appropriate options when multiple candidates fit.
- Movement group rule (max 1 per day). Definitions:
    Press group = all chest/shoulder presses
    Row group = all horizontal pulling movements
    Pull Up group = all vertical pulling movements (pull ups/chin ups/pulldowns)
    Squat group = all squat variations
    Lunge group = all lunge/split-squat/step-up variations
    Deadlift group = all deadlift variations
    Push Ups group = all push-up variations
    If one exercise from a group is chosen, do not add another from the same group that day.
- Micro coverage rule: Each day must include ≥3 distinct micro regions (UPPER day covers chest/back/shoulders/bis/tris; LOWER day covers quads/glutes/hamstrings/calves).
- Micro novelty rule: Include 1–2 safe, less-common micro targets per day (e.g., LOWER CHEST, POSTERIOR DELTOID, ADDUCTORS, CALVES) appropriate for {level}.
- Weekly micro distribution:
    • UPPER: CHEST = presses (MIDDLE/UPPER) + ≥1 fly/lower chest; BACK = ≥1 vertical pull + ≥1 horizontal row + optional erector; SHOULDER = include anterior+lateral+posterior; ARM = at least one biceps and one triceps.
    • LOWER: Must include one squat pattern (MG>=4) AND one hinge/deadlift pattern (MG>=4/5). Cover quads+glutes+hamstrings; optional adductors or calves isolation.
- Indirect diversity rule: If one variation of a major pattern (press/row/squat/lunge/deadlift) is included, prefer a different plane/angle/implement next—do not add another close variant.
- Anti-top-bias rule: Build a candidate list for each slot; shuffle BEFORE scoring by (1) MG_num, (2) large→small muscle groups, (3) weekly non-repetition, (4) novelty quota. Select from the top-mid, not always the top-1.

## Procedure (follow EXACTLY)
1) Candidate build (per day): filter Catalog by split mapping above, then enforce movement group rule.
2) Primary selection:
    - UPPER: start with 2 chest compounds, 2 back compounds (1 vertical+1 horizontal), 1 shoulder press + 1 lateral/rear raise, add 1 biceps + 1 triceps isolation.
    - LOWER: start with 1 squat + 1 deadlift pattern (MG>=4/5), then 2–3 accessories (MG=3), finish with 1–2 isolations (quads/hamstrings/calves/adductors).
3) Micro coverage check: each day must cover ≥3 micro regions; adjust if needed.
4) Strict ordering by MG_num:
    - Sort exercises MG_num descending.
    - Ensure no isolation (MG<=2) appears before compound/accessory (MG>=3).
    - Tie-breakers: (a) Chest/Back before Shoulders/Arms/Calves, (b) bilateral before unilateral, (c) free-weight > machine > cable > bodyweight, (d) prefer not-yet-used this week.
5) Integrity loop: re-check uniqueness, group rule, micro diversity; fix & re-sort until all rules pass.

## Final self-check BEFORE emit
- Per day: exercise_name values are strictly unique.
- Per day: ≤1 per movement group.
- Per day: MG_num strictly descending; ties follow tie-breakers.
- Per day: ≥3 distinct micro regions.
- Per week: balanced micro coverage across UPPER/LOWER.
- Exercises appropriate for {level}.

## Catalog
# Each item = [bName, eName, MG_num, {{"micro":[...]}}]
{catalog_json}

## Output
Return exactly one minified JSON object only (no spaces/newlines), matching:
{{"days":[[[bodypart,exercise_name],...],...]}}
'''