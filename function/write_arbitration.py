"""
仲裁脚本：处理 result_merge 表的 text_result 和 table_result
1. 将 text_result 复制到 buffer
2. 将 table_result 中 buffer 没有的 alloy_id 添加到 buffer
3. 匹配 text_result 和 table_result 中相同的 alloy_id，写入 match 列
"""
import psycopg2
import json
from tqdm import tqdm
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


def parse_result(result):
    """
    解析 result（text_result 或 table_result）
    返回: 解析后的字典，如果解析失败返回 None
    """
    if result is None:
        return None
    
    if isinstance(result, dict):
        return result
    elif isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    else:
        return None


def get_alloy_ids(result_data):
    """
    从 result_data 中提取所有的 alloy_id
    返回: alloy_id 列表
    """
    alloy_ids = []
    
    if result_data is None:
        return alloy_ids
    
    if not isinstance(result_data, dict) or "extraction_results" not in result_data:
        return alloy_ids
    
    extraction_results = result_data["extraction_results"]
    if not isinstance(extraction_results, list):
        return alloy_ids
    
    for alloy in extraction_results:
        if isinstance(alloy, dict) and "alloy_id" in alloy:
            alloy_id = alloy["alloy_id"]
            if alloy_id is not None:
                alloy_ids.append(alloy_id)
    
    return alloy_ids


def get_alloy_by_id(result_data, alloy_id):
    """
    从 result_data 中根据 alloy_id 获取对应的 alloy 对象
    返回: alloy 字典，如果不存在返回 None
    """
    if result_data is None:
        return None
    
    if not isinstance(result_data, dict) or "extraction_results" not in result_data:
        return None
    
    extraction_results = result_data["extraction_results"]
    if not isinstance(extraction_results, list):
        return None
    
    for alloy in extraction_results:
        if isinstance(alloy, dict) and alloy.get("alloy_id") == alloy_id:
            return alloy
    
    return None


def merge_buffer_with_table_result(buffer_data, table_result_data):
    """
    将 table_result 中 buffer 没有的 alloy_id 添加到 buffer
    返回: 更新后的 buffer_data
    """
    if buffer_data is None:
        buffer_data = {"extraction_results": []}
    
    if table_result_data is None:
        return buffer_data
    
    # 获取 buffer 中已有的 alloy_id
    buffer_alloy_ids = set(get_alloy_ids(buffer_data))
    
    # 获取 table_result 中的所有 alloy_id
    table_alloy_ids = get_alloy_ids(table_result_data)
    
    # 找出 table_result 中有但 buffer 中没有的 alloy_id
    new_alloy_ids = [aid for aid in table_alloy_ids if aid not in buffer_alloy_ids]
    
    # 将这些新的 alloy 添加到 buffer
    if "extraction_results" not in buffer_data:
        buffer_data["extraction_results"] = []
    
    for alloy_id in new_alloy_ids:
        alloy = get_alloy_by_id(table_result_data, alloy_id)
        if alloy is not None:
            buffer_data["extraction_results"].append(alloy)
    
    return buffer_data


def create_match_result(text_result_data, table_result_data):
    """
    对比 text_result 和 table_result，找出相同的 alloy_id，创建 match 数据
    返回: match 数据字典
    match 格式：
    {
      "extraction_results": [
        {
          "alloy_id": "...",
          "text": {...},  // 来自 text_result
          "table": {...}  // 来自 table_result
        }
      ]
    }
    """
    match_data = {"extraction_results": []}
    
    if text_result_data is None or table_result_data is None:
        return match_data
    
    # 获取 text_result 和 table_result 中的所有 alloy_id
    text_alloy_ids = set(get_alloy_ids(text_result_data))
    table_alloy_ids = set(get_alloy_ids(table_result_data))
    
    # 找出相同的 alloy_id
    common_alloy_ids = text_alloy_ids & table_alloy_ids
    
    # 为每个相同的 alloy_id 创建匹配记录
    for alloy_id in common_alloy_ids:
        text_alloy = get_alloy_by_id(text_result_data, alloy_id)
        table_alloy = get_alloy_by_id(table_result_data, alloy_id)
        
        if text_alloy is not None and table_alloy is not None:
            match_alloy = {
                "alloy_id": alloy_id,
                "text": text_alloy,
                "table": table_alloy
            }
            match_data["extraction_results"].append(match_alloy)
    
    return match_data


def process_arbitration():
    """处理仲裁逻辑"""
    # 从 db.py 获取连接配置
    db_config = get_connection_params()
    
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = create_connection(db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功！\n")
        
        # ========== 步骤1: 将所有 text_result 复制到 buffer ==========
        print("步骤1: 将 text_result 复制到 buffer...")
        cursor.execute("""
            SELECT id, identifier, text_result
            FROM result_merge
            WHERE text_result IS NOT NULL
            AND text_result::text != 'null'::text
            ORDER BY id
        """)
        text_records = cursor.fetchall()
        
        print(f"找到 {len(text_records)} 条有 text_result 的记录\n")
        
        step1_updated = 0
        step1_skipped = 0
        
        if len(text_records) > 0:
            with tqdm(total=len(text_records), desc="步骤1: 复制 text_result 到 buffer") as pbar:
                for record_id, identifier, text_result in text_records:
                    try:
                        # 解析 text_result
                        text_result_data = parse_result(text_result)
                        
                        if text_result_data is None:
                            step1_skipped += 1
                            pbar.update(1)
                            continue
                        
                        # 深拷贝 text_result 到 buffer
                        buffer_data = json.loads(json.dumps(text_result_data))
                        buffer_json = json.dumps(buffer_data, ensure_ascii=False)
                        
                        # 更新 buffer
                        cursor.execute("""
                            UPDATE result_merge 
                            SET buffer = %s::jsonb
                            WHERE id = %s
                        """, (buffer_json, record_id))
                        
                        conn.commit()
                        step1_updated += 1
                        
                    except Exception as e:
                        print(f"\n步骤1: 处理 id {record_id} (identifier: {identifier}) 时出错: {str(e)}")
                        try:
                            conn.rollback()
                        except:
                            pass
                        step1_skipped += 1
                        continue
                    
                    pbar.update(1)
        
        print(f"步骤1完成: 更新 {step1_updated} 条记录，跳过 {step1_skipped} 条记录\n")
        
        # ========== 步骤2和3: 处理 table_result 不为空的记录 ==========
        print("步骤2和3: 处理 table_result 不为空的记录...")
        cursor.execute("""
            SELECT id, identifier, text_result, table_result, buffer, match
            FROM result_merge
            WHERE table_result IS NOT NULL
            AND table_result::text != 'null'::text
            ORDER BY id
        """)
        table_records = cursor.fetchall()
        
        print(f"找到 {len(table_records)} 条有 table_result 的记录\n")
        
        if len(table_records) == 0:
            print("没有找到需要处理的 table_result 记录")
            return
        
        # 统计信息
        step2_processed = 0
        step2_updated_buffer = 0
        step2_updated_match = 0
        step2_skipped = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(table_records), desc="步骤2和3: 合并和匹配") as pbar:
            for record_id, identifier, text_result, table_result, buffer, match in table_records:
                try:
                    # 解析数据
                    text_result_data = parse_result(text_result)
                    table_result_data = parse_result(table_result)
                    
                    if text_result_data is None or table_result_data is None:
                        step2_skipped += 1
                        pbar.update(1)
                        continue
                    
                    # 获取当前的 buffer（如果不存在，使用 text_result）
                    buffer_data = parse_result(buffer)
                    if buffer_data is None:
                        # 如果 buffer 为空，使用 text_result
                        buffer_data = json.loads(json.dumps(text_result_data))
                    
                    # 步骤2: 将 table_result 中 buffer 没有的 alloy_id 添加到 buffer
                    updated_buffer = merge_buffer_with_table_result(buffer_data, table_result_data)
                    buffer_json = json.dumps(updated_buffer, ensure_ascii=False)
                    
                    # 步骤3: 创建 match 数据
                    match_data = create_match_result(text_result_data, table_result_data)
                    match_json = json.dumps(match_data, ensure_ascii=False) if match_data["extraction_results"] else None
                    
                    # 更新数据库
                    if match_json:
                        cursor.execute("""
                            UPDATE result_merge 
                            SET buffer = %s::jsonb, match = %s::jsonb
                            WHERE id = %s
                        """, (buffer_json, match_json, record_id))
                        step2_updated_match += 1
                    else:
                        cursor.execute("""
                            UPDATE result_merge 
                            SET buffer = %s::jsonb
                            WHERE id = %s
                        """, (buffer_json, record_id))
                    
                    conn.commit()
                    step2_processed += 1
                    step2_updated_buffer += 1
                    
                except Exception as e:
                    print(f"\n步骤2和3: 处理 id {record_id} (identifier: {identifier}) 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    try:
                        conn.rollback()
                    except:
                        pass
                    step2_skipped += 1
                    continue
                
                pbar.update(1)
        
        # 输出统计结果
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"\n步骤1统计:")
        print(f"  更新 buffer 的记录数: {step1_updated}")
        print(f"  跳过记录数: {step1_skipped}")
        print(f"\n步骤2和3统计:")
        print(f"  总处理记录数: {step2_processed}")
        print(f"  更新 buffer 的记录数: {step2_updated_buffer}")
        print(f"  更新 match 的记录数: {step2_updated_match}")
        print(f"  跳过记录数: {step2_skipped}")
        print("=" * 80)
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 关闭数据库连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    process_arbitration()

