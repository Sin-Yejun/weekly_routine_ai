
import json
lang = ['ko', 'en', 'ja', 'zh-Hans', 'zh-Hant', 'id', 'de', 'nl', 'es', 'pt', 'it', 'fr']
def replace_e_name():
    with open('data/post_process.json', 'r', encoding='utf-8') as f:
        post_process_data = json.load(f)

    with open('data/exercise_list_multi.json', 'r', encoding='utf-8') as f:
        exercise_list_multi_data = json.load(f)

    exercise_name_map = {item['code']: item['en'] for item in exercise_list_multi_data}

    for item in post_process_data:
        e_text_id = item.get('e_text_id')
        if e_text_id in exercise_name_map:
            item['e_name'] = exercise_name_map[e_text_id]

    with open('data/post_process_en.json', 'w', encoding='utf-8') as f:
        json.dump(post_process_data, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    replace_e_name()
