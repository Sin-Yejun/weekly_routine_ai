import json

genders = ["M", "F"]
levels = ["Beginner", "Novice", "Intermediate", "Advanced", "Elite"]
split_ids = ["SPLIT", "FB"]
freqs = [2, 3, 4, 5]

test_cases = []
for gender in genders:
    for level in levels:
        for split_id in split_ids:
            for freq in freqs:
                test_cases.append({
                    "gender": gender,
                    "level": level,
                    "split_id": split_id,
                    "freq": freq
                })

with open("C:\\Users\\yejun\\Desktop\\Project\\weekly_routine_ai\\web\\test_cases.json", "w", encoding="utf-8") as f:
    json.dump(test_cases, f, indent=2, ensure_ascii=False)

print("test_cases.json file created successfully with 80 test cases.")
