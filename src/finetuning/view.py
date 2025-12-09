import json

path = 'data/finetuning_data_v9.jsonl'

with open(path, "r", encoding="utf-8") as f:
    # 첫 번째 줄만 읽기
    first_line = f.readline()
    if first_line.strip():  # 빈 줄이 아닌 경우
        data = json.loads(first_line)
        print(data["messages"][0]["content"])