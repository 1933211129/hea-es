"""
导出 result_merge 表的完整数据到 xlsx 文件
"""
import psycopg2
import json
import pandas as pd
from datetime import datetime
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


def export_result_merge_data():
    """导出 result_merge 表的完整数据到 xlsx 文件"""
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
        
        # 查询所有字段
        print("查询 result_merge 表所有字段...")
        cursor.execute("""
            SELECT * FROM result_merge ORDER BY id
        """)
        records = cursor.fetchall()
        
        # 获取所有字段名
        colnames = [desc[0] for desc in cursor.description]
        
        print(f"找到 {len(records)} 条记录\n")
        
        if len(records) == 0:
            print("没有找到需要导出的记录")
            return
        
        # 准备数据
        print("正在处理数据...")
        data_list = []
        
        # 使用 tqdm 进度条
        with tqdm(total=len(records), desc="处理数据") as pbar:
            for record in records:
                # 转换为字段名-值的字典
                row_dict = {}
                for i, field in enumerate(colnames):
                    value = record[i]
                    # 处理 JSONB 字段，转换为字符串（假设 JSON 字段名包含 "result" 或 "merge" 或 "info" 或以"_json"结尾等，可按需调整）
                    if field.endswith("result") or field.endswith("merge") or field.endswith("info") or field.endswith("_json") or "result" in field or "json" in field or "info" in field or "merge" in field:
                        if value is not None and (isinstance(value, dict) or isinstance(value, list)):
                            value = json.dumps(value, ensure_ascii=False)
                    row_dict[field] = value
                data_list.append(row_dict)
                pbar.update(1)
        
        # 创建 DataFrame
        df = pd.DataFrame(data_list, columns=colnames)
        
        # 生成文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_merge_export_{timestamp}.xlsx"
        
        # 保存为 Excel 文件
        print(f"\n正在保存到 Excel 文件: {filename}...")
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='result_merge', index=False)

            # 设置列宽（可选：自适应或扩展部分主要字段宽度，避免全部字段都超宽）
            worksheet = writer.sheets['result_merge']
            # 可自定义关键列宽度，其他列可默认
            if "id" in colnames:
                worksheet.column_dimensions['A'].width = 10   # id
            if "identifier" in colnames:
                idx = colnames.index("identifier")
                worksheet.column_dimensions[chr(ord('A') + idx)].width = 30
            # 可继续为部分重要字段扩宽
            for i, field in enumerate(colnames):
                if field.endswith("result") or field.endswith("merge") or field.endswith("info") or "result" in field:
                    worksheet.column_dimensions[chr(ord('A') + i)].width = 50
                if field.endswith("num"):
                    worksheet.column_dimensions[chr(ord('A') + i)].width = 12

        print(f"✓ 数据已成功导出到: {filename}")
        print(f"  总记录数: {len(records)}")
        print(f"  列数: {len(df.columns)}")
        
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
    export_result_merge_data()

