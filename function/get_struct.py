import json
from pathlib import Path

# 你要分析的 JSON 文件路径，直接在这里修改即可
JSON_PATH = Path(__file__).parent / "data.json"  # 例如：当前目录下的 data.json

def get_type_str(value):
    if isinstance(value, dict):
        return 'object'
    elif isinstance(value, list):
        return 'array'
    elif isinstance(value, str):
        return 'string'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, (int, float)):
        return 'number'
    elif value is None:
        return 'null'
    return type(value).__name__

def print_json_structure(data, indent=0):
    if isinstance(data, dict):
        for k, v in data.items():
            t = get_type_str(v)
            print('  ' * indent + f"{k}: {t}")
            if isinstance(v, dict):
                print_json_structure(v, indent + 1)
            elif isinstance(v, list) and v:
                # Print inner structure of first element (if list is not empty)
                first = v[0]
                if isinstance(first, dict):
                    print_json_structure(first, indent + 1)
    elif isinstance(data, list):
        # Just process first element for structure
        if data:
            print_json_structure(data[0], indent)

def main():
    json_path = JSON_PATH
    if not json_path.exists():
        print(f"未找到文件: {json_path}")
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print_json_structure(data)

if __name__ == '__main__':
    main()
