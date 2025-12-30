"""
写入对齐结果：调用 split_match 和 alignment_text_table_result 进行对齐，更新 text_table_result 字段
"""
import psycopg2
import json
from tqdm import tqdm
from db import get_connection_params
from split_match import split_match_by_identifier
from alignment_text_table_result import (
    build_prompt,
    get_llm_result_with_retry,
    add_source_to_result
)


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


def parse_jsonb(data):
    """解析 JSONB 数据"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def align_text_table_data(split_item):
    """
    对齐单个 split_item（包含 alloy_id, text, table）
    
    参数:
        split_item: 包含 alloy_id, text, table 的字典
    
    返回:
        对齐后的结果字典（包含 source），如果失败返回 None
    """
    try:
        alloy_id = split_item.get('alloy_id')
        text_data = split_item.get('text')
        table_data = split_item.get('table')
        
        if not alloy_id:
            return None
        
        # 构造输入数据格式（与 alignment_text_table_result.py 的 input_test.txt 格式一致）
        # 注意：table_data 可能已经包含 source 字段（table_info），需要保留
        input_data = {
            'alloy_id': alloy_id,
            'text': text_data if text_data else {},
            'table': table_data if table_data else {}
        }
        
        # 构造 prompt
        prompt = build_prompt(input_data)
        
        # 调用 LLM 获取对齐结果
        print(f"    正在对齐 alloy_id: {alloy_id}...")
        result = get_llm_result_with_retry(prompt)
        
        if result is None:
            print(f"    ⚠ LLM 对齐失败，alloy_id: {alloy_id}")
            return None
        
        # 添加 source 字段
        result_dict = result.model_dump()
        result_dict_with_source = add_source_to_result(result_dict, input_data)
        
        # 返回第一个 extraction_result（因为每个 split_item 只包含一个 alloy_id）
        extraction_results = result_dict_with_source.get('extraction_results', [])
        if extraction_results:
            print(f"    ✓ 对齐成功，alloy_id: {alloy_id}")
            return extraction_results[0]  # 返回单个合金的结果
        
        print(f"    ⚠ 对齐结果为空，alloy_id: {alloy_id}")
        return None
        
    except Exception as e:
        print(f"    对齐处理出错 (alloy_id: {split_item.get('alloy_id', 'N/A')}): {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def update_buffer_with_aligned_result(buffer_data, aligned_result):
    """
    根据对齐结果更新 buffer 中对应的 alloy_id 的数据
    
    参数:
        buffer_data: buffer 字段的完整数据（包含 extraction_results 列表）
        aligned_result: 对齐后的单个合金结果（包含 alloy_id）
    
    返回:
        更新后的 buffer_data
    """
    if not isinstance(buffer_data, dict) or 'extraction_results' not in buffer_data:
        return buffer_data
    
    if not isinstance(aligned_result, dict) or 'alloy_id' not in aligned_result:
        return buffer_data
    
    target_alloy_id = aligned_result.get('alloy_id')
    extraction_results = buffer_data.get('extraction_results', [])
    
    # 查找并替换对应的 alloy_id 的结果
    updated = False
    for i, item in enumerate(extraction_results):
        if isinstance(item, dict) and item.get('alloy_id') == target_alloy_id:
            # 找到匹配的 alloy_id，替换整个项
            extraction_results[i] = aligned_result
            updated = True
            break
    
    if not updated:
        # 如果没有找到，添加到列表末尾
        extraction_results.append(aligned_result)
    
    return buffer_data


def process_identifier(identifier, conn, cursor):
    """
    处理单个 identifier 的对齐和更新
    
    参数:
        identifier: identifier
        conn: 数据库连接
        cursor: 数据库游标
    
    返回:
        (success: bool, aligned_count: int, error_message: str)
    """
    try:
        # 1. 调用 split_match_by_identifier 获取需要对齐的列表
        split_results = split_match_by_identifier(identifier)
        
        if not split_results:
            # 如果没有 match 数据，直接复制 buffer 到 text_table_result
            cursor.execute("""
                SELECT buffer
                FROM result_merge
                WHERE identifier = %s
                AND buffer IS NOT NULL
                AND buffer::text != 'null'::text
            """, (identifier,))
            
            result = cursor.fetchone()
            if result and result[0]:
                buffer_data = parse_jsonb(result[0])
                if buffer_data:
                    cursor.execute("""
                        UPDATE result_merge
                        SET text_table_result = %s::jsonb
                        WHERE identifier = %s
                    """, (json.dumps(buffer_data, ensure_ascii=False), identifier))
                    conn.commit()
                    return (True, 0, None)
            
            return (True, 0, "没有 match 数据且 buffer 为空")
        
        # 2. 获取当前的 buffer 数据
        cursor.execute("""
            SELECT buffer
            FROM result_merge
            WHERE identifier = %s
            AND buffer IS NOT NULL
            AND buffer::text != 'null'::text
        """, (identifier,))
        
        buffer_result = cursor.fetchone()
        if not buffer_result or not buffer_result[0]:
            return (False, 0, "buffer 字段为空")
        
        buffer_data = parse_jsonb(buffer_result[0])
        if not buffer_data:
            return (False, 0, "buffer 数据解析失败")
        
        # 3. 对每个 split_item 进行对齐（循环处理所有需要对齐的项）
        aligned_count = 0
        failed_count = 0
        
        print(f"    需要对齐 {len(split_results)} 个 alloy_id")
        for idx, split_item in enumerate(split_results, 1):
            print(f"    [{idx}/{len(split_results)}] 处理 alloy_id: {split_item.get('alloy_id', 'N/A')}")
            aligned_result = align_text_table_data(split_item)
            
            if aligned_result:
                # 更新 buffer 中对应的 alloy_id
                buffer_data = update_buffer_with_aligned_result(buffer_data, aligned_result)
                aligned_count += 1
            else:
                failed_count += 1
        
        # 4. 将更新后的 buffer 写入 text_table_result
        # 即使部分对齐失败，也要更新（保留已对齐的结果）
        cursor.execute("""
            UPDATE result_merge
            SET text_table_result = %s::jsonb
            WHERE identifier = %s
        """, (json.dumps(buffer_data, ensure_ascii=False), identifier))
        conn.commit()
        
        if aligned_count > 0:
            return (True, aligned_count, None)
        else:
            return (False, 0, f"所有对齐都失败（共 {len(split_results)} 个）")
            
    except Exception as e:
        return (False, 0, f"处理出错: {str(e)}")


def process_all_identifiers():
    """处理所有有 match 字段的 identifier"""
    db_config = get_connection_params()
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = create_connection(db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功！\n")
        
        # 查询所有有 match 字段的记录
        print("查询需要处理的记录...")
        cursor.execute("""
            SELECT DISTINCT identifier
            FROM result_merge
            WHERE match IS NOT NULL
            AND match::text != 'null'::text
            ORDER BY identifier
        """)
        
        identifiers = [row[0] for row in cursor.fetchall()]
        
        print(f"找到 {len(identifiers)} 个 identifier 需要处理\n")
        
        if len(identifiers) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 统计信息
        total_processed = 0
        total_success = 0
        total_aligned = 0
        total_failed = 0
        
        # 处理每个 identifier
        for identifier in tqdm(identifiers, desc="处理 identifier"):
            success, aligned_count, error_msg = process_identifier(identifier, conn, cursor)
            
            total_processed += 1
            if success:
                total_success += 1
                total_aligned += aligned_count
            else:
                total_failed += 1
                print(f"  ✗ identifier={identifier}: {error_msg}")
        
        # 处理 match 为空的记录（直接复制 buffer 到 text_table_result）
        print("\n处理 match 为空的记录...")
        cursor.execute("""
            SELECT identifier, buffer
            FROM result_merge
            WHERE (match IS NULL OR match::text = 'null'::text)
            AND buffer IS NOT NULL
            AND buffer::text != 'null'::text
            AND (text_table_result IS NULL OR text_table_result::text = 'null'::text)
        """)
        
        empty_match_records = cursor.fetchall()
        empty_match_count = 0
        
        for identifier, buffer in empty_match_records:
            try:
                buffer_data = parse_jsonb(buffer)
                if buffer_data:
                    cursor.execute("""
                        UPDATE result_merge
                        SET text_table_result = %s::jsonb
                        WHERE identifier = %s
                    """, (json.dumps(buffer_data, ensure_ascii=False), identifier))
                    empty_match_count += 1
            except Exception as e:
                print(f"  ✗ identifier={identifier}: 复制 buffer 失败 - {str(e)}")
        
        conn.commit()
        
        # 输出统计结果
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"总处理 identifier 数: {total_processed}")
        print(f"成功处理: {total_success}")
        print(f"失败处理: {total_failed}")
        print(f"总对齐合金数: {total_aligned}")
        print(f"match 为空直接复制: {empty_match_count}")
        print("=" * 80)
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    process_all_identifiers()

