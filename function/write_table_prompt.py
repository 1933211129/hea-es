"""
从 new_table_info 和 ex_info 表读取数据，构造 table prompt，写入 new_table_info 表
"""
import psycopg2
import json
from string import Template
from tqdm import tqdm
from db import get_connection_params

# Prompt 模板
PROMPT_TEMPLATE = """# Role
你是一位精通电催化析氢反应 (HER) 数据分析的专家。你具备极强的 HTML 表格解析能力，能从科研论文表格中，结合正文引用信息，精准提取合金的实验条件与性能指标。

# Task
请阅读提供的【表格信息】，参照【合金名册】中的合金 ID 及其别称 (aliases)，从 HTML 表格中提取对应的实验参数与性能数据。

# Input Data
1. **【合金名册 (core_alloys)】**：第一步识别出的实体清单。你必须将表格中的样本行精准映射到这些 ID 上。
2. **【表格信息】**：
   - `location`: 表格标题 (Table Caption)，通常包含全局测试条件。
   - `source_content`: HTML 格式的表格原文。
   - `reference_text_list`: 正文中引用该表格的文本，用于辅助理解缩写、代号或补充缺失条件。

# Extraction Logic
1. **表头语义对齐 (Header Mapping)**：
   - 仔细解析 HTML 中的 `<thead>` 或首行 `<tr>`。特别注意复合表头（如上层是 Overpotential，下层是不同的电流密度数值）。
   - 必须将单元格数值与其所属的列标题（性能指标）和行标题（合金名称/代号）精准对应。
2. **别名/代号桥接**：
   - 若表格首列使用的是代号（如 Sample 1, S-1），请结合【合金名册】中的 `aliases` 以及 `reference_text_list` 中的描述，将其还原为正确的 `alloy_id`。
3. **条件综合提取**：
   - 优先从 `location` (Caption) 和 `reference_text_list` 中提取通用的电解液（成分、浓度、pH）及测试环境。
   - 若表格内部列信息与标题信息冲突，以表格内部列标注的特定条件为准。

# Constraints
- **严禁虚构**：若表格和引用文本中均未提及某项，必须填 null。
- **原文还原**：对于非数值字段（如成分、基底等），必须保留原文描述，剔除 HTML 标签，严禁自行翻译或改写。
- **过电位列表化**：overpotential 必须是列表。必须提取表格中展示的所有特征点（如 10, 100 mA cm^-2 等分别对应的数值）。
- **禁止输出解释**：仅输出符合下述 Schema 的合法 JSON 对象。
- 仅返回location、表格信息、reference_text_list中包含的合金名册中的合金ID，其他合金ID若未提及则不必返回。

# Output Schema (Strict JSON)
{
  "extraction_results": [
    {
      "alloy_id": "名册中的原始 ID",
      "experimental_conditions": {
        "electrolyte": {
          "electrolyte_composition": "成分 (如 'KOH') or null",
          "concentration_molar": "浓度 (如 '1.0 M') or null",
          "ph_value": "pH数值 (如 '14.0') or null"
        },
        "test_setup": {
          "substrate": "基底材料 (如 'Nickel foam') or null",
          "ir_compensation": "iR补偿情况 (如 '95% compensated') or null",
          "scan_rate": "扫速 (如 '5 mV s^-1') or null"
        },
        "synthesis_method": {
          "method": "制备方法 or null",
          "key_parameters": "核心参数 or null"
        },
        "other_environmental_params": [
          { "key": "名称", "value": "内容" }
        ]
      },
      "performance": {
        "overpotential": [
          { "value": "数值", "unit": "mV", "current_density": "对应的电流密度" }
        ],
        "tafel_slope": { "value": "数值", "unit": "mV dec^-1" },
        "stability": {
          "test_method": "Chronopotentiometry / CV Cycling / Unknown",
          "duration_hours": "持续时间",
          "cycle_count": "循环圈数 or null",
          "performance_retention": "保持率",
          "degradation_details": "衰减描述"
        },
        "supplementary_performance": [
          { "key": "指标名", "value": "数值及单位" }
        ]
      }
    }
  ]
}

---
### 待处理数据：
**【合金名册 (core_alloys)】**：
$core_alloys

**【表格信息】**：
$table_info

**仅输出合法的 JSON 格式。**仅返回location、表格信息、reference_text_list中包含的合金名册中的合金ID，其他合金ID若未提及则不必返回。"""


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


def build_table_prompt(core_alloys, table_info):
    """根据 core_alloys 和 table_info 构造 table prompt"""
    # 如果 core_alloys 是字符串，先解析为 JSON
    if isinstance(core_alloys, str):
        try:
            core_alloys = json.loads(core_alloys)
        except json.JSONDecodeError:
            return None
    
    # 如果 table_info 是字符串，先解析为 JSON
    if isinstance(table_info, str):
        try:
            table_info = json.loads(table_info)
        except json.JSONDecodeError:
            return None
    
    # 如果 core_alloys 或 table_info 是 None 或空，返回 None
    if not core_alloys or not table_info:
        return None
    
    # 从 text_alloy_result 中提取 core_alloys
    if isinstance(core_alloys, dict) and "core_alloys" in core_alloys:
        core_alloys_list = core_alloys["core_alloys"]
    elif isinstance(core_alloys, list):
        core_alloys_list = core_alloys
    else:
        return None
    
    if not isinstance(core_alloys_list, list) or len(core_alloys_list) == 0:
        return None
    
    # 将 core_alloys 和 table_info 格式化为 JSON 字符串（美化格式）
    core_alloys_json = json.dumps(core_alloys_list, ensure_ascii=False, indent=2)
    table_info_json = json.dumps(table_info, ensure_ascii=False, indent=2)
    
    # 使用 Template 替换模板中的占位符（避免 JSON 中的花括号冲突）
    template = Template(PROMPT_TEMPLATE)
    prompt = template.substitute(
        core_alloys=core_alloys_json,
        table_info=table_info_json
    )
    
    return prompt


def process_table_prompts():
    """处理数据，构造 table prompt 并写入数据库"""
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
        
        # 查询需要处理的数据（从 new_table_info 表，关联 ex_info 表获取 core_alloys）
        print("查询需要处理的数据...")
        cursor.execute("""
            SELECT nti.id, nti.identifier, nti.table_info, ei.text_alloy_result
            FROM new_table_info nti
            INNER JOIN ex_info ei ON nti.identifier = ei.identifier
            WHERE nti.table_info IS NOT NULL
            AND ei.text_alloy_result IS NOT NULL
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 统计信息
        total_processed = 0
        skipped_count = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理 table prompt") as pbar:
            for record_id, identifier, table_info, text_alloy_result in records:
                try:
                    # 解析 text_alloy_result 获取 core_alloys
                    if isinstance(text_alloy_result, dict):
                        result_data = text_alloy_result
                    elif isinstance(text_alloy_result, str):
                        result_data = json.loads(text_alloy_result)
                    else:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 构造 prompt
                    table_prompt = build_table_prompt(result_data, table_info)
                    
                    if table_prompt is None:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 写入数据库
                    cursor.execute("""
                        UPDATE new_table_info 
                        SET table_prompt = %s
                        WHERE id = %s
                    """, (table_prompt, record_id))
                    
                    conn.commit()
                    total_processed += 1
                    
                except json.JSONDecodeError as e:
                    print(f"\n处理 ID {record_id} (identifier: {identifier}) 时JSON解析错误: {str(e)}")
                    skipped_count += 1
                    continue
                except Exception as e:
                    print(f"\n处理 ID {record_id} (identifier: {identifier}) 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    skipped_count += 1
                    continue
                
                pbar.update(1)
        
        print("\n" + "=" * 80)
        print("处理完成！")
        print(f"总记录数: {len(records)}")
        print(f"成功处理: {total_processed} 条")
        print(f"跳过: {skipped_count} 条")
        print("=" * 80)
        
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
    process_table_prompts()