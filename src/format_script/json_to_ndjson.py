# pip install ijson
import ijson, json, os, sys
from decimal import Decimal

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

src = "data/json/workout_days.json"
dst = "data/json/workout_days.ndjson"

def find_array_prefix(path: str) -> str | None:
    # JSON 스트림에서 'start_array'가 처음 나오는 prefix를 탐색
    with open(path, "rb") as f:
        for prefix, event, _ in ijson.parse(f):
            if event == "start_array":
                return prefix  # '' 이면 최상위 배열
    return None

prefix = find_array_prefix(src)
print("→ array prefix:", repr(prefix))
if prefix is None:
    print("⚠️  JSON 안에 배열을 못 찾았습니다. 형식을 확인하세요.")
    sys.exit(1)

iter_path = f"{prefix}.item" if prefix else "item"
count = 0

with open(src, "rb") as f_in, open(dst, "w", encoding="utf-8") as f_out:
    for obj in ijson.items(f_in, iter_path):
        f_out.write(json.dumps(obj, ensure_ascii=False, cls=DecimalEncoder) + "\n")
        count += 1
        if count % 100_000 == 0:
            print(f"  wrote {count:,} rows...")

print(f"✅ NDJSON 생성 완료: {dst} (rows={count:,})  size={os.path.getsize(dst):,} bytes")
