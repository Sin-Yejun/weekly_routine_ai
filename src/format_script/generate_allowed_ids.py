import json
from collections import defaultdict

def parse_custom_format(file_path):
    """
    Parses the custom text format from eTextIds_by_eInfoType.txt.
    """
    data = defaultdict(dict)
    current_major_key = None

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if line.startswith('--- Groups by'):
            current_major_key = line.split('by ')[-1].split(' ---')[0]
        elif ':' in line and '"' in line and current_major_key:
            try:
                parts = line.split(':')
                if len(parts) == 2:
                    # The sub-key is the value part, e.g., "Abs" from "bName": "Abs"
                    key = parts[1].strip().strip('"')
                    # The next line should contain the values
                    if i + 1 < len(lines):
                        values_line = lines[i + 1].strip()
                        if values_line:
                            values = [v.strip().strip('"') for v in values_line.split(',')]
                            data[current_major_key][key] = values
            except (ValueError, IndexError):
                # Ignore lines that are not in the expected key-value format
                continue
    return data

def main():
    """
    Main function to generate allowed_ids.json.
    """
    input_file = 'data/02_processed/eTextIds_by_eInfoType_old.txt'
    output_file = 'web/allowed_ids_filtered.json'

    # 1. Parse the source file
    grouped_data = parse_custom_format(input_file)

    # 2. Build the new structure for allowed_ids.json
    allowed_ids = {}

    # Helper to get data regardless of key case
    def get_case_insensitive(data_dict, key):
        if not data_dict or not key:
            return None
        for k, v in data_dict.items():
            if k.lower() == key.lower():
                return v
        return None

    # Get all necessary groups
    body_region_group = grouped_data.get('body_region', {})
    movement_type_group = grouped_data.get('movement_type', {})
    bname_group = grouped_data.get('bName', {})
    tool_en_group = grouped_data.get('tool_en', {})

    # --- 2-day split ---
    upper = get_case_insensitive(body_region_group, 'upper')
    lower = get_case_insensitive(body_region_group, 'lower')
    etc_body_region = get_case_insensitive(body_region_group, 'etc')
    if upper and lower:
        allowed_ids['2'] = {
            "UPPER": upper,
            "LOWER": lower,
            "ETC" :etc_body_region,
        }

    # --- 3-day split ---
    push = get_case_insensitive(movement_type_group, 'push')
    pull = get_case_insensitive(movement_type_group, 'pull')
    legs_3day = get_case_insensitive(movement_type_group, 'legs')
    etc_movement_type = get_case_insensitive(movement_type_group, 'etc')
    if push and pull and legs_3day:
        allowed_ids['3'] = {
            "PUSH": push,
            "PULL": pull,
            "LEGS": legs_3day,
            "ETC" :etc_movement_type,
        }

    # --- 4-day and 5-day splits from bName ---
    chest = get_case_insensitive(bname_group, 'Chest')
    back = get_case_insensitive(bname_group, 'Back')
    shoulders = get_case_insensitive(bname_group, 'Shoulder')
    legs_bname = get_case_insensitive(bname_group, 'Leg')
    arm = get_case_insensitive(bname_group, 'Arm')
    etc_bname = get_case_insensitive(bname_group, 'Etc')

    if all([chest, back, shoulders, legs_bname]):
        allowed_ids['4'] = {
            "CHEST": chest,
            "BACK": back,
            "SHOULDER": shoulders,
            "LEGS": legs_bname,
            "ETC" :etc_bname,
        }

    if all([chest, back, legs_bname, shoulders, arm]):
        allowed_ids['5'] = {
            "CHEST": chest,
            "BACK": back,
            "LEGS": legs_bname,
            "SHOULDER": shoulders,
            "ARM": arm,
            "ETC" :etc_bname,
        }

    # --- Top-level categories ---
    abs_exercises = get_case_insensitive(bname_group, 'Abs')
    cardio_exercises = get_case_insensitive(bname_group, 'Cardio')
    if abs_exercises:
        allowed_ids['ABS'] = abs_exercises
    if cardio_exercises:
        allowed_ids['CARDIO'] = cardio_exercises
    if etc_bname:
        allowed_ids['ETC'] = etc_bname
    
    if tool_en_group:
        allowed_ids['TOOL'] = tool_en_group

    # 3. Write the output file with custom formatting
    output_lines = []
    output_lines.append("{")

    num_top_level_items = len(allowed_ids)
    i = 0
    for key, value in sorted(allowed_ids.items()):
        i += 1
        line_end = "," if i < num_top_level_items else ""
        
        if isinstance(value, dict):
            output_lines.append(f'    "{key}": {{')
            
            num_sub_items = len(value)
            j = 0
            for sub_key, sub_value in sorted(value.items()):
                j += 1
                sub_line_end = "," if j < num_sub_items else ""
                list_str = json.dumps(sub_value, ensure_ascii=False)
                output_lines.append(f'        "{sub_key}": {list_str}{sub_line_end}')
                
            output_lines.append(f'    }}{line_end}')
            
        elif isinstance(value, list):
            list_str = json.dumps(value, ensure_ascii=False)
            output_lines.append(f'    "{key}": {list_str}{line_end}')

    output_lines.append("}")
    final_string = "\n".join(output_lines)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_string)

    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    main()
