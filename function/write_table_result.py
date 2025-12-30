"""
从 new_table_info 表读取 table_prompt，调用大模型获取结果，写入 table_result 字段
"""
import psycopg2
import json
import re
import time
import requests
from typing import Optional
from tqdm import tqdm
from db import get_connection_params
from config import (
    CHATANYWHERE_API_KEY,
    CHATANYWHERE_API_URL,
    CHATANYWHERE_MODEL,
    MAX_RETRIES,
    MAX_TOKENS,
    TEMPERATURE
)

# 动态覆盖 API key
CHATANYWHERE_API_KEY = "sk-tHxZa5r4v06o8DelkankxWKkhVr93LFZrWZ9AcvQ9caAzph9"


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
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except:
        return False


def extract_json_from_text(text: str) -> Optional[str]:
    """从文本中提取JSON内容，去除可能的markdown代码块标记"""
    # 移除可能的markdown代码块标记
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # 尝试找到JSON对象
    # 查找第一个 { 和最后一个 }
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx + 1]
        return json_str
    
    return None


def call_llm_api(prompt: str) -> Optional[str]:
    """调用大模型API"""
    headers = {
        "Authorization": f"Bearer {CHATANYWHERE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": CHATANYWHERE_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS
    }
    
    try:
        response = requests.post(
            CHATANYWHERE_API_URL,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return content
        
        return None
    except requests.exceptions.RequestException as e:
        print(f"API请求错误: {str(e)}")
        return None
    except Exception as e:
        print(f"API调用异常: {str(e)}")
        return None


def validate_json_format(response_text: str) -> Optional[str]:
    """验证返回的文本是否为有效的JSON格式"""
    if not response_text:
        return None
    
    # 提取JSON内容
    json_str = extract_json_from_text(response_text)
    if not json_str:
        return None
    
    try:
        # 尝试解析JSON，验证格式是否正确
        data = json.loads(json_str)
        # 验证通过，返回格式化的JSON字符串
        return json.dumps(data, ensure_ascii=False)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        return None
    except Exception as e:
        print(f"JSON验证错误: {str(e)}")
        return None


def get_llm_result_with_retry(prompt: str) -> Optional[str]:
    """调用大模型并重试，直到获得有效结果或超过最大重试次数"""
    for attempt in range(MAX_RETRIES):
        try:
            # 调用API
            response_text = call_llm_api(prompt)
            if not response_text:
                print(f"  重试 {attempt + 1}/{MAX_RETRIES}: API返回为空")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)  # 等待2秒后重试
                continue
            
            # 验证结果是否为有效的JSON格式
            validated_json = validate_json_format(response_text)
            if validated_json:
                # 验证通过，返回JSON字符串
                return validated_json
            else:
                print(f"  重试 {attempt + 1}/{MAX_RETRIES}: 结果不是有效的JSON格式")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)  # 等待2秒后重试
                continue
                
        except Exception as e:
            print(f"  重试 {attempt + 1}/{MAX_RETRIES}: 发生异常 - {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            continue
    
    # 所有重试都失败
    print(f"  超过最大重试次数 ({MAX_RETRIES})，跳过此记录")
    return None


def process_table_results():
    """处理所有prompt，调用大模型并写入结果"""
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
            SELECT id, table_prompt 
            FROM new_table_info 
            WHERE table_prompt IS NOT NULL 
            AND table_prompt != ''
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 检查 new_table_info 表是否有 table_result 字段
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'new_table_info' 
            AND column_name = 'table_result'
        """)
        has_column = cursor.fetchone() is not None
        
        if not has_column:
            print("创建 table_result 字段...")
            cursor.execute("""
                ALTER TABLE new_table_info 
                ADD COLUMN table_result JSONB
            """)
            conn.commit()
            print("✓ 字段创建成功\n")
        
        # 统计信息
        processed_count = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理大模型请求") as pbar:
            for idx, (record_id, table_prompt) in enumerate(records):
                try:
                    # 每处理10条记录检查一次连接
                    if idx > 0 and idx % 10 == 0:
                        if not check_connection(conn):
                            print(f"\n连接丢失，正在重新连接...")
                            cursor.close()
                            conn.close()
                            conn = create_connection(db_config)
                            cursor = conn.cursor()
                    
                    # 检查是否已经有结果
                    cursor.execute("""
                        SELECT table_result 
                        FROM new_table_info 
                        WHERE id = %s
                    """, (record_id,))
                    existing_result = cursor.fetchone()
                    
                    if existing_result and existing_result[0] is not None:
                        skipped_count += 1
                        pbar.set_postfix({
                            '成功': success_count,
                            '失败': failed_count,
                            '跳过': skipped_count
                        })
                        pbar.update(1)
                        continue
                    
                    # 调用大模型
                    print(f"\n处理 ID: {record_id}")
                    result_json = get_llm_result_with_retry(table_prompt)
                    
                    # 立即写入数据库
                    if result_json:
                        cursor.execute("""
                            UPDATE new_table_info 
                            SET table_result = %s::jsonb
                            WHERE id = %s
                        """, (result_json, record_id))
                        conn.commit()
                        success_count += 1
                        print(f"  ✓ 成功写入数据库")
                    else:
                        # 写入空值
                        cursor.execute("""
                            UPDATE new_table_info 
                            SET table_result = NULL
                            WHERE id = %s
                        """, (record_id,))
                        conn.commit()
                        failed_count += 1
                        print(f"  ✗ 失败，已写入NULL")
                    
                    processed_count += 1
                    pbar.set_postfix({
                        '成功': success_count,
                        '失败': failed_count,
                        '跳过': skipped_count
                    })
                    
                    # 避免请求过快，添加短暂延迟
                    time.sleep(0.5)
                
                except psycopg2.Error as e:
                    print(f"\n处理 ID {record_id} 时数据库错误: {str(e)}")
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
                    print(f"\n处理 ID {record_id} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
                    continue
                
                pbar.update(1)
        
        print(f"\n" + "=" * 60)
        print(f"处理完成！")
        print(f"总计: {processed_count} 条")
        print(f"成功: {success_count} 条")
        print(f"失败: {failed_count} 条")
        print(f"跳过: {skipped_count} 条（已有结果）")
        print("=" * 60)
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
        
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
    process_table_results()
