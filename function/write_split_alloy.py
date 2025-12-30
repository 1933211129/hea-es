"""
将 ex_info 表中的 text_alloy_result 按策略拆分，写入新表 ex_info_text
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


def split_alloys(core_alloys, max_per_group=4):
    """
    根据拆分策略将合金列表拆分为多个组
    
    策略：
    - X <= 4: 不拆分
    - X = 5: 3 + 2
    - X = 6: 3 + 3
    - X = 7: 4 + 3
    - X = 8: 4 + 4
    - X = 9: 3 + 3 + 3
    - 其他情况：尽量4个一组，避免最后一组太小
    """
    total = len(core_alloys)
    
    # 如果总数 <= 4，不拆分
    if total <= max_per_group:
        return [core_alloys]
    
    # 特殊情况处理
    if total == 5:
        groups = [core_alloys[0:3], core_alloys[3:5]]
    elif total == 6:
        groups = [core_alloys[0:3], core_alloys[3:6]]
    elif total == 7:
        groups = [core_alloys[0:4], core_alloys[4:7]]
    elif total == 8:
        groups = [core_alloys[0:4], core_alloys[4:8]]
    elif total == 9:
        groups = [core_alloys[0:3], core_alloys[3:6], core_alloys[6:9]]
    else:
        # 一般情况：计算分组
        groups = []
        quotient = total // max_per_group  # 能分成几组完整的4个
        remainder = total % max_per_group  # 余数
        
        if remainder == 0:
            # 能整除，全部4个一组
            for i in range(quotient):
                start = i * max_per_group
                end = start + max_per_group
                groups.append(core_alloys[start:end])
        elif remainder >= 3:
            # 余数 >= 3，直接分组：4 + 4 + ... + 余数
            for i in range(quotient):
                start = i * max_per_group
                end = start + max_per_group
                groups.append(core_alloys[start:end])
            # 最后一组
            groups.append(core_alloys[quotient * max_per_group:])
        elif remainder == 2:
            # 余数为2，避免最后一组只有2个，将倒数第二组改为3个
            # 例如：10个 -> 4 + 3 + 3，而不是 4 + 4 + 2
            if quotient >= 1:
                # 前面都是4个一组，最后两组改为3+3
                for i in range(quotient - 1):
                    start = i * max_per_group
                    end = start + max_per_group
                    groups.append(core_alloys[start:end])
                # 最后两组，每组3个
                last_start = (quotient - 1) * max_per_group
                groups.append(core_alloys[last_start:last_start + 3])
                groups.append(core_alloys[last_start + 3:])
            else:
                # quotient = 0 的情况（理论上不会到这里，因为 total > 4 且 remainder = 2 意味着 total >= 2）
                # 但为了安全，直接返回
                groups.append(core_alloys)
        elif remainder == 1:
            # 余数为1，根据用户描述，49个的情况是 12组×4 + 1组×1
            for i in range(quotient):
                start = i * max_per_group
                end = start + max_per_group
                groups.append(core_alloys[start:end])
            # 最后一组（只有1个）
            groups.append(core_alloys[quotient * max_per_group:])
    
    # 验证拆分结果
    total_in_groups = sum(len(group) for group in groups)
    if total_in_groups != total:
        raise ValueError(f"拆分错误！原始数量: {total}, 拆分后总数: {total_in_groups}, 分组: {[len(g) for g in groups]}")
    
    return groups


def split_and_write():
    """拆分合金数据并写入新表"""
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
        
        # 查询需要处理的数据
        print("查询需要处理的数据...")
        cursor.execute("""
            SELECT identifier, filename, title, alloy_elements, text_alloy_result
            FROM ex_info
            WHERE text_alloy_result IS NOT NULL
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 统计信息
        total_processed = 0
        total_split = 0
        total_groups = 0
        skipped_count = 0
        identifier_original_counts = {}  # 记录每个identifier的原始合金总数
        identifier_split_counts = {}  # 记录每个identifier拆分后的组数
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理拆分") as pbar:
            for identifier, filename, title, alloy_elements, text_alloy_result in records:
                try:
                    # 解析 text_alloy_result
                    if isinstance(text_alloy_result, dict):
                        result_data = text_alloy_result
                    elif isinstance(text_alloy_result, str):
                        result_data = json.loads(text_alloy_result)
                    else:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 检查是否有 core_alloys
                    if not result_data or "core_alloys" not in result_data:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    core_alloys = result_data["core_alloys"]
                    if not isinstance(core_alloys, list) or len(core_alloys) == 0:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 记录原始合金数量
                    original_count = len(core_alloys)
                    if identifier not in identifier_original_counts:
                        identifier_original_counts[identifier] = 0
                    identifier_original_counts[identifier] += original_count
                    
                    # 拆分合金
                    groups = split_alloys(core_alloys, max_per_group=4)
                    
                    # 验证拆分是否正确：检查总数是否一致
                    total_in_groups = sum(len(group) for group in groups)
                    if total_in_groups != len(core_alloys):
                        print(f"\n错误: identifier {identifier} 拆分验证失败！")
                        print(f"  原始数量: {len(core_alloys)}, 拆分后总数: {total_in_groups}")
                        print(f"  分组情况: {[len(g) for g in groups]}")
                        print(f"  跳过此记录，不写入数据库")
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 额外验证：检查是否有重复的合金ID（在同一组内）
                    for idx, group in enumerate(groups):
                        group_ids = [item.get("id", "") for item in group if isinstance(item, dict)]
                        if len(group_ids) != len(set(group_ids)):
                            duplicates = [id for id in group_ids if group_ids.count(id) > 1]
                            print(f"\n警告: identifier {identifier} 第 {idx+1} 组内有重复的合金ID: {set(duplicates)}")
                    
                    # 记录拆分后的组数
                    if identifier not in identifier_split_counts:
                        identifier_split_counts[identifier] = 0
                    identifier_split_counts[identifier] += len(groups)
                    
                    # 如果只有一组且数量 <= 4，不需要拆分
                    if len(groups) == 1 and len(core_alloys) <= 4:
                        # 直接写入，不拆分
                        result_json = json.dumps(result_data, ensure_ascii=False)
                        cursor.execute("""
                            INSERT INTO ex_info_text (identifier, filename, title, alloy_elements, text_alloy_result)
                            VALUES (%s, %s, %s, %s, %s::jsonb)
                        """, (identifier, filename, title, json.dumps(alloy_elements) if alloy_elements else None, result_json))
                        total_processed += 1
                        total_groups += 1  # 不拆分也算一组
                    else:
                        # 需要拆分，每组写入一条记录
                        total_split += 1
                        for group in groups:
                            # 构造完整的JSON结构
                            split_result = {
                                "core_alloys": group
                            }
                            result_json = json.dumps(split_result, ensure_ascii=False)
                            
                            cursor.execute("""
                                INSERT INTO ex_info_text (identifier, filename, title, alloy_elements, text_alloy_result)
                                VALUES (%s, %s, %s, %s, %s::jsonb)
                            """, (identifier, filename, title, json.dumps(alloy_elements) if alloy_elements else None, result_json))
                            total_groups += 1
                        total_processed += 1
                    
                    # 每处理一条记录就提交
                    conn.commit()
                    
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
        print(f"需要拆分: {total_split} 条")
        print(f"拆分后总组数: {total_groups} 条")
        print(f"跳过: {skipped_count} 条")
        print("=" * 80)
        
        # 输出每个identifier的统计信息
        if identifier_original_counts:
            print("\n按 Identifier 统计（原始合金总数 vs 拆分后组数）:")
            print(f"{'Identifier':<40} {'原始合金总数':<15} {'拆分后组数':<15}")
            print("-" * 80)
            for identifier in sorted(identifier_original_counts.keys()):
                original_total = identifier_original_counts[identifier]
                split_groups = identifier_split_counts.get(identifier, 0)
                print(f"{identifier:<40} {original_total:<15} {split_groups:<15}")
            print("-" * 80)
            print(f"总计: {len(identifier_original_counts)} 个不同的 identifier")
            print(f"所有 identifier 的原始合金总数: {sum(identifier_original_counts.values())}")
            print(f"所有 identifier 的拆分后总组数: {sum(identifier_split_counts.values())}")
        
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
    split_and_write()
