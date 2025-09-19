import json
from collections import defaultdict

def process_exercise_data(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create maps for all groupings
    einfo_map = defaultdict(lambda: {'eNames': [], 'bNames': set()})
    bname_map = defaultdict(list)
    movement_type_map = defaultdict(list)
    body_region_map = defaultdict(list)
    tool_en_map = defaultdict(list)
    cm_ex_list = []
    high_sum_list = []

    for item in data:
        einfo_map[item['eInfoType']]['eNames'].append(f'"{item["eName"]}"')
        einfo_map[item['eInfoType']]['bNames'].add(item['bName'])
        bname_map[item['bName']].append(f'"{item["eName"]}"')
        movement_type_map[item['movement_type']].append(f'"{item["eName"]}"')
        body_region_map[item['body_region']].append(f'"{item["eName"]}"')
        if 'tool_en' in item:
            tool_en_map[item['tool_en']].append(f'"{item["eName"]}"')

        # Check for cm_ex condition
        if item.get('MG_num', 0) >= 3 and item.get('up_4', 0) >= 3:
            cm_ex_list.append(f'"{item["eName"]}"')

        # Add new condition for musle_point_sum
        if item.get('musle_point_sum', 0) >= 15:
            high_sum_list.append(f'"{item["eName"]}"')

    with open(output_path, 'w', encoding='utf-8') as f:
        # --- Write eInfoType groups ---
        f.write("--- Groups by eInfoType ---\n\n")
        for i in range(1, 7):
            f.write(f'"eInfoType": {i}\n')
            bnames = sorted(list(einfo_map[i]['bNames']))
            f.write(','.join([f'"{bname}"' for bname in bnames]) + '\n')
            f.write(','.join(einfo_map[i]['eNames']) + '\n\n')

        # --- Write bName groups ---
        f.write("\n--- Groups by bName ---\n\n")
        for bname in sorted(bname_map.keys()):
            f.write(f'"bName": "{bname}"\n')
            f.write(','.join(bname_map[bname]) + '\n\n')

        # --- Write movement_type groups ---
        f.write("\n--- Groups by movement_type ---\n\n")
        for mtype in sorted(movement_type_map.keys()):
            f.write(f'"movement_type": "{mtype}"\n')
            f.write(','.join(movement_type_map[mtype]) + '\n\n')

        # --- Write body_region groups ---
        f.write("\n--- Groups by body_region ---\n\n")
        for region in sorted(body_region_map.keys()):
            f.write(f'"body_region": "{region}"\n')
            f.write(','.join(body_region_map[region]) + '\n\n')
            
        # --- Write tool_en groups ---
        f.write("\n--- Groups by tool_en ---\n\n")
        for tool in sorted(tool_en_map.keys()):
            f.write(f'"tool_en": "{tool}"\n')
            f.write(','.join(tool_en_map[tool]) + '\n\n')

        # --- Write cm_ex group ---
        f.write("\n--- Group by cm_ex ---\n\n")
        f.write('"cm_ex":\n')
        f.write(','.join(cm_ex_list) + '\n\n')

        # --- Write new high_sum group ---
        f.write("\n--- Group by musle_point_sum_15_plus ---\n\n")
        f.write('"musle_point_sum_15_plus":\n')
        f.write(','.join(high_sum_list) + '\n\n')

if __name__ == '__main__':
    process_exercise_data(
        'data/02_processed/processed_query_result_filtered.json',
        'data/02_processed/eNames_by_eInfoType_filtered.txt'
    )