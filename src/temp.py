# deArrIndex, eInfoType, tId // 후처리
# eName, eTextId, bName, bTextId   // AI 추론
import json

output_example = [
    {
        "bName": "가슴",
        "bTextId": "CAT_CHEST",
        "eName": "벤치프레스",
        "eTextId": "BB_BP",
        "totSets": 3,
    },
    {
        "bName": "가슴",
        "bTextId": "CAT_CHEST",
        "eName": "덤벨 벤치프레스",
        "eTextId": "DB_BP",
        "totSets": 3,
    },
    {
        "bName": "가슴",
        "bTextId": "CAT_CHEST",
        "eName": "인클라인 덤벨 벤치프레스",
        "eTextId": "DB_INC_BP",
    },
    {
        "bName": "가슴",
        "bTextId": "CAT_CHEST",
        "eName": "딥스",
        "eTextId": "DIPS",
        "totSets": 3
    },
    {
        "bName": "유산소",
        "bTextId": "CAT_CARDIO",
        "eName": "트레드밀",
        "eTextId": "TREADMIL",
        "totSets": 1
    }
]

with open('data/post_process.json', 'r', encoding='utf-8') as f:
    exercise_list = json.load(f)

# e_text_id를 키로 사용하여 e_info_type과 t_id를 저장할 딕셔너리 생성
exercise_lookup = {}
for exercise in exercise_list:
    e_text_id = exercise.get("e_text_id")
    if e_text_id not in exercise_lookup:
        exercise_lookup[e_text_id] = {
            "eInfoType": exercise.get("e_info_type"),
            "tId": exercise.get("t_id")
        }

deArrIndex = 0
# output_example의 각 항목에 eInfoType과 tId 정보 추가
for item in output_example:
    e_text_id = item.get("eTextId")
    if e_text_id in exercise_lookup:
        info = exercise_lookup[e_text_id]
        item["eInfoType"] = info.get("eInfoType")
        item["tId"] = info.get("tId")
        item["deArrIndex"] = deArrIndex
    deArrIndex += 1
print(json.dumps(output_example, indent=4, ensure_ascii=False))