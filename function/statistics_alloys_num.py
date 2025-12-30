"""
统计 result_merge 表中 text_result 和 table_result 字段的合金实体数量
将统计结果写入 alloy_num 字段
"""
import psycopg2
import json
from db import get_connection_params
from tqdm import tqdm

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


def count_alloys_in_result(result):
    """
    统计 result 中的合金数量
    result: text_result 或 table_result 的 JSON 数据
    返回: 合金数量（int）
    """
    if result is None:
        return 0
    
    try:
        # 解析 JSON
        if isinstance(result, dict):
            result_data = result
        elif isinstance(result, str):
            result_data = json.loads(result)
        else:
            return 0
        
        # 检查是否有 extraction_results 字段
        if not isinstance(result_data, dict) or "extraction_results" not in result_data:
            return 0
        
        extraction_results = result_data["extraction_results"]
        if not isinstance(extraction_results, list):
            return 0
        
        return len(extraction_results)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0


def statistics_alloys():
    """统计每行的合金实体数量并写入 alloy_num 字段"""
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
        
        # 查询所有记录（使用 id 标识）
        print("查询数据...")
        cursor.execute("""
            SELECT id, text_result, table_result 
            FROM result_merge
            ORDER BY id
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 统计信息
        total_processed = 0
        total_updated = 0
        skipped_count = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="统计合金数量") as pbar:
            for record_id, text_result, table_result in records:
                try:
                    # 统计 text_result 中的合金数量
                    text_count = count_alloys_in_result(text_result)
                    
                    # 统计 table_result 中的合金数量
                    table_count = count_alloys_in_result(table_result)
                    
                    # 计算总数
                    total_alloy_count = text_count + table_count
                    
                    # 更新 alloy_num 字段
                    cursor.execute("""
                        UPDATE result_merge 
                        SET alloy_num = %s
                        WHERE id = %s
                    """, (total_alloy_count, record_id))
                    
                    conn.commit()
                    total_processed += 1
                    total_updated += 1
                    
                except Exception as e:
                    print(f"\n处理 id {record_id} 时出错: {str(e)}")
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
        print(f"总记录数: {len(records)}")
        print(f"成功更新: {total_updated} 条记录")
        print(f"跳过: {skipped_count} 条记录（处理错误）")
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
    statistics_alloys()
