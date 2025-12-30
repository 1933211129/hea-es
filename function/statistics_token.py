"""
统计 result_merge 表中 match 字段的 token 数量
"""
import psycopg2
import tiktoken
import json
from db import get_connection_params
from collections import Counter

# 初始化tiktoken编码器
ENCODING = tiktoken.get_encoding("cl100k_base")


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


def count_tokens(text):
    """使用 tiktoken 计算文本的 token 数量"""
    if not text:
        return 0
    return len(ENCODING.encode(text))


def statistics_match_tokens():
    """统计 result_merge 表中 match 字段的 token 数量"""
    db_config = get_connection_params()
    
    conn = None
    cursor = None

    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = create_connection(db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功！\n")
        
        # 查询所有 match 非空的记录
        print("查询数据...")
        cursor.execute("""
            SELECT id, identifier, match
            FROM result_merge
            WHERE match IS NOT NULL
            AND match::text != 'null'::text
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条含有 match 字段的记录\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        print("=" * 100)
        print(f"{'ID':<10} {'Identifier':<40} {'Token数量':<15} {'状态'}")
        print("=" * 100)
        
        total_records = 0
        valid_records = 0
        invalid_records = 0
        token_counts = []
        
        for record_id, identifier, match_field in records:
            total_records += 1
            token_count = 0
            status = ""

            try:
                if match_field:
                    # 类型兼容：如果是dict无需转json，否则是str
                    if isinstance(match_field, dict):
                        match_json_str = json.dumps(match_field, ensure_ascii=False)
                    elif isinstance(match_field, str):
                        match_json_str = match_field
                    else:
                        raise ValueError("match 字段类型未知")
                    
                    token_count = count_tokens(match_json_str)
                    token_counts.append(token_count)
                    valid_records += 1
                    status = "✓"
                else:
                    status = "✗ 为空"
                    invalid_records += 1
            
            except Exception as e:
                status = f"✗ 错误: {str(e)[:30]}"
                invalid_records += 1

            print(f"{record_id:<10} {identifier:<40} {token_count:<15} {status}")
        
        print("=" * 100)
        print("\n统计摘要:")
        print(f"总记录数: {total_records}")
        print(f"有效记录数: {valid_records}")
        print(f"无效记录数: {invalid_records}")
        
        if token_counts:
            print(f"\nToken数量分布:")
            count_distribution = Counter(token_counts)
            for count in sorted(count_distribution.keys()):
                num_records = count_distribution[count]
                perc = (num_records / valid_records * 100) if valid_records else 0
                print(f"  {count} tokens: {num_records} 条记录 ({perc:.1f}%)")
            
            print(f"\nToken数量统计:")
            print(f"  最小值: {min(token_counts)}")
            print(f"  最大值: {max(token_counts)}")
            print(f"  平均值: {sum(token_counts) / len(token_counts):.2f}")
            sorted_counts = sorted(token_counts)
            median_idx = len(sorted_counts) // 2
            if len(sorted_counts) % 2 == 0:
                median = (sorted_counts[median_idx - 1] + sorted_counts[median_idx]) / 2
            else:
                median = sorted_counts[median_idx]
            print(f"  中位数: {median:.2f}")
            
            print(f"\nToken数量区间分布:")
            ranges = [
                (0, 1000, "0-1000"),
                (1000, 2000, "1000-2000"),
                (2000, 4000, "2000-4000"),
                (4000, 8000, "4000-8000"),
                (8000, 16000, "8000-16000"),
                (16000, 32000, "16000-32000"),
                (32000, float("inf"), "32000+")
            ]
            for min_v, max_v, label in ranges:
                count_in_range = sum(1 for tc in token_counts if min_v <= tc < max_v)
                perc = (count_in_range / valid_records * 100) if valid_records else 0
                print(f"  {label:15}: {count_in_range:4} 条记录 ({perc:5.1f}%)")
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    statistics_match_tokens()
