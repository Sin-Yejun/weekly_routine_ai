import json

line_num = 2  # 읽고 싶은 줄 번호
with open("data/finetuning_data.jsonl", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, start=1):
        if i == line_num:
            data = json.loads(line)

            # input.txt 저장
            with open("input.txt", "w", encoding="utf-8") as fin:
                fin.write(data.get("input", ""))

            # output.txt 저장
            with open("output.txt", "w", encoding="utf-8") as fout:
                fout.write(data.get("output", ""))
            break
