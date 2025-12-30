"""
从 ex_info_text 表读取数据，构造 performance prompt，写入 performance_prompt_text 表
"""
import psycopg2
import json
from string import Template
from tqdm import tqdm
from db import get_connection_params

# Prompt 模板
PROMPT_TEMPLATE = """# Role
你是一位精通电催化尤其是析氢反应 HER的数据挖掘专家。你具备极强的逻辑推理能力，能从复杂的学术论文句子列表中，根据已知的【合金名册】提取对应的实验条件与性能指标。

# Task
请阅读提供的【句子列表】，并参照【合金名册】中的合金 ID 及其别称（aliases）、组分（composition）为每一个核心合金填充其对应的实验参数与性能数据。
**重要语境说明**：提供的 JSON 列表是全文按顺序拆分的结果。请务必将这些句子视为**连续的整体文本**，利用上下文（如代词指代、前后逻辑）来精准对齐合金、实验条件及性能指标。

# Input Data
1. **【合金名册 (core_alloys)】**：第一步识别出的实体清单。你必须严格按照此名册中的 ID 进行填充，不能脑补，不能自行扩充合金ID。
2. **【句子列表 (Text)】**：带有 ID 的论文原文（格式为 `{"id": 数字, "sentence": "内容"}`）。

# Extraction Logic
1. **实体对齐 (Entity Binding)**：
   - 必须通过 `aliases`（别称）识别文中指代。例如文中提到 "Sample II"，你必须将其对应到名册中别称为 "Sample II" 的 ID 下。
2. **全局条件继承 (Global Inheritance)**：
   - 电解液、基底、扫速等通用条件通常在论文前半部分的 Experimental 章节说明。
   - 若某合金性能段落未重复说明条件，请务必回溯全文，提取该合金所属实验组的通用设置。
3. **字段级原子溯源 (Atomic Tracing)**：
   - 每一个 `source` 字段必须包含提供该信息的句子 ID 列表。不同性能点的来源通常是不同的，请精准定位。
4. **动态口袋 (Supplementary Bags)**：
   - 若文中出现了非预定义的关键实验条件或核心性能指标，请分别放入 `other_environmental_params` 和 `supplementary_performance` 中。

# Output Schema (Strict JSON)
请输出一个 JSON 对象，其 key 为 `extraction_results`，内容为合金数据列表：
{
  "extraction_results": [
    {
      "alloy_id": "名册中的原始 ID",
      "experimental_conditions": {
        "electrolyte": {
          "electrolyte_composition": "成分 (如 'KOH') or null",
          "concentration_molar": "浓度 (如 '1.0 M') or null",
          "ph_value": "pH数值 (如 '14.0') or null",
          "source": [句子ID]
        },
        "test_setup": {
          "substrate": "基底材料 (如 'Nickel Foam') or null",
          "ir_compensation": "iR补偿情况 (如 '95%') or null",
          "scan_rate": "扫速 (如 '5 mV s^-1') or null",
          "source": [句子ID]
        },
        "synthesis_method": {
          "method": "制备方法 (如 'Pulsed electrodeposition') or null",
          "key_parameters": "核心参数 (如 '2023 K, 0.55 s') or null",
          "source": [句子ID]
        },
        "other_environmental_params": [
          { "key": "特殊条件名称", "value": "内容", "source": [句子ID] }
        ]
      },
      "performance": {
        "overpotential": [
          {
            "value": "数值",
            "unit": "mV",
            "current_density": "对应的电流密度 (如 '10 mA cm^-2')",
            "source": [句子ID]
          }
        ],
        "tafel_slope": {
          "value": "数值",
          "unit": "mV dec^-1",
          "source": [句子ID]
        },
        "stability": {
          "test_method": "Chronopotentiometry / CV Cycling / Unknown",
          "duration_hours": "持续时间 (如 '50')",
          "cycle_count": "循环圈数 or null",
          "performance_retention": "保持率 (如 '98%')",
          "degradation_details": "衰减描述 (如 '5 mV shift')",
          "source": [句子ID]
        },
        "supplementary_performance": [
          { "key": "其他指标名称", "value": "数值及单位", "source": [句子ID] }
        ]
      }
    }
  ]
}

# Constraints
- 严禁脑补数据。若文中未提及，字段填 null。
- overpotential 必须是列表，抓取文中所有提到的特征点数据。
- 确保 source ID 与输入列表中的 ID 完全一致。
- 尊重原文描述，结果整理时可以剔除latex，但不需要翻译、解释。

---
### 待处理数据：
**【合金名册 (core_alloys)】**：
$core_alloys

**【句子列表 (Text)】**：
$sentence_list

**仅输出合法的 JSON 格式，不要任何前导词或后续解释。**
"""


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


def build_performance_prompt(core_alloys, sentence_list):
    """根据 core_alloys 和 sentence_list 构造 performance prompt"""
    # 如果 core_alloys 是字符串，先解析为 JSON
    if isinstance(core_alloys, str):
        try:
            core_alloys = json.loads(core_alloys)
        except json.JSONDecodeError:
            return None
    
    # 如果 sentence_list 是字符串，先解析为 JSON
    if isinstance(sentence_list, str):
        try:
            sentence_list = json.loads(sentence_list)
        except json.JSONDecodeError:
            return None
    
    # 如果 core_alloys 或 sentence_list 是 None 或空，返回 None
    if not core_alloys or not sentence_list:
        return None
    
    # 将 core_alloys 和 sentence_list 格式化为 JSON 字符串（美化格式）
    core_alloys_json = json.dumps(core_alloys, ensure_ascii=False, indent=2)
    sentence_list_json = json.dumps(sentence_list, ensure_ascii=False, indent=2)
    
    # 使用 Template 替换模板中的占位符（避免 JSON 中的花括号冲突）
    template = Template(PROMPT_TEMPLATE)
    prompt = template.substitute(
        core_alloys=core_alloys_json,
        sentence_list=sentence_list_json
    )
    
    return prompt


def process_performance_prompts():
    """处理数据，构造 performance prompt 并写入数据库"""
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
        
        # 查询需要处理的数据（从 ex_info_text 表）
        print("查询需要处理的数据...")
        cursor.execute("""
            SELECT eit.identifier, eit.text_alloy_result, ei.sentence_list
            FROM ex_info_text eit
            INNER JOIN ex_info ei ON eit.identifier = ei.identifier
            WHERE eit.text_alloy_result IS NOT NULL
            AND ei.sentence_list IS NOT NULL
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
        with tqdm(total=len(records), desc="处理 performance prompt") as pbar:
            for identifier, text_alloy_result, sentence_list in records:
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
                    
                    # 构造 prompt
                    performance_prompt = build_performance_prompt(core_alloys, sentence_list)
                    
                    if performance_prompt is None:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 写入数据库
                    cursor.execute("""
                        INSERT INTO performance_prompt_text (identifier, performance_prompt_text)
                        VALUES (%s, %s)
                    """, (identifier, performance_prompt))
                    
                    conn.commit()
                    total_processed += 1
                    
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
    process_performance_prompts()