"""
从 ex_info 表读取 text_alloy_result，将 evidence_source 中的数字ID替换为句子文本，写入 alloy_info 列
"""
import psycopg2
import json
import time
from typing import Dict, List, Optional
from tqdm import tqdm
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


def build_sentence_map(sentence_list: List[Dict]) -> Dict[int, str]:
    """
    从 sentence_list 构建 id -> sentence 的映射字典
    
    Args:
        sentence_list: 句子列表，格式如 [{"id": 1, "sentence": "..."}, ...]
    
    Returns:
        字典，key 为 id，value 为 sentence 文本
    """
    sentence_map = {}
    if not sentence_list or not isinstance(sentence_list, list):
        return sentence_map
    
    for item in sentence_list:
        if isinstance(item, dict) and 'id' in item and 'sentence' in item:
            sentence_id = item.get('id')
            sentence_text = item.get('sentence', '')
            if sentence_id is not None:
                sentence_map[int(sentence_id)] = sentence_text
    
    return sentence_map


def replace_evidence_source_with_text(text_alloy_result: Dict, sentence_list: List[Dict]) -> Optional[Dict]:
    """
    将 text_alloy_result 中的 evidence_source 数字ID替换为句子文本
    
    Args:
        text_alloy_result: 合金结果字典，包含 core_alloys
        sentence_list: 句子列表，用于查找对应的句子文本
    
    Returns:
        处理后的字典，如果处理失败返回 None
    """
    if not text_alloy_result or not isinstance(text_alloy_result, dict):
        return None
    
    # 构建句子映射
    sentence_map = build_sentence_map(sentence_list)
    
    # 深拷贝原字典，避免修改原始数据
    result = json.loads(json.dumps(text_alloy_result))
    
    # 处理 core_alloys
    if 'core_alloys' in result and isinstance(result['core_alloys'], list):
        for alloy in result['core_alloys']:
            if isinstance(alloy, dict) and 'evidence_source' in alloy:
                evidence_ids = alloy.get('evidence_source', [])
                if isinstance(evidence_ids, list):
                    # 将数字ID列表替换为句子文本列表
                    evidence_texts = []
                    for evidence_id in evidence_ids:
                        if isinstance(evidence_id, int) and evidence_id in sentence_map:
                            evidence_texts.append(sentence_map[evidence_id])
                        elif isinstance(evidence_id, (int, str)):
                            # 尝试转换为整数
                            try:
                                evidence_id_int = int(evidence_id)
                                if evidence_id_int in sentence_map:
                                    evidence_texts.append(sentence_map[evidence_id_int])
                            except (ValueError, TypeError):
                                pass
                    
                    # 替换 evidence_source
                    alloy['evidence_source'] = evidence_texts
    
    return result


def process_alloy_info():
    """处理所有记录，将 evidence_source 替换为文本并写入 alloy_info"""
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
        
        # 查询所有需要处理的记录
        print("查询需要处理的记录...")
        cursor.execute("""
            SELECT identifier, text_alloy_result, sentence_list 
            FROM hea.public.ex_info 
            WHERE text_alloy_result IS NOT NULL 
            AND text_alloy_result::text != 'null'::text
            AND sentence_list IS NOT NULL 
            AND sentence_list::text != 'null'::text
            AND sentence_list::text != '[]'::text
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 检查 alloy_info 列是否存在，不存在则创建
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'ex_info' 
            AND column_name = 'alloy_info'
        """)
        has_column = cursor.fetchone() is not None
        
        if not has_column:
            print("创建 alloy_info 字段...")
            cursor.execute("""
                ALTER TABLE hea.public.ex_info 
                ADD COLUMN alloy_info JSONB
            """)
            conn.commit()
            print("✓ 字段创建成功\n")
        
        # 统计信息
        processed_count = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理进度", unit="条") as pbar:
            for record in records:
                try:
                    identifier = record[0]
                    text_alloy_result = record[1]
                    sentence_list = record[2]
                    
                    pbar.set_description(f"处理 {identifier}")
                    
                    # 解析 JSON 数据
                    try:
                        if isinstance(text_alloy_result, str):
                            text_alloy_result = json.loads(text_alloy_result)
                        if isinstance(sentence_list, str):
                            sentence_list = json.loads(sentence_list)
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"\n  ✗ {identifier}: JSON 解析失败 - {str(e)}")
                        skipped_count += 1
                        processed_count += 1
                        pbar.update(1)
                        continue
                    
                    # 替换 evidence_source
                    alloy_info = replace_evidence_source_with_text(text_alloy_result, sentence_list)
                    
                    if alloy_info is None:
                        print(f"\n  ✗ {identifier}: 处理失败，跳过")
                        skipped_count += 1
                    else:
                        # 写入数据库
                        cursor.execute("""
                            UPDATE hea.public.ex_info 
                            SET alloy_info = %s::jsonb
                            WHERE identifier = %s
                        """, (json.dumps(alloy_info, ensure_ascii=False), identifier))
                        conn.commit()
                        success_count += 1
                        print(f"\n  ✓ {identifier}: 成功写入 alloy_info")
                    
                    processed_count += 1
                    pbar.set_postfix({
                        '成功': success_count,
                        '失败': failed_count,
                        '跳过': skipped_count
                    })
                    pbar.update(1)
                    
                except psycopg2.Error as e:
                    print(f"\n处理 identifier {identifier} 时数据库错误: {str(e)}")
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
                    failed_count += 1
                    processed_count += 1
                    pbar.update(1)
                    continue
                    
                except Exception as e:
                    print(f"\n处理 identifier {identifier} 时发生错误: {str(e)}")
                    failed_count += 1
                    processed_count += 1
                    pbar.update(1)
                    continue
        
        # 输出统计信息
        print("\n" + "="*50)
        print("处理完成！")
        print(f"总计: {processed_count} 条")
        print(f"成功: {success_count} 条")
        print(f"失败: {failed_count} 条")
        print(f"跳过: {skipped_count} 条")
        print("="*50)
        
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("\n数据库连接已关闭")


if __name__ == "__main__":
    process_alloy_info()

