"""
处理 table_result 数据：
1. 先删除 result_merge 表中 table_result 为 null 的行
2. 为 new_table_info 表中所有 table_result 不为空的值都补充 source
3. 将 new_table_info 表中 identifier 唯一的 table_result 写入 result_merge 表的 table_result 字段
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


def has_source_in_result(result_data):
    """
    检查 result_data 中是否已经有 source 字段
    返回: True 如果有 source，False 如果没有
    """
    if not isinstance(result_data, dict) or "extraction_results" not in result_data:
        return False
    
    extraction_results = result_data["extraction_results"]
    if not isinstance(extraction_results, list):
        return False
    
    # 检查是否有任何 source 字段
    for alloy in extraction_results:
        if not isinstance(alloy, dict):
            continue
        
        # 检查 experimental_conditions 中的 source
        if 'experimental_conditions' in alloy:
            exp_cond = alloy['experimental_conditions']
            if isinstance(exp_cond, dict):
                for key in ['electrolyte', 'test_setup', 'synthesis_method']:
                    if key in exp_cond and isinstance(exp_cond[key], dict):
                        if 'source' in exp_cond[key]:
                            return True
                if 'other_environmental_params' in exp_cond:
                    if isinstance(exp_cond['other_environmental_params'], list):
                        for param in exp_cond['other_environmental_params']:
                            if isinstance(param, dict) and 'source' in param:
                                return True
        
        # 检查 performance 中的 source
        if 'performance' in alloy:
            perf = alloy['performance']
            if isinstance(perf, dict):
                if 'overpotential' in perf and isinstance(perf['overpotential'], list):
                    for item in perf['overpotential']:
                        if isinstance(item, dict) and 'source' in item:
                            return True
                if 'tafel_slope' in perf and isinstance(perf['tafel_slope'], dict):
                    if 'source' in perf['tafel_slope']:
                        return True
                if 'stability' in perf and isinstance(perf['stability'], dict):
                    if 'source' in perf['stability']:
                        return True
                if 'supplementary_performance' in perf:
                    if isinstance(perf['supplementary_performance'], list):
                        for item in perf['supplementary_performance']:
                            if isinstance(item, dict) and 'source' in item:
                                return True
    
    return False


def extract_alloy_ids(table_result):
    """
    从 table_result 中提取所有的 alloy_id
    返回: alloy_id 列表
    """
    alloy_ids = []
    
    if table_result is None:
        return alloy_ids
    
    try:
        # 解析 JSON
        if isinstance(table_result, dict):
            result_data = table_result
        elif isinstance(table_result, str):
            result_data = json.loads(table_result)
        else:
            return alloy_ids
        
        # 检查是否有 extraction_results 字段
        if not isinstance(result_data, dict) or "extraction_results" not in result_data:
            return alloy_ids
        
        extraction_results = result_data["extraction_results"]
        if not isinstance(extraction_results, list):
            return alloy_ids
        
        # 提取所有 alloy_id
        for alloy in extraction_results:
            if isinstance(alloy, dict) and "alloy_id" in alloy:
                alloy_id = alloy["alloy_id"]
                if alloy_id is not None:
                    alloy_ids.append(alloy_id)
    
    except (json.JSONDecodeError, KeyError, TypeError):
        # 如果解析失败，返回空列表
        pass
    
    return alloy_ids


def has_duplicate_alloy_ids(table_results):
    """
    检查相同 identifier 的多个 table_result 中是否有重复的 alloy_id
    table_results: [(table_id, table_result), ...] 列表
    返回: True 如果有重复，False 如果没有重复
    """
    all_alloy_ids = []
    
    for table_id, table_result in table_results:
        alloy_ids = extract_alloy_ids(table_result)
        all_alloy_ids.extend(alloy_ids)
    
    # 检查是否有重复
    return len(all_alloy_ids) != len(set(all_alloy_ids))


def merge_table_results(table_results):
    """
    合并多个 table_result JSON 对象
    将所有 extraction_results 数组合并成一个
    参考 write_merge_text_result.py 的 merge_results 函数
    """
    merged_extraction_results = []
    
    for table_id, table_result in table_results:
        if not table_result:
            continue
            
        # 解析 result
        if isinstance(table_result, dict):
            result_data = table_result
        elif isinstance(table_result, str):
            try:
                result_data = json.loads(table_result)
            except json.JSONDecodeError:
                continue
        else:
            continue
        
        # 提取 extraction_results
        if isinstance(result_data, dict) and "extraction_results" in result_data:
            extraction_results = result_data["extraction_results"]
            if isinstance(extraction_results, list):
                merged_extraction_results.extend(extraction_results)
    
    # 构造合并后的结果
    merged_result = {
        "extraction_results": merged_extraction_results
    }
    
    return merged_result


def add_source_to_result(result_data, table_id):
    """
    为 table_result 添加 source 字段（如果不存在才添加）
    result_data: 解析后的 JSON 对象
    table_id: 对应的表格 ID
    """
    if not isinstance(result_data, dict) or "extraction_results" not in result_data:
        return result_data
    
    extraction_results = result_data["extraction_results"]
    if not isinstance(extraction_results, list):
        return result_data
    
    # 遍历每个合金记录
    for alloy in extraction_results:
        if not isinstance(alloy, dict):
            continue
        
        # 1. 为 experimental_conditions 添加 source
        if 'experimental_conditions' in alloy:
            exp_cond = alloy['experimental_conditions']
            
            # 检查 exp_cond 是否为 None 或不是字典
            if exp_cond is None or not isinstance(exp_cond, dict):
                continue
            
            # electrolyte, test_setup, synthesis_method 的 source
            for key in ['electrolyte', 'test_setup', 'synthesis_method']:
                if key in exp_cond and isinstance(exp_cond[key], dict):
                    # 如果 source 不存在，才添加
                    if 'source' not in exp_cond[key]:
                        exp_cond[key]['source'] = []
                    if table_id not in exp_cond[key]['source']:
                        exp_cond[key]['source'].append(table_id)
            
            # other_environmental_params 的 source
            if 'other_environmental_params' in exp_cond:
                if isinstance(exp_cond['other_environmental_params'], list):
                    for param in exp_cond['other_environmental_params']:
                        if isinstance(param, dict):
                            # 如果 source 不存在，才添加
                            if 'source' not in param:
                                param['source'] = []
                            if table_id not in param['source']:
                                param['source'].append(table_id)
        
        # 2. 为 performance 添加 source
        if 'performance' in alloy:
            perf = alloy['performance']
            
            # 检查 perf 是否为 None 或不是字典
            if perf is None or not isinstance(perf, dict):
                continue
            
            # overpotential 的 source
            if 'overpotential' in perf:
                if isinstance(perf['overpotential'], list):
                    for item in perf['overpotential']:
                        if isinstance(item, dict):
                            # 如果 source 不存在，才添加
                            if 'source' not in item:
                                item['source'] = []
                            if table_id not in item['source']:
                                item['source'].append(table_id)
            
            # tafel_slope 的 source
            if 'tafel_slope' in perf:
                if isinstance(perf['tafel_slope'], dict):
                    # 如果 source 不存在，才添加
                    if 'source' not in perf['tafel_slope']:
                        perf['tafel_slope']['source'] = []
                    if table_id not in perf['tafel_slope']['source']:
                        perf['tafel_slope']['source'].append(table_id)
            
            # stability 的 source
            if 'stability' in perf:
                if isinstance(perf['stability'], dict):
                    # 如果 source 不存在，才添加
                    if 'source' not in perf['stability']:
                        perf['stability']['source'] = []
                    if table_id not in perf['stability']['source']:
                        perf['stability']['source'].append(table_id)
            
            # supplementary_performance 的 source
            if 'supplementary_performance' in perf:
                if isinstance(perf['supplementary_performance'], list):
                    for item in perf['supplementary_performance']:
                        if isinstance(item, dict):
                            # 如果 source 不存在，才添加
                            if 'source' not in item:
                                item['source'] = []
                            if table_id not in item['source']:
                                item['source'].append(table_id)
    
    return result_data


def process_unique_table_results():
    """处理 table_result 数据"""
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
        
        # ========== 步骤 1: 为 new_table_info 表中所有 table_result 不为空的值补充 source ==========
        print("=" * 80)
        print("步骤 2: 为 new_table_info 表中所有 table_result 不为空的值补充 source")
        print("=" * 80)
        
        # 查询所有有 table_result 的记录
        cursor.execute("""
            SELECT id, table_id, table_result 
            FROM new_table_info 
            WHERE table_result IS NOT NULL
            AND table_result::text != 'null'::text
            ORDER BY id
        """)
        all_records = cursor.fetchall()
        
        print(f"找到 {len(all_records)} 条有结果的记录\n")
        
        if len(all_records) > 0:
            total_updated = 0
            skipped_count = 0
            
            with tqdm(total=len(all_records), desc="补充 source 字段") as pbar:
                for record_id, table_id, table_result in all_records:
                    try:
                        # 解析 table_result
                        if isinstance(table_result, dict):
                            result_data = table_result
                        elif isinstance(table_result, str):
                            try:
                                result_data = json.loads(table_result)
                            except json.JSONDecodeError:
                                skipped_count += 1
                                pbar.update(1)
                                continue
                        else:
                            skipped_count += 1
                            pbar.update(1)
                            continue
                        
                        # 检查是否已经有 source 字段
                        if has_source_in_result(result_data):
                            # 如果已经有 source，跳过（不更新）
                            pbar.update(1)
                            continue
                        
                        # 如果没有 source，才添加 source 字段
                        result_with_source = add_source_to_result(result_data, table_id)
                        
                        # 转换为 JSON 字符串
                        result_json = json.dumps(result_with_source, ensure_ascii=False)
                        
                        # 更新 new_table_info 表
                        cursor.execute("""
                            UPDATE new_table_info 
                            SET table_result = %s::jsonb
                            WHERE id = %s
                        """, (result_json, record_id))
                        
                        conn.commit()
                        total_updated += 1
                        
                    except Exception as e:
                        print(f"\n处理 id {record_id} 时出错: {str(e)}")
                        try:
                            conn.rollback()
                        except:
                            pass
                        skipped_count += 1
                        continue
                    
                    pbar.update(1)
            
            print(f"\n✓ 成功更新 {total_updated} 条记录")
            print(f"跳过 {skipped_count} 条记录（JSON 解析失败或其他错误）\n")
        
        # ========== 步骤 2: 删除 new_table_info 表中 table_result 为 null 的行 ==========
        print("=" * 80)
        print("步骤 2: 删除 new_table_info 表中 table_result 为 null 的行")
        print("=" * 80)
        
        # 先记录删除前的行数
        cursor.execute("SELECT COUNT(*) FROM new_table_info")
        before_delete_count = cursor.fetchone()[0]
        print(f"删除前 new_table_info 表的行数: {before_delete_count}")
        
        cursor.execute("SELECT COUNT(*) FROM new_table_info WHERE table_result IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"找到 {null_count} 条 table_result 为 null 的记录\n")
        
        if null_count > 0:
            # 只删除 table_result IS NULL 的行
            cursor.execute("DELETE FROM new_table_info WHERE table_result IS NULL")
            conn.commit()
            
            # 验证删除后的行数
            cursor.execute("SELECT COUNT(*) FROM new_table_info")
            after_delete_count = cursor.fetchone()[0]
            deleted_count = before_delete_count - after_delete_count
            print(f"✓ 已删除 {deleted_count} 条记录（table_result 为 null 的行）")
            print(f"删除后 new_table_info 表的行数: {after_delete_count}\n")
        else:
            print("✓ 没有需要删除的记录\n")
        
        # ========== 步骤 3: 从 new_table_info 读取 table_result，匹配 result_merge 的 identifier，更新 table_result 字段 ==========
        print("=" * 80)
        print("步骤 3: 从 new_table_info 读取 table_result，匹配 result_merge 的 identifier，更新 table_result 字段")
        print("=" * 80)
        
        # 查询所有有 table_result 的记录
        cursor.execute("""
            SELECT identifier, table_id, table_result 
            FROM new_table_info 
            WHERE table_result IS NOT NULL
            AND table_result::text != 'null'::text
            ORDER BY identifier
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条有结果的记录\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 按 identifier 分组
        identifier_groups = {}
        for identifier, table_id, table_result in records:
            if identifier not in identifier_groups:
                identifier_groups[identifier] = []
            identifier_groups[identifier].append((table_id, table_result))
        
        print(f"共找到 {len(identifier_groups)} 个不同的 identifier\n")
        
        # 统计信息
        total_updated = 0
        total_not_found = 0
        skipped_count = 0
        duplicate_skipped = 0
        
        # 使用进度条处理每个 identifier
        with tqdm(total=len(identifier_groups), desc="处理 identifier") as pbar:
            for identifier, table_results in identifier_groups.items():
                try:
                    # 先检查 result_merge 表中是否存在该 identifier
                    cursor.execute("""
                        SELECT identifier FROM result_merge WHERE identifier = %s
                    """, (identifier,))
                    exists = cursor.fetchone() is not None
                    
                    if not exists:
                        # 如果 identifier 不存在，跳过（不插入，不删除）
                        total_not_found += 1
                        pbar.update(1)
                        continue
                    
                    # 检查相同 identifier 的 table_result 中是否有重复的 alloy_id
                    if has_duplicate_alloy_ids(table_results):
                        # 如果有重复，跳过
                        duplicate_skipped += 1
                        pbar.update(1)
                        continue
                    
                    # 如果没有重复，合并所有 table_result
                    merged_result = merge_table_results(table_results)
                    
                    # 转换为 JSON 字符串
                    result_json = json.dumps(merged_result, ensure_ascii=False)
                    
                    # 只更新现有记录的 table_result 字段（匹配到的才更新，不影响其他字段）
                    cursor.execute("""
                        UPDATE result_merge 
                        SET table_result = %s::jsonb
                        WHERE identifier = %s
                    """, (result_json, identifier))
                    
                    # 验证更新是否成功（不影响其他数据）
                    cursor.execute("SELECT COUNT(*) FROM result_merge WHERE identifier = %s", (identifier,))
                    verify_count = cursor.fetchone()[0]
                    if verify_count != 1:
                        raise Exception(f"更新后验证失败：identifier {identifier} 的行数异常")
                    
                    conn.commit()
                    total_updated += 1
                    
                except Exception as e:
                    print(f"\n处理 identifier {identifier} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    try:
                        conn.rollback()
                    except:
                        pass
                    skipped_count += 1
                    continue
                
                pbar.update(1)
        
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"总 identifier 数: {len(identifier_groups)}")
        print(f"成功更新: {total_updated} 条记录（无重复 alloy_id，已合并并更新）")
        print(f"未匹配到: {total_not_found} 条记录（identifier 不存在，已跳过）")
        print(f"跳过（有重复 alloy_id）: {duplicate_skipped} 个 identifier")
        print(f"跳过（JSON 解析失败或其他错误）: {skipped_count} 条记录")
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
    process_unique_table_results()
