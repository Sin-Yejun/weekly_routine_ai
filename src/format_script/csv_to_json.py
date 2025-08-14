
import csv
import json

def convert_csv_to_json(csv_path, json_path):
    exercise_list = []
    with open(csv_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)

        # Map header names to indices for clarity
        header_map = {name.strip().replace('\n', ''): i for i, name in enumerate(header)}

        code_idx = header_map.get('Code')
        ko_idx = header_map.get('Name(ko)')
        en_idx = header_map.get('Name(en)')
        ja_idx = header_map.get('Name(ja)')
        zh_hans_idx = header_map.get('Name(zh-Hans)')
        zh_hant_idx = header_map.get('Name(zh-Hant)')
        id_idx = header_map.get('Name(id)')
        de_idx = header_map.get('Name(de)')
        nl_idx = header_map.get('Name(nl)')
        es_idx = header_map.get('Name(es)')
        pt_idx = header_map.get('Name(pt)')
        it_idx = header_map.get('Name(it)')
        fr_idx = header_map.get('Name(fr)')
        # Category,Info Type,Tool
        bodypart_idx = header_map.get('Category')
        info_type_idx = header_map.get('Info Type')
        tool_idx = header_map.get('Tool')

        for row in csv_reader:
            # Skip empty rows
            if not any(row):
                continue

            exercise_data = {
                'code': row[code_idx] if code_idx is not None and len(row) > code_idx else '',
                'ko': row[ko_idx] if ko_idx is not None and len(row) > ko_idx else '',
                'en': row[en_idx] if en_idx is not None and len(row) > en_idx else '',
                'ja': row[ja_idx] if ja_idx is not None and len(row) > ja_idx else '',
                'zh-Hans': row[zh_hans_idx] if zh_hans_idx is not None and len(row) > zh_hans_idx else '',
                'zh-Hant': row[zh_hant_idx] if zh_hant_idx is not None and len(row) > zh_hant_idx else '',
                'id': row[id_idx] if id_idx is not None and len(row) > id_idx else '',
                'de': row[de_idx] if de_idx is not None and len(row) > de_idx else '',
                'nl': row[nl_idx] if nl_idx is not None and len(row) > nl_idx else '',
                'es': row[es_idx] if es_idx is not None and len(row) > es_idx else '',
                'pt': row[pt_idx] if pt_idx is not None and len(row) > pt_idx else '',
                'it': row[it_idx] if it_idx is not None and len(row) > it_idx else '',
                'fr': row[fr_idx] if fr_idx is not None and len(row) > fr_idx else '',
                'bodypart': int(row[bodypart_idx] if bodypart_idx is not None and len(row) > bodypart_idx else 0),
                'info_type': list(map(int, row[info_type_idx].split(','))) if info_type_idx is not None and len(row) > info_type_idx else [],
                'tool': int(row[tool_idx] if tool_idx is not None and len(row) > tool_idx else 0),
            }
            exercise_list.append(exercise_data)

    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(exercise_list, json_file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    # Note: This script assumes it is run from the root directory of the project.
    # Adjust paths if necessary.
    convert_csv_to_json('data/csv/ai_exercise_list.csv', 'data/multilingual-pack/ai_exercise_list.json')
    print("Conversion complete. JSON file created.")
