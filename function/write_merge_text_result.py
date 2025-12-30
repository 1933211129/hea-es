"""
合并 performance_prompt_text 表中相同 identifier 的 result，写入 result_merge 表
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


def merge_results(results):
    """
    合并多个 result JSON 对象
    将所有 extraction_results 数组合并成一个
    """
    merged_extraction_results = []
    
    for result in results:
        if not result:
            continue
            
        # 解析 result
        if isinstance(result, dict):
            result_data = result
        elif isinstance(result, str):
            try:
                result_data = json.loads(result)
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


def process_merge_results():
    """处理合并结果并写入数据库"""
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
        
        # 查询所有有 result 的记录，按 identifier 分组
        print("查询需要处理的数据...")
        cursor.execute("""
            SELECT identifier, result 
            FROM performance_prompt_text 
            WHERE result IS NOT NULL
            AND result::text != 'null'::text
            ORDER BY identifier
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条有结果的记录\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 按 identifier 分组
        identifier_results = {}
        for identifier, result in records:
            if identifier not in identifier_results:
                identifier_results[identifier] = []
            identifier_results[identifier].append(result)
        
        print(f"找到 {len(identifier_results)} 个不同的 identifier 需要合并\n")
        
        # 统计信息
        total_processed = 0
        total_merged = 0
        skipped_count = 0
        
        # 使用进度条处理每个 identifier
        with tqdm(total=len(identifier_results), desc="合并结果") as pbar:
            for identifier, results in identifier_results.items():
                try:
                    # 合并结果
                    merged_result = merge_results(results)
                    
                    # 检查合并后的结果是否为空
                    if not merged_result.get("extraction_results"):
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 转换为 JSON 字符串
                    try:
                        merged_result_json = json.dumps(merged_result, ensure_ascii=False)
                    except Exception as e:
                        print(f"  JSON 序列化失败: {str(e)}")
                        conn.rollback()
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 写入数据库
                    try:
                        cursor.execute("""
                            INSERT INTO result_merge (identifier, text_result)
                            VALUES (%s, %s::jsonb)
                        """, (identifier, merged_result_json))
                        
                        conn.commit()
                        total_processed += 1
                        total_merged += len(results)
                    except psycopg2.Error as db_error:
                        print(f"  数据库写入错误: {str(db_error)}")
                        conn.rollback()
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                except Exception as e:
                    print(f"\n处理 identifier {identifier} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # 回滚失败的事务
                    try:
                        conn.rollback()
                    except:
                        pass
                    skipped_count += 1
                    continue
                
                pbar.update(1)
        
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"总 identifier 数: {len(identifier_results)}")
        print(f"成功合并: {total_processed} 个 identifier")
        print(f"合并的总记录数: {total_merged} 条")
        print(f"跳过: {skipped_count} 个 identifier（合并后结果为空）")
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
    process_merge_results()
