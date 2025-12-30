"""
匹配图片信息：读取 text_table_result，匹配 figure_info，更新 merge_result 字段
"""
import psycopg2
import json
import re
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


def parse_jsonb(data):
    """解析 JSONB 数据"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def normalize_text(text):
    """
    标准化文本用于匹配（去除空格、转换为小写、去除标点等）
    """
    if not isinstance(text, str):
        return ""
    # 转换为小写，去除前后空格
    text = text.lower().strip()
    # 去除多余的空白字符
    text = " ".join(text.split())
    # 去除常见的标点符号（保留字母数字和基本符号）
    text = re.sub(r'[^\w\s]', ' ', text)
    text = " ".join(text.split())
    return text


def texts_match(text1, text2):
    """
    判断两个文本是否匹配
    使用标准化后的文本进行比较，支持部分匹配和关键词匹配
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if not norm1 or not norm2:
        return False
    
    # 完全匹配
    if norm1 == norm2:
        return True
    
    # 部分匹配：检查一个文本是否包含另一个
    if norm1 in norm2 or norm2 in norm1:
        # 如果较短的文本长度 >= 10，认为匹配成功
        shorter = min(len(norm1), len(norm2))
        if shorter >= 10:
            return True
    
    # 提取关键词进行匹配（对于较长的文本）
    if len(norm1) > 30 or len(norm2) > 30:
        # 提取重要的单词（长度 >= 4 的单词）
        words1 = set([w for w in re.findall(r'\b\w{4,}\b', norm1)])
        words2 = set([w for w in re.findall(r'\b\w{4,}\b', norm2)])
        
        if words1 and words2:
            # 计算重叠度
            intersection = words1 & words2
            union = words1 | words2
            if union:
                overlap_ratio = len(intersection) / len(union)
                # 如果重叠度 >= 0.3 且至少有2个共同关键词，认为匹配
                if overlap_ratio >= 0.3 and len(intersection) >= 2:
                    return True
    
    return False


def match_figure_to_source(source_list, figure_info_list):
    """
    匹配 source 列表中的文本与 figure_info 列表
    
    参数:
        source_list: source 文本列表，如 ["sentence 1", "sentence 2"]
        figure_info_list: figure_info 列表，每个元素包含 location 和 reference_text_list
    
    返回:
        匹配到的 figure_info 字典，如果没有匹配返回 None
    """
    if not source_list or not figure_info_list:
        return None
    
    # 遍历所有 figure_info
    for figure_info in figure_info_list:
        if not isinstance(figure_info, dict):
            continue
        
        location = figure_info.get('location', '')
        reference_text_list = figure_info.get('reference_text_list', [])
        
        # 检查 location 是否匹配任何 source 文本
        if location:
            for source_text in source_list:
                if isinstance(source_text, str) and texts_match(location, source_text):
                    return figure_info
        
        # 检查 reference_text_list 中的每个文本是否匹配任何 source 文本
        if isinstance(reference_text_list, list):
            for ref_text in reference_text_list:
                if not isinstance(ref_text, str):
                    continue
                for source_text in source_list:
                    if isinstance(source_text, str) and texts_match(ref_text, source_text):
                        return figure_info
    
    return None


def add_figure_source_to_data(data, figure_info_list):
    """
    递归遍历数据结构，为匹配的 source 字段添加 figure_source
    
    参数:
        data: 要处理的数据（dict, list 或其他类型）
        figure_info_list: figure_info 列表
    
    返回:
        (处理后的数据, 是否已匹配)
    """
    if isinstance(data, dict):
        result = {}
        matched = False
        
        for key, value in data.items():
            if key == 'source' and isinstance(value, list):
                # 找到 source 字段，尝试匹配
                matched_figure = match_figure_to_source(value, figure_info_list)
                if matched_figure:
                    # 匹配成功，添加 figure_source
                    result[key] = value
                    result['figure_source'] = matched_figure
                    matched = True
                else:
                    # 未匹配，保持原样
                    result[key] = value
            else:
                # 递归处理其他字段
                processed_value, sub_matched = add_figure_source_to_data(value, figure_info_list)
                result[key] = processed_value
                if sub_matched:
                    matched = True
        
        return result, matched
        
    elif isinstance(data, list):
        result = []
        matched = False
        for item in data:
            processed_item, sub_matched = add_figure_source_to_data(item, figure_info_list)
            result.append(processed_item)
            if sub_matched:
                matched = True
        return result, matched
    else:
        return data, False


def get_figure_info(identifier, conn):
    """
    根据 identifier 从 table_figure_info 表中获取 figure_info
    
    参数:
        identifier: identifier
        conn: 数据库连接
    
    返回:
        figure_info 列表，如果不存在返回空列表
    """
    cursor = None
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT figure_info
            FROM table_figure_info
            WHERE identifier = %s
            AND figure_info IS NOT NULL
            LIMIT 1
        """, (identifier,))
        
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return []
        
        figure_info = result[0]
        
        # 解析 figure_info
        if isinstance(figure_info, list):
            return figure_info
        elif isinstance(figure_info, str):
            try:
                parsed = json.loads(figure_info)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        
        return []
        
    except Exception as e:
        print(f"    获取 figure_info 时出错: {str(e)}")
        return []
    finally:
        if cursor:
            cursor.close()


def process_identifier(identifier, conn, cursor):
    """
    处理单个 identifier 的图片信息匹配
    
    参数:
        identifier: identifier
        conn: 数据库连接
        cursor: 数据库游标
    
    返回:
        (success: bool, matched: bool, error_message: str)
    """
    try:
        # 1. 获取 text_table_result
        cursor.execute("""
            SELECT text_table_result
            FROM result_merge
            WHERE identifier = %s
            AND text_table_result IS NOT NULL
            AND text_table_result::text != 'null'::text
        """, (identifier,))
        
        result = cursor.fetchone()
        if not result or not result[0]:
            return (False, False, "text_table_result 字段为空")
        
        text_table_result = parse_jsonb(result[0])
        if not text_table_result:
            return (False, False, "text_table_result 数据解析失败")
        
        # 2. 获取 figure_info
        figure_info_list = get_figure_info(identifier, conn)
        
        if not figure_info_list:
            # 没有 figure_info，直接复制 text_table_result 到 merge_result
            cursor.execute("""
                UPDATE result_merge
                SET merge_result = %s::jsonb
                WHERE identifier = %s
            """, (json.dumps(text_table_result, ensure_ascii=False), identifier))
            conn.commit()
            return (True, False, None)
        
        # 3. 匹配并添加 figure_source
        merge_result, matched = add_figure_source_to_data(text_table_result, figure_info_list)
        
        # 4. 写入 merge_result
        cursor.execute("""
            UPDATE result_merge
            SET merge_result = %s::jsonb
            WHERE identifier = %s
        """, (json.dumps(merge_result, ensure_ascii=False), identifier))
        conn.commit()
        
        return (True, matched, None)
        
    except Exception as e:
        return (False, False, f"处理出错: {str(e)}")


def process_all_identifiers():
    """处理所有有 text_table_result 的 identifier"""
    db_config = get_connection_params()
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = create_connection(db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功！\n")
        
        # 查询所有有 text_table_result 的记录
        print("查询需要处理的记录...")
        cursor.execute("""
            SELECT DISTINCT identifier
            FROM result_merge
            WHERE text_table_result IS NOT NULL
            AND text_table_result::text != 'null'::text
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
        total_matched = 0
        total_failed = 0
        
        # 处理每个 identifier
        for identifier in tqdm(identifiers, desc="处理 identifier"):
            success, matched, error_msg = process_identifier(identifier, conn, cursor)
            
            total_processed += 1
            if success:
                total_success += 1
                if matched:
                    total_matched += 1
            else:
                total_failed += 1
                print(f"  ✗ identifier={identifier}: {error_msg}")
        
        # 输出统计结果
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"总处理 identifier 数: {total_processed}")
        print(f"成功处理: {total_success}")
        print(f"匹配到图片信息: {total_matched}")
        print(f"未匹配（直接复制）: {total_success - total_matched}")
        print(f"失败处理: {total_failed}")
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

