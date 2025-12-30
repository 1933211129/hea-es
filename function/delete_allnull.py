"""
纯统计脚本：检查 result_merge 表的 text_result 字段
找出 experimental_conditions 和 performance 中全是 null 的字段
输出对应的 identifier 和 alloy_id
注意：本脚本只做统计，不对数据本身做任何操作（不修改、不删除）
"""
import psycopg2
import json
from tqdm import tqdm
import pandas as pd
from datetime import datetime
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


def is_all_null(obj, exclude_keys=None):
    """
    检查对象的所有值是否都为 null（排除指定键）
    exclude_keys: 要排除的键列表（如 ['source']）
    """
    if exclude_keys is None:
        exclude_keys = []
    
    if obj is None:
        return True
    
    if not isinstance(obj, dict):
        return False
    
    for key, value in obj.items():
        if key in exclude_keys:
            continue
        if value is not None:
            # 如果是列表，检查列表是否为空或所有元素都为 null
            if isinstance(value, list):
                if len(value) > 0:
                    # 检查列表中是否有非 null 元素
                    for item in value:
                        if item is not None:
                            if isinstance(item, dict):
                                # 如果是字典，递归检查（排除 source）
                                if not is_all_null(item, exclude_keys=exclude_keys):
                                    return False
                            else:
                                return False
            else:
                return False
    return True


def check_experimental_conditions_all_null(exp_cond):
    """
    检查 experimental_conditions 是否全部为 null（排除 source 字段）
    返回: True 如果全部为 null，False 如果有非 null 值
    """
    if exp_cond is None:
        return True
    
    if not isinstance(exp_cond, dict):
        return False
    
    return is_all_null(exp_cond, exclude_keys=['source'])


def check_performance_all_null(performance):
    """
    检查 performance 是否全部为 null（排除 source 字段）
    返回: True 如果全部为 null，False 如果有非 null 值
    """
    if performance is None:
        return True
    
    if not isinstance(performance, dict):
        return False
    
    return is_all_null(performance, exclude_keys=['source'])


def check_text_result(identifier, text_result):
    """
    纯统计：检查单个 text_result 中每个 alloy 的 experimental_conditions 和 performance 是否全部为 null
    返回: [(alloy_id, experimental_conditions_all_null, performance_all_null), ...]
    不修改任何数据
    """
    results = []
    
    # 解析 JSON（只读，不修改）
    if isinstance(text_result, str):
        try:
            result_data = json.loads(text_result)
        except json.JSONDecodeError:
            return results
    elif isinstance(text_result, dict):
        result_data = text_result
    else:
        return results
    
    if not isinstance(result_data, dict) or "extraction_results" not in result_data:
        return results
    
    extraction_results = result_data["extraction_results"]
    if not isinstance(extraction_results, list):
        return results
    
    # 遍历每个合金记录（纯统计，不修改）
    for idx, alloy in enumerate(extraction_results):
        if not isinstance(alloy, dict):
            continue
        
        alloy_id = alloy.get("alloy_id", f"alloy_{idx}")
        
        # 检查 experimental_conditions 是否全部为 null
        exp_cond = alloy.get('experimental_conditions')
        experimental_conditions_all_null = check_experimental_conditions_all_null(exp_cond)
        
        # 检查 performance 是否全部为 null
        performance = alloy.get('performance')
        performance_all_null = check_performance_all_null(performance)
        
        # 只记录有问题的（至少有一个全为 null）
        if experimental_conditions_all_null or performance_all_null:
            results.append((alloy_id, experimental_conditions_all_null, performance_all_null))
    
    return results


def check_allnull_fields():
    """
    纯统计：检查所有 text_result 中的全 null 字段
    不修改任何数据，只输出统计结果
    """
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
        
        # 查询所有有 text_result 的记录（纯查询，不修改数据）
        print("查询需要检查的数据（纯统计，不修改数据）...")
        cursor.execute("""
            SELECT identifier, text_result 
            FROM result_merge 
            WHERE text_result IS NOT NULL
            AND text_result::text != 'null'::text
            ORDER BY identifier
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条有结果的记录\n")
        
        if len(records) == 0:
            print("没有找到需要检查的记录")
            return
        
        # 统计信息
        total_checked = 0
        total_alloys = 0
        results_list = []
        
        # 使用进度条处理每条记录（纯统计，不修改数据）
        with tqdm(total=len(records), desc="统计全null字段") as pbar:
            for identifier, text_result in records:
                try:
                    # 检查该记录（纯统计，不修改数据）
                    alloy_results = check_text_result(identifier, text_result)
                    
                    for alloy_id, exp_all_null, perf_all_null in alloy_results:
                        results_list.append({
                            "identifier": identifier,
                            "alloy_id": alloy_id,
                            "experimental_conditions_all_null": exp_all_null,
                            "performance_all_null": perf_all_null
                        })
                        total_alloys += 1
                    
                    total_checked += 1
                    
                except Exception as e:
                    print(f"\n检查 identifier {identifier} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                pbar.update(1)
        
        # 保存结果到 Excel 文件
        print("\n正在保存结果到 Excel 文件...")
        
        if results_list:
            # 创建 DataFrame
            df_data = []
            for result in results_list:
                exp_status = "全部为null" if result["experimental_conditions_all_null"] else "有非null值"
                perf_status = "全部为null" if result["performance_all_null"] else "有非null值"
                df_data.append({
                    "identifier": result["identifier"],
                    "alloy_id": result["alloy_id"],
                    "experimental_conditions": exp_status,
                    "performance": perf_status
                })
            
            df = pd.DataFrame(df_data)
            
            # 生成文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"allnull_statistics_{timestamp}.xlsx"
            
            # 保存为 Excel 文件
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='全null字段统计', index=False)
                
                # 获取工作表并设置列宽
                worksheet = writer.sheets['全null字段统计']
                worksheet.column_dimensions['A'].width = 30  # identifier
                worksheet.column_dimensions['B'].width = 30  # alloy_id
                worksheet.column_dimensions['C'].width = 25  # experimental_conditions
                worksheet.column_dimensions['D'].width = 20  # performance
            
            print(f"✓ 结果已保存到: {filename}")
            print(f"  总检查 identifier 数: {total_checked}")
            print(f"  有全null字段的 alloy 数: {total_alloys}")
        else:
            print("✓ 没有发现全null字段，无需保存文件")
        
        print("\n统计完成！（纯统计，未修改任何数据）")
        
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
    check_allnull_fields()
