"""
统计 result_merge 表中 text_result 字段，检查 performance 全为 null 的合金记录
"""
import psycopg2
import json
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


def is_performance_all_null(performance):
    """
    检查 performance 字段是否全部为 null
    检查 overpotential, tafel_slope, stability, supplementary_performance
    """
    if not performance or not isinstance(performance, dict):
        return True
    
    # 检查 overpotential
    overpotential = performance.get("overpotential")
    if overpotential:
        if isinstance(overpotential, list) and len(overpotential) > 0:
            # 检查列表中是否有非空项
            for item in overpotential:
                if item and isinstance(item, dict):
                    # 检查是否有非 null 的值
                    if any(v is not None and v != "" for v in item.values()):
                        return False
        elif overpotential and not isinstance(overpotential, list):
            # 如果不是列表但有值，也不算全 null
            return False
    
    # 检查 tafel_slope
    tafel_slope = performance.get("tafel_slope")
    if tafel_slope:
        if isinstance(tafel_slope, dict):
            if any(v is not None and v != "" for v in tafel_slope.values()):
                return False
        elif tafel_slope and not isinstance(tafel_slope, dict):
            return False
    
    # 检查 stability
    stability = performance.get("stability")
    if stability:
        if isinstance(stability, dict):
            if any(v is not None and v != "" for v in stability.values()):
                return False
        elif stability and not isinstance(stability, dict):
            return False
    
    # 检查 supplementary_performance
    supplementary_performance = performance.get("supplementary_performance")
    if supplementary_performance:
        if isinstance(supplementary_performance, list) and len(supplementary_performance) > 0:
            for item in supplementary_performance:
                if item and isinstance(item, dict):
                    if any(v is not None and v != "" for v in item.values()):
                        return False
        elif supplementary_performance and not isinstance(supplementary_performance, list):
            return False
    
    # 所有字段都是 null 或空
    return True


def check_null_performance():
    """检查 performance 全为 null 的合金记录"""
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
        
        # 查询所有有 text_result 的记录
        print("查询数据...")
        cursor.execute("""
            SELECT identifier, text_result 
            FROM result_merge
            WHERE text_result IS NOT NULL
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要检查\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        print("=" * 80)
        print("检查 performance 全为 null 的合金记录\n")
        print(f"{'Identifier':<40} {'Alloy ID':<50}")
        print("=" * 80)
        
        # 统计信息
        total_records = 0
        total_alloys = 0
        null_performance_count = 0
        null_alloys = []  # 存储全为 null 的合金记录
        
        for identifier, text_result in records:
            total_records += 1
            
            try:
                # 解析 text_result
                if isinstance(text_result, dict):
                    result_data = text_result
                elif isinstance(text_result, str):
                    result_data = json.loads(text_result)
                else:
                    continue
                
                if not result_data or "extraction_results" not in result_data:
                    continue
                
                extraction_results = result_data["extraction_results"]
                if not isinstance(extraction_results, list):
                    continue
                
                # 遍历每个合金
                for alloy in extraction_results:
                    total_alloys += 1
                    
                    if not isinstance(alloy, dict):
                        continue
                    
                    alloy_id = alloy.get("alloy_id", "未知")
                    performance = alloy.get("performance")
                    
                    # 检查 performance 是否全为 null
                    if is_performance_all_null(performance):
                        null_performance_count += 1
                        null_alloys.append((identifier, alloy_id))
                        print(f"{identifier:<40} {alloy_id:<50}")
                    
            except json.JSONDecodeError as e:
                print(f"处理 identifier {identifier} 时JSON解析错误: {str(e)}")
                continue
            except Exception as e:
                print(f"处理 identifier {identifier} 时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        print("=" * 80)
        print("\n统计摘要:")
        print(f"总记录数: {total_records}")
        print(f"总合金数: {total_alloys}")
        print(f"performance 全为 null 的合金数: {null_performance_count}")
        print(f"占比: {(null_performance_count / total_alloys * 100) if total_alloys > 0 else 0:.2f}%")
        
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
    check_null_performance()
