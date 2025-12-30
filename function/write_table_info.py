"""
从 table_figure_info 表读取 table_info，拆分后写入 new_table_info 表
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


def process_table_info():
    """处理表格信息并写入新表"""
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
        
        # 查询需要处理的数据（table_info 不为空）
        print("查询需要处理的数据...")
        cursor.execute("""
            SELECT identifier, table_info 
            FROM table_figure_info 
            WHERE table_info IS NOT NULL
            AND table_info::text != 'null'::text
            AND table_info::text != '[]'::text
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 统计信息
        total_processed = 0
        total_single = 0
        total_split = 0
        total_rows = 0
        skipped_count = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理表格信息") as pbar:
            for identifier, table_info in records:
                try:
                    # 解析 table_info
                    if isinstance(table_info, list):
                        table_info_list = table_info
                    elif isinstance(table_info, str):
                        try:
                            table_info_list = json.loads(table_info)
                        except json.JSONDecodeError:
                            print(f"\n警告: identifier {identifier} 的 table_info 不是有效的 JSON 格式")
                            skipped_count += 1
                            pbar.update(1)
                            continue
                    else:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 检查是否为列表
                    if not isinstance(table_info_list, list):
                        print(f"\n警告: identifier {identifier} 的 table_info 不是列表格式")
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 检查列表是否为空
                    if len(table_info_list) == 0:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 如果只有一个元素
                    if len(table_info_list) == 1:
                        # 直接写入，table_id 为 identifier_1
                        table_id = f"{identifier}_1"
                        single_table_info = json.dumps(table_info_list[0], ensure_ascii=False)
                        
                        cursor.execute("""
                            INSERT INTO new_table_info (identifier, table_id, table_info)
                            VALUES (%s, %s, %s::jsonb)
                        """, (identifier, table_id, single_table_info))
                        
                        total_single += 1
                        total_rows += 1
                    else:
                        # 多个元素，拆分成多行
                        for idx, table_item in enumerate(table_info_list, start=1):
                            table_id = f"{identifier}_{idx}"
                            table_info_json = json.dumps(table_item, ensure_ascii=False)
                            
                            cursor.execute("""
                                INSERT INTO new_table_info (identifier, table_id, table_info)
                                VALUES (%s, %s, %s::jsonb)
                            """, (identifier, table_id, table_info_json))
                            
                            total_rows += 1
                        
                        total_split += 1
                    
                    # 每处理一条记录就提交
                    conn.commit()
                    total_processed += 1
                    
                except json.JSONDecodeError as e:
                    print(f"\n处理 identifier {identifier} 时JSON解析错误: {str(e)}")
                    skipped_count += 1
                    continue
                except Exception as e:
                    print(f"\n处理 identifier {identifier} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    skipped_count += 1
                    continue
                
                pbar.update(1)
        
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"总记录数: {len(records)}")
        print(f"成功处理: {total_processed} 条")
        print(f"单个表格: {total_single} 条")
        print(f"多个表格（已拆分）: {total_split} 条")
        print(f"拆分后总行数: {total_rows} 条")
        print(f"跳过: {skipped_count} 条")
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
    process_table_info()
