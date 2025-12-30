"""
更新result_merge表，text_result字段的source信息
将source中的数字ID替换为实际的句子内容
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


def get_sentence_dict(identifier, conn, cache):
    """
    根据 identifier 获取 sentence_list，并转换为字典（带缓存）
    
    参数:
        identifier: identifier
        conn: 数据库连接对象
        cache: 缓存字典，key 为 identifier，value 为 sentences_dict
    
    返回:
        sentences_dict: {id: sentence} 字典
    """
    # 检查缓存
    if identifier in cache:
        return cache[identifier]
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # 查询 sentence_list
        cursor.execute("""
            SELECT sentence_list
            FROM ex_info
            WHERE identifier = %s
            AND sentence_list IS NOT NULL
            LIMIT 1
        """, (identifier,))
        
        result = cursor.fetchone()
        if result is None or result[0] is None:
            cache[identifier] = {}
            return {}
        
        sentence_list = result[0]
        
        # 解析 sentence_list
        if isinstance(sentence_list, list):
            sentences_dict = {item.get("id"): item.get("sentence", "") for item in sentence_list if isinstance(item, dict)}
        elif isinstance(sentence_list, str):
            try:
                sentences_data = json.loads(sentence_list)
                if isinstance(sentences_data, list):
                    sentences_dict = {item.get("id"): item.get("sentence", "") for item in sentences_data if isinstance(item, dict)}
                else:
                    sentences_dict = {}
            except json.JSONDecodeError:
                sentences_dict = {}
        else:
            sentences_dict = {}
        
        # 存入缓存
        cache[identifier] = sentences_dict
        return sentences_dict
        
    except Exception as e:
        print(f"获取句子内容时出错 (identifier={identifier}): {str(e)}")
        cache[identifier] = {}
        return {}
    finally:
        if cursor:
            cursor.close()


def get_sentences_by_ids(identifier, sentence_ids, conn, cache):
    """
    根据 identifier 和句子 ID 列表，从缓存中获取对应的句子内容
    
    参数:
        identifier: identifier
        sentence_ids: 句子 ID 列表，如 [60, 61]
        conn: 数据库连接对象
        cache: 缓存字典
    
    返回:
        句子内容列表，如 ["句子1", "句子2"]
    """
    if not sentence_ids:
        return []
    
    # 获取 sentence_dict（带缓存）
    sentences_dict = get_sentence_dict(identifier, conn, cache)
    
    # 根据 sentence_ids 获取对应的句子内容
    sentences = []
    for sid in sentence_ids:
        if sid in sentences_dict:
            sentences.append(sentences_dict[sid])
    
    return sentences


def is_numeric_list(value):
    """判断值是否为数字列表"""
    if not isinstance(value, list):
        return False
    if len(value) == 0:
        return False
    # 检查列表中的所有元素是否都是数字
    return all(isinstance(item, (int, float)) for item in value)


def replace_source_ids(data, identifier, conn, cache):
    """
    递归遍历数据结构，将 source 字段中的数字ID替换为实际句子内容
    
    参数:
        data: 要处理的数据（dict, list 或其他类型）
        identifier: identifier，用于查询句子
        conn: 数据库连接对象
        cache: 缓存字典
    
    返回:
        处理后的数据
    """
    if isinstance(data, dict):
        # 如果是字典，递归处理每个键值对
        result = {}
        for key, value in data.items():
            if key == 'source' and is_numeric_list(value):
                # 如果 key 是 'source' 且值是数字列表，替换为实际句子内容
                sentences = get_sentences_by_ids(identifier, value, conn, cache)
                result[key] = sentences if sentences else value  # 如果找不到句子，保留原值
            else:
                # 递归处理其他字段
                result[key] = replace_source_ids(value, identifier, conn, cache)
        return result
    elif isinstance(data, list):
        # 如果是列表，递归处理每个元素
        return [replace_source_ids(item, identifier, conn, cache) for item in data]
    else:
        # 其他类型直接返回
        return data


def process_text_result_sources():
    """处理 result_merge 表的 text_result 字段，更新 source 信息"""
    db_config = get_connection_params()
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = create_connection(db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功！\n")
        
        # 查询所有需要处理的记录
        print("查询需要处理的记录...")
        cursor.execute("""
            SELECT identifier, text_result
            FROM result_merge
            WHERE text_result IS NOT NULL
            AND text_result::text != 'null'::text
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 统计信息
        processed_count = 0
        updated_count = 0
        error_count = 0
        
        # 缓存字典，避免重复查询同一个 identifier 的 sentence_list
        sentence_cache = {}
        
        # 处理每条记录
        for identifier, text_result in tqdm(records, desc="处理记录"):
            try:
                # 解析 text_result
                if isinstance(text_result, dict):
                    text_result_data = text_result
                elif isinstance(text_result, str):
                    try:
                        text_result_data = json.loads(text_result)
                    except json.JSONDecodeError:
                        print(f"  [错误] identifier={identifier}: text_result JSON 解析失败")
                        error_count += 1
                        continue
                else:
                    print(f"  [跳过] identifier={identifier}: text_result 格式不正确")
                    processed_count += 1
                    continue
                
                # 替换 source 中的数字ID为实际句子内容
                updated_text_result = replace_source_ids(text_result_data, identifier, conn, sentence_cache)
                
                # 检查是否有变化
                if updated_text_result != text_result_data:
                    # 更新数据库
                    cursor.execute("""
                        UPDATE result_merge
                        SET text_result = %s
                        WHERE identifier = %s
                    """, (json.dumps(updated_text_result, ensure_ascii=False), identifier))
                    
                    updated_count += 1
                
                processed_count += 1
                
            except Exception as e:
                print(f"  [错误] identifier={identifier}: {str(e)}")
                error_count += 1
                continue
        
        # 提交事务
        conn.commit()
        
        # 打印统计信息
        print(f"\n处理完成！")
        print(f"  总记录数: {len(records)}")
        print(f"  已处理: {processed_count}")
        print(f"  已更新: {updated_count}")
        print(f"  错误数: {error_count}")
        
    except Exception as e:
        print(f"\n处理过程中发生错误: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    process_text_result_sources()
