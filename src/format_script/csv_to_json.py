
import csv
import json

def convert_csv_to_json(csv_path, json_path):
    exercise_list = []
    with open(csv_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)

        # Map header names to indices for clarity
        header_map = {name.strip().replace('\n', ''): i for i, name in enumerate(header)}
        # Key,Korean(ko),English(en),Japanese(ja),Simplified Chinese (zh-Hans),Traditional Chinese (zh-Hant),Indonesian (id),Deutsch (de),Netherland (nl),Español(es),Portuguese (pt),Italiano (it),Français (fr)
        code_idx = header_map.get('Key', 0)  # Default to index 0 if 'Key' is not found
        ko_idx = header_map.get('Korean(ko)')
        en_idx = header_map.get('English(en)')
        ja_idx = header_map.get('Japanese(ja)')
        zh_hans_idx = header_map.get('Simplified Chinese (zh-Hans)')
        zh_hant_idx = header_map.get('Traditional Chinese (zh-Hant)')
        id_idx = header_map.get('Indonesian (id)')
        de_idx = header_map.get('Deutsch (de)')
        nl_idx = header_map.get('Netherland (nl)')
        es_idx = header_map.get('Español(es)')
        pt_idx = header_map.get('Portuguese (pt)')
        it_idx = header_map.get('Italiano (it)')
        fr_idx = header_map.get('Français (fr)')

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
            }
            exercise_list.append(exercise_data)

    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(exercise_list, json_file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    # Note: This script assumes it is run from the root directory of the project.
    # Adjust paths if necessary.
    convert_csv_to_json('data/bodypart_name_db.csv', 'data/bodypart_name_multi.json')
    print("Conversion complete. JSON file created.")
