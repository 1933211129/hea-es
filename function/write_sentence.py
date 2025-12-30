import psycopg2
from psycopg2 import sql
import json
import time
from tqdm import tqdm
from split_tool import split_text_to_chunks
from db import get_connection_params

def create_connection(db_config):
    """创建PostgreSQL数据库连接，带重试机制"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
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
            if attempt < max_retries - 1:
                print(f"连接失败，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise

def check_connection(conn):
    """检查PostgreSQL连接是否有效"""
    try:
        # PostgreSQL没有ping方法，通过执行简单查询来检查
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except:
        return False

def test_connection(db_config):
    """测试PostgreSQL数据库连接并检查表信息"""
    print("=" * 60)
    print("正在测试PostgreSQL数据库连接...")
    print(f"主机: {db_config.get('host')}")
    print(f"端口: {db_config.get('port')}")
    print(f"数据库: {db_config.get('database')}")
    print(f"用户: {db_config.get('user')}")
    print("=" * 60)
    
    conn = None
    cursor = None
    
    try:
        # 尝试连接
        print("\n步骤 1: 尝试连接数据库...")
        conn = create_connection(db_config)
        print("✓ 数据库连接成功！")
        
        cursor = conn.cursor()
        
        # 检查表是否存在
        print("\n步骤 2: 检查表 'ex_info' 是否存在...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'ex_info'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            print("✓ 表 'ex_info' 存在")
        else:
            print("✗ 表 'ex_info' 不存在！")
            return False, None, None
        
        # 查询表中的数据条数
        print("\n步骤 3: 查询表中的数据条数...")
        cursor.execute("SELECT COUNT(*) FROM ex_info")
        total_count = cursor.fetchone()[0]
        print(f"✓ 表中共有 {total_count} 条记录")
        
        # 查询有text字段且不为空的记录数
        cursor.execute("SELECT COUNT(*) FROM ex_info WHERE text IS NOT NULL AND text != ''")
        text_count = cursor.fetchone()[0]
        print(f"✓ 其中 {text_count} 条记录有文本内容")
        
        # 查询表结构
        print("\n步骤 4: 检查表结构...")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'ex_info'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print("表字段:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        # 检查是否有sentence_list字段
        has_sentence_list = any(col[0] == 'sentence_list' for col in columns)
        if has_sentence_list:
            print("✓ 'sentence_list' 字段存在")
        else:
            print("⚠ 警告: 'sentence_list' 字段不存在，可能需要创建")
        
        print("\n" + "=" * 60)
        print("连接测试完成！所有检查通过。")
        print("=" * 60 + "\n")
        
        return True, conn, cursor
        
    except psycopg2.Error as e:
        print(f"\n✗ 数据库连接失败！")
        print(f"错误信息: {str(e)}")
        print("\n可能的原因:")
        print("1. 数据库服务器未启动或无法访问")
        print("2. 端口号不正确（PostgreSQL默认5432）")
        print("3. 用户名或密码错误")
        print("4. 数据库名称不正确")
        print("5. 防火墙阻止连接")
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return False, None, None
    except Exception as e:
        print(f"\n✗ 发生未知错误: {str(e)}")
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return False, None, None

def process_sentences():
    """处理数据库中的文本并写入句子切分结果"""

    # 从 db.py 导入数据库连接配置
    db_config = get_connection_params()

    # 先测试连接
    success, conn, cursor = test_connection(db_config)
    if not success:
        print("\n连接测试失败，程序退出。")
        return
    
    try:

        # 查询所有有文本内容的记录
        print("开始处理数据...\n")
        cursor.execute("SELECT id, text FROM ex_info WHERE text IS NOT NULL AND text != ''")
        records = cursor.fetchall()

        if len(records) == 0:
            print("没有找到需要处理的记录（text字段为空或NULL）")
            return
        
        print(f"找到 {len(records)} 条有效记录需要处理\n")

        # 用于批量更新的数据
        batch_data = []
        batch_size = 3
        processed_count = 0

        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理句子切分") as pbar:
            for idx, (record_id, text) in enumerate(records):
                try:
                    # 每处理10条记录检查一次连接
                    if idx > 0 and idx % 10 == 0:
                        if not check_connection(conn):
                            print(f"\n连接丢失，正在重新连接...")
                            cursor.close()
                            conn.close()
                            conn = create_connection(db_config)
                            cursor = conn.cursor()
                    
                    # 调用句子切分函数
                    sentences = split_text_to_chunks(text)

                    # 将结果转换为JSON字符串存储
                    sentence_list_json = json.dumps(sentences, ensure_ascii=False)

                    # 添加到批量更新数据中
                    batch_data.append((sentence_list_json, record_id))
                    processed_count += 1

                    # 每达到batch_size或最后一条时执行批量更新
                    if len(batch_data) >= batch_size or idx == len(records) - 1:
                        # 确保连接有效
                        if not check_connection(conn):
                            print(f"\n连接丢失，正在重新连接...")
                            cursor.close()
                            conn.close()
                            conn = create_connection(db_config)
                            cursor = conn.cursor()
                        
                        # 批量更新数据库
                        update_query = "UPDATE ex_info SET sentence_list = %s WHERE id = %s"
                        cursor.executemany(update_query, batch_data)
                        conn.commit()

                        print(f"\n已更新 {len(batch_data)} 条记录 (总计: {processed_count}/{len(records)})")
                        batch_data = []  # 清空批量数据

                except psycopg2.Error as e:
                    print(f"\n处理记录 ID {record_id} 时数据库错误: {str(e)}")
                    # 尝试重新连接
                    try:
                        if cursor:
                            cursor.close()
                        if conn:
                            conn.close()
                        conn = create_connection(db_config)
                        cursor = conn.cursor()
                        print("已重新连接数据库")
                    except:
                        print("重新连接失败")
                        break
                    continue
                    
                except Exception as e:
                    print(f"\n处理记录 ID {record_id} 时出错: {str(e)}")
                    continue

                pbar.update(1)

        print("\n所有记录处理完成！")

    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")

    except Exception as e:
        print(f"发生错误: {str(e)}")

    finally:
        # 关闭数据库连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    process_sentences()
