
import json

def generate_m_ratio_weight():
    # Load the exercise mapping
    with open('C:/Users/yejun/Desktop/Project/weekly_routine_ai/data/02_processed/processed_query_result_200.json', 'r', encoding='utf-8') as f:
        exercise_data = json.load(f)

    # Create a mapping from eTextId to eName
    etextid_to_ename = {item['eTextId']: item['eName'] for item in exercise_data}

    # Read the ratios and create the new dictionary
    m_ratio_weight = {}
    with open('C:/Users/yejun/Desktop/Project/weekly_routine_ai/src/temp.txt', 'r', encoding='utf-8') as f:
        next(f)  # Skip header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                name, ratio_str = parts
                ratio = float(ratio_str)
                ename = etextid_to_ename.get(name)
                if ename:
                    m_ratio_weight[ename] = ratio
                else:
                    print(f"Warning: eTextId '{name}' not found in mapping file.")


    # Print the resulting dictionary in the desired format
    print("F_ratio_weight = {")
    for name, ratio in m_ratio_weight.items():
        print(f'    "{name}": {ratio},')
    print("}")

if __name__ == "__main__":
    generate_m_ratio_weight()
