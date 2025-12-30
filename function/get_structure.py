"""
读取 JSON 文件，输出其结构信息（键和值的类型）
"""
import json
from typing import Any, Dict, List, Union


def get_type_name(value: Any) -> str:
    """
    获取值的类型名称
    
    参数:
        value: 任意值
    
    返回:
        类型名称字符串
    """
    if value is None:
        return "null"
    
    type_name = type(value).__name__
    
    # 对于列表，显示元素类型
    if isinstance(value, list):
        if len(value) == 0:
            return "list (empty)"
        # 获取第一个元素的类型
        first_type = get_type_name(value[0])
        return f"list[{first_type}]"
    
    # 对于字典，显示为 dict
    if isinstance(value, dict):
        return "dict"
    
    return type_name


def analyze_structure(data: Any, prefix: str = "", max_depth: int = 10, current_depth: int = 0) -> List[str]:
    """
    递归分析数据结构，返回结构信息列表
    
    参数:
        data: 要分析的数据
        prefix: 当前路径前缀
        max_depth: 最大递归深度
        current_depth: 当前递归深度
    
    返回:
        结构信息列表，每个元素是 "路径: 类型" 的字符串
    """
    results = []
    
    if current_depth >= max_depth:
        return results
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            value_type = get_type_name(value)
            results.append(f"{current_path}: {value_type}")
            
            # 递归处理嵌套的字典和列表
            if isinstance(value, dict):
                results.extend(analyze_structure(value, current_path, max_depth, current_depth + 1))
            elif isinstance(value, list) and len(value) > 0:
                # 对于列表，分析第一个元素的结构
                first_item = value[0]
                if isinstance(first_item, (dict, list)):
                    results.extend(analyze_structure(first_item, f"{current_path}[0]", max_depth, current_depth + 1))
    
    elif isinstance(data, list):
        if len(data) > 0:
            first_item = data[0]
            item_type = get_type_name(first_item)
            results.append(f"{prefix}[0]: {item_type}")
            
            # 递归处理列表中的第一个元素
            if isinstance(first_item, (dict, list)):
                results.extend(analyze_structure(first_item, f"{prefix}[0]", max_depth, current_depth + 1))
    
    return results


def get_json_structure(file_path: str) -> List[str]:
    """
    读取 JSON 文件并返回其结构信息
    
    参数:
        file_path: JSON 文件路径
    
    返回:
        结构信息列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 分析结构
        structure = analyze_structure(data)
        
        return structure
        
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 不存在")
        return []
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 - {str(e)}")
        return []
    except Exception as e:
        print(f"错误: {str(e)}")
        return []


def print_structure(structure: List[str]):
    """
    打印结构信息
    
    参数:
        structure: 结构信息列表
    """
    if not structure:
        print("结构信息为空")
        return
    
    print("JSON 结构信息:")
    print("=" * 80)
    for line in structure:
        print(line)
    print("=" * 80)
    print(f"\n总共 {len(structure)} 个字段")


def main():
    """主函数"""
    test_file = "test.json"
    
    print(f"读取文件: {test_file}")
    print()
    
    structure = get_json_structure(test_file)
    print_structure(structure)


if __name__ == "__main__":
    main()

