import json
with open("web/allowed_ids.json", "r", encoding="utf-8") as f:
    ALLOWED_IDS = json.load(f)

print(ALLOWED_IDS)