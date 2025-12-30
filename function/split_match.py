"""
拆分 match 字段：根据 identifier 读取 match 字段，按 alloy_id 拆分
返回每个 alloy_id 需要对齐的表-文信息列表
"""
import psycopg2
import json
from db import get_connection_params

# ========== 配置参数 ==========


def create_connection(db_config):
    """创建PostgreSQL数据库连接"""
    try:
        conn = psycopg2.connect(
            host=db_config.get('host'),
            port=db_config.get('port'),
            database=db_config.get('database'),
            user=db_config.get('user'),
            password=db_config.get('password'),
            connect_timeout=30
        )
        return conn
    except psycopg2.Error as e:
        print(f"数据库连接失败: {str(e)}")
        raise


def get_table_info_by_table_id(table_id):
    """
    根据 table_id 从 new_table_info 表中获取 table_info
    
    参数:
        table_id: table_id，如 '52d505140f7272322ffdf1a7db897458_1'
    
    返回:
        table_info 内容，如果不存在返回 None
    """
    db_config = get_connection_params()
    conn = None
    cursor = None
    
    try:
        conn = create_connection(db_config)
        cursor = conn.cursor()
        
        # 查询 table_info
        cursor.execute("""
            SELECT table_info
            FROM new_table_info
            WHERE table_id = %s
            AND table_info IS NOT NULL
            LIMIT 1
        """, (table_id,))
        
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return None
        
        return result[0]
        
    except Exception as e:
        print(f"获取 table_info 时出错: {str(e)}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def extract_table_id_from_source(obj):
    """
    递归提取 table 对象中所有 source 字段的 table_id
    返回第一个找到的 table_id（因为所有 source 都相同）
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "source" and isinstance(value, list) and len(value) > 0:
                first_item = value[0]
                if isinstance(first_item, str) and "_" in first_item:
                    return first_item  # 返回 table_id
            # 递归查找
            result = extract_table_id_from_source(value)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = extract_table_id_from_source(item)
            if result:
                return result
    return None


def remove_source_fields(obj):
    """
    递归删除对象中所有的 source 字段
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key != "source":
                # 递归处理非 source 字段
                result[key] = remove_source_fields(value)
        return result
    elif isinstance(obj, list):
        return [remove_source_fields(item) for item in obj]
    else:
        return obj


def replace_source_with_content(obj, identifier, table_info_cache=None):
    """
    递归处理对象，保持 source 字段不变（句子内容列表已经存在）
    不再查询 sentence_list，直接返回原对象
    
    参数:
        obj: 要处理的对象（字典、列表等）
        identifier: identifier（保留参数，不再使用）
        table_info_cache: table_info 缓存字典（未使用，保留兼容性）
    
    返回:
        处理后的对象（实际上保持不变，因为句子内容已经存在）
    """
    # 句子内容列表已经存在，不需要替换，直接返回原对象
    return obj


def process_table_source(table_obj):
    """
    处理 table 对象的 source 字段：
    1. 提取所有 source 字段中的 table_id（应该都相同）
    2. 查询一次 table_info
    3. 删除所有子字段中的 source 字段
    4. 在 table 对象最外层添加 source 字段，值为 table_info，放在最后
    
    参数:
        table_obj: table 对象
    
    返回:
        处理后的 table 对象
    """
    if not isinstance(table_obj, dict):
        return table_obj
    
    # 1. 提取 table_id
    table_id = extract_table_id_from_source(table_obj)
    
    # 2. 查询 table_info（如果找到 table_id）
    table_info = None
    if table_id:
        table_info = get_table_info_by_table_id(table_id)
    
    # 3. 删除所有子字段中的 source 字段
    cleaned_table = remove_source_fields(table_obj)
    
    # 4. 在 table 对象最外层添加 source 字段，放在最后
    if table_info is not None:
        # 创建一个新字典，先添加原有字段，最后添加 source
        result = {}
        for key, value in cleaned_table.items():
            result[key] = value
        result["source"] = table_info
        return result
    else:
        return cleaned_table


def split_match_by_identifier(identifier):
    """
    根据 identifier 读取 match 字段，按 alloy_id 拆分，并将 table 的 source 替换为实际 table_info
    
    参数:
        identifier: 要查询的 identifier（字符串）
    
    返回:
        列表，每个元素是一个字典，包含：
        {
            "alloy_id": "...",
            "text": {...},  # 来自 text_result 的数据，source 已经是句子内容列表
            "table": {...}  # 来自 table_result 的数据，source 已替换为实际 table_info
        }
        如果 match 字段为空或不存在，返回空列表
    
    示例:
        >>> results = split_match_by_identifier("0641dcdc064abf0da0c0b376c1bdcecf")
        >>> print(len(results))
    """
    # 从 db.py 获取连接配置
    db_config = get_connection_params()
    
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        conn = create_connection(db_config)
        cursor = conn.cursor()
        
        # 查询指定 identifier 的 match 字段
        cursor.execute("""
            SELECT match
            FROM result_merge
            WHERE identifier = %s
            AND match IS NOT NULL
            AND match::text != 'null'::text
            LIMIT 1
        """, (identifier,))
        
        result = cursor.fetchone()
        
        if result is None or result[0] is None:
            return []
        
        match_data = result[0]
        
        # 解析 match 数据
        if isinstance(match_data, dict):
            match_dict = match_data
        elif isinstance(match_data, str):
            try:
                match_dict = json.loads(match_data)
            except json.JSONDecodeError:
                return []
        else:
            return []
        
        # 检查是否有 extraction_results 字段
        if not isinstance(match_dict, dict) or "extraction_results" not in match_dict:
            return []
        
        extraction_results = match_dict["extraction_results"]
        
        if not isinstance(extraction_results, list):
            return []
        
        # 按 alloy_id 拆分，每个元素就是一个需要对齐的信息
        split_results = []
        
        for item in extraction_results:
            if not isinstance(item, dict):
                continue
            
            # 每个 item 应该包含 alloy_id, text, table
            if "alloy_id" not in item:
                continue
            
            # 构造拆分后的字典
            split_item = {
                "alloy_id": item.get("alloy_id"),
                "text": item.get("text"),  # text 部分的 source 已经是句子内容列表，不需要处理
                "table": item.get("table")
            }
            
            # 处理 table 部分的 source：
            # 1. 提取 table_id（所有 source 都相同，只查询一次）
            # 2. 删除所有子字段中的 source 字段
            # 3. 在 table 对象最外层添加统一的 source 字段，值为 table_info，放在最后
            if split_item["table"]:
                split_item["table"] = process_table_source(split_item["table"])
            
            split_results.append(split_item)
        
        return split_results
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
        raise
        
    except Exception as e:
        print(f"处理错误: {str(e)}")
        raise
        
    finally:
        # 关闭数据库连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_identifiers_with_match():
    """
    获取所有有 match 字段的 identifier 列表
    
    返回:
        identifier 列表
    """
    # 从 db.py 获取连接配置
    db_config = get_connection_params()
    
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        conn = create_connection(db_config)
        cursor = conn.cursor()
        
        # 查询所有有 match 字段的 identifier
        cursor.execute("""
            SELECT DISTINCT identifier
            FROM result_merge
            WHERE match IS NOT NULL
            AND match::text != 'null'::text
            ORDER BY identifier
        """)
        
        results = cursor.fetchall()
        identifiers = [row[0] for row in results]
        
        return identifiers
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
        raise
        
    except Exception as e:
        print(f"处理错误: {str(e)}")
        raise
        
    finally:
        # 关闭数据库连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def main():
    """主函数：测试 split_match_by_identifier 函数"""
    # 测试 identifier
    test_identifier = "0641dcdc064abf0da0c0b376c1bdcecf"
    
    print(f"测试 identifier: {test_identifier}")
    print("=" * 80)
    
    try:
        # 调用函数拆分 match 字段
        split_results = split_match_by_identifier(test_identifier)
        
        print(f"\n✓ 处理成功！")
        print(f"拆分结果数量: {split_results}")
        
        if len(split_results) > 0:
            print(f"\n拆分结果详情:")
            for i, result in enumerate(split_results, 1):
                print(f"\n  [{i}] alloy_id: {result.get('alloy_id', 'N/A')}")
                print(f"      text 字段存在: {result.get('text') is not None}")
                print(f"      table 字段存在: {result.get('table') is not None}")
                if result.get('table') and 'source' in result.get('table', {}):
                    print(f"      table.source 已处理: ✓")
        else:
            print(f"\n⚠ 警告: identifier '{test_identifier}' 没有找到 match 字段或 match 字段为空")
            
    except Exception as e:
        print(f"\n✗ 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

