import json
from collections import defaultdict

def process_exercise_data(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create maps for all groupings
    einfo_map = defaultdict(lambda: {'eTextIds': [], 'bNames': set()})
    bname_map = defaultdict(list)
    movement_type_map = defaultdict(list)
    body_region_map = defaultdict(list)

    for item in data:
        einfo_map[item['eInfoType']]['eTextIds'].append(f'"{item["eTextId"]}"')
        einfo_map[item['eInfoType']]['bNames'].add(item['bName'])
        bname_map[item['bName']].append(f'"{item["eTextId"]}"')
        movement_type_map[item['movement_type']].append(f'"{item["eTextId"]}"')
        body_region_map[item['body_region']].append(f'"{item["eTextId"]}"')

    with open(output_path, 'w', encoding='utf-8') as f:
        # --- Write eInfoType groups ---
        f.write("--- Groups by eInfoType ---\
\n")
        for i in range(1, 7):
            f.write(f'"eInfoType": {i}\n')
            bnames = sorted(list(einfo_map[i]['bNames']))
            f.write(','.join([f'"{bname}"' for bname in bnames]) + '\n')
            f.write(','.join(einfo_map[i]['eTextIds']) + '\n\n')

        # --- Write bName groups ---
        f.write("\n--- Groups by bName ---\
\n")
        for bname in sorted(bname_map.keys()):
            f.write(f'"bName": "{bname}"\n')
            f.write(','.join(bname_map[bname]) + '\n\n')

        # --- Write movement_type groups ---
        f.write("\n--- Groups by movement_type ---\
\n")
        for mtype in sorted(movement_type_map.keys()):
            f.write(f'"movement_type": "{mtype}"\n')
            f.write(','.join(movement_type_map[mtype]) + '\n\n')

        # --- Write body_region groups ---
        f.write("\n--- Groups by body_region ---\
\n")
        for region in sorted(body_region_map.keys()):
            f.write(f'"body_region": "{region}"\n')
            f.write(','.join(body_region_map[region]) + '\n\n')

if __name__ == '__main__':
    process_exercise_data(
        'data/02_processed/processed_query_result.json',
        'data/02_processed/eTextIds_by_eInfoType.txt'
    )
