"""
检查 hea.public.result_merge 表中，相同 identifier 的 text_result 是否存在重复的 alloy_id
若存在，打印出其对应的 identifier 和 alloy_id
"""
import psycopg2
import json
from collections import defaultdict
from db import get_connection_params


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


def extract_alloy_ids_from_text_result(text_result):
    """
    从 text_result 字段中提取所有的 alloy_id
    返回: alloy_id 列表
    """
    alloy_ids = []
    
    if text_result is None:
        return alloy_ids
    
    try:
        if isinstance(text_result, dict):
            result_data = text_result
        elif isinstance(text_result, str):
            result_data = json.loads(text_result)
        else:
            return alloy_ids

        # text_result 数据结构：假定是 dict，alloy_id 在某个固定字段或列表中
        # 示例：{"alloy_id": "XX"} 或 {"results": [{"alloy_id": ...}, ...]}
        if isinstance(result_data, dict):
            # 方案1: 直接在顶层
            if "alloy_id" in result_data:
                alloy_id = result_data["alloy_id"]
                if alloy_id is not None:
                    alloy_ids.append(alloy_id)
            # 方案2: 在 results 列表中
            elif "results" in result_data and isinstance(result_data["results"], list):
                for res in result_data["results"]:
                    if isinstance(res, dict) and "alloy_id" in res:
                        alloy_id = res["alloy_id"]
                        if alloy_id is not None:
                            alloy_ids.append(alloy_id)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # 如果解析失败，返回空列表
        pass

    return alloy_ids


def check_duplicate_alloy_ids_in_text_result():
    """
    检查 hea.public.result_merge 表中，相同 identifier 的 text_result 是否存在重复的 alloy_id
    若存在，打印出其对应的 identifier 和 alloy_id
    """
    db_config = get_connection_params()
    conn = None
    try:
        conn = create_connection(db_config)
        cursor = conn.cursor()
        # 查询所有有 text_result 的记录，包含 identifier
        cursor.execute("""
            SELECT identifier, id, text_result
            FROM hea.public.result_merge
            WHERE text_result IS NOT NULL
            AND text_result::text != 'null'::text
            ORDER BY identifier, id
        """)
        all_records = cursor.fetchall()
        
        print(f"共查询到 {len(all_records)} 条有 text_result 的记录\n")
        
        # 按 identifier 分组
        identifier_to_alloy_ids = defaultdict(lambda: defaultdict(list))
        
        for identifier, record_id, text_result in all_records:
            alloy_ids = extract_alloy_ids_from_text_result(text_result)
            for alloy_id in alloy_ids:
                identifier_to_alloy_ids[identifier][alloy_id].append(record_id)
        
        # 查找重复 alloy_id
        duplicate_found = False
        total_duplicates = 0
        
        for identifier, alloy_id_dict in identifier_to_alloy_ids.items():
            identifier_has_duplicate = False
            for alloy_id, rec_ids in alloy_id_dict.items():
                if len(rec_ids) > 1:
                    if not identifier_has_duplicate:
                        print(f"identifier: {identifier}")
                        identifier_has_duplicate = True
                        duplicate_found = True
                    print(f"  发现重复的 alloy_id: {alloy_id}")
                    print(f"    出现在以下 id 中: {', '.join(map(str, rec_ids))}")
                    total_duplicates += 1
            if identifier_has_duplicate:
                print()
        
        if not duplicate_found:
            print("✓ 未发现重复的 alloy_id（在相同 identifier 下）")
        else:
            print(f"\n共发现 {total_duplicates} 个重复的 alloy_id（在相同 identifier 下）")
    except Exception as e:
        print(f"检查过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    check_duplicate_alloy_ids_in_text_result()

