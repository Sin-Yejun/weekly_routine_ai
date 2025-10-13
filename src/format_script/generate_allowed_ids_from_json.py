import json
from collections import defaultdict

def generate_allowed_ids_from_json(input_path, output_path):
    """
    Parses a JSON file of exercise data and groups it into a specific format.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            exercises = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        return

    # --- 1. Group exercises by different keys ---
    by_body_region = defaultdict(list)
    by_movement_type = defaultdict(list)
    by_bName = defaultdict(list)
    by_tool = defaultdict(list)

    for exercise in exercises:
        e_name = exercise.get('eName')
        if not e_name:
            continue

        # Group by body_region
        body_region = exercise.get('body_region', 'etc').lower()
        by_body_region[body_region].append(e_name)

        # Group by movement_type
        movement_type = exercise.get('movement_type', 'etc').lower()
        by_movement_type[movement_type].append(e_name)

        # Group by bName (body part)
        b_name = exercise.get('bName', 'Etc').capitalize()
        by_bName[b_name].append(e_name)

        # Group by tool_en
        tool = exercise.get('tool_en', 'Etc').capitalize()
        by_tool[tool].append(e_name)

    # --- 2. Build the final structure ---
    allowed_ids = {}

    # 2-day split (UPPER/LOWER)
    allowed_ids['2'] = {
        "UPPER": sorted(by_body_region.get('upper', [])),
        "LOWER": sorted(by_body_region.get('lower', [])),
        "ETC": sorted(by_body_region.get('etc', []))
    }

    # 3-day split (PUSH/PULL/LEGS)
    allowed_ids['3'] = {
        "PUSH": sorted(by_movement_type.get('push', [])),
        "PULL": sorted(by_movement_type.get('pull', [])),
        "LEGS": sorted(by_movement_type.get('legs', [])),
        "ETC": sorted(by_movement_type.get('etc', []))
    }

    # 4-day and 5-day splits from bName
    chest = sorted(by_bName.get('Chest', []))
    back = sorted(by_bName.get('Back', []))
    shoulder = sorted(by_bName.get('Shoulder', []))
    legs_bname = sorted(by_bName.get('Leg', []))
    arm = sorted(by_bName.get('Arm', []))
    etc_bname = sorted(by_bName.get('Etc', []))

    allowed_ids['4'] = {
        "CHEST": chest,
        "BACK": back,
        "SHOULDER": shoulder,
        "LEGS": legs_bname,
        "ETC": etc_bname
    }
    allowed_ids['5'] = {
        "CHEST": chest,
        "BACK": back,
        "LEGS": legs_bname,
        "SHOULDER": shoulder,
        "ARM": arm,
        "ETC": etc_bname
    }

    # Top-level categories
    allowed_ids['ABS'] = sorted(by_bName.get('Abs', []))
    allowed_ids['CARDIO'] = sorted(by_bName.get('Cardio', []))
    allowed_ids['ETC'] = etc_bname
    
    # Tool category
    allowed_ids['TOOL'] = {k: sorted(v) for k, v in by_tool.items()}

    # --- 3. Write the output file with custom pretty-printing ---
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('{\n')
        num_top_level_items = len(allowed_ids)
        for i, (key, value) in enumerate(sorted(allowed_ids.items())):
            line_end = ',' if i < num_top_level_items - 1 else ''
            if isinstance(value, dict):
                f.write(f'    "{key}": {{\n')
                num_sub_items = len(value)
                for j, (sub_key, sub_value) in enumerate(sorted(value.items())):
                    sub_line_end = ',' if j < num_sub_items - 1 else ''
                    list_str = json.dumps(sub_value, ensure_ascii=False)
                    f.write(f'        "{sub_key}": {list_str}{sub_line_end}\n')
                f.write(f'    }}{line_end}\n')
            else:
                list_str = json.dumps(value, ensure_ascii=False)
                f.write(f'    "{key}": {list_str}{line_end}\n')
        f.write('}\n')

    print(f"Successfully generated {output_path}")

if __name__ == "__main__":
    input_file = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\data\02_processed\processed_query_result_200.json'
    output_file = r'C:\Users\yejun\Desktop\Project\weekly_routine_ai\web\allowed_name_200.json'
    generate_allowed_ids_from_json(input_file, output_file)