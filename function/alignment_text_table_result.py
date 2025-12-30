"""
文本-表格结果仲裁：调用 LLM 对 text 和 table 数据进行仲裁，生成最终结果
"""
import json
import re
import time
import ast
import requests
from typing import List, Optional
from pydantic import BaseModel, Field
from config import (
    CHATANYWHERE_API_KEY,
    CHATANYWHERE_API_URL,
    CHATANYWHERE_MODEL,
    MAX_RETRIES,
    MAX_TOKENS,
    TEMPERATURE
)


# Prompt 模板
prompt = """
# Role
你是一位精通电催化研究（HER/ORR）的高级数据仲裁专家。你具备极强的数据辨析能力，能对比"文本提取结果"与"表格提取结果"，依据原始证据链产出该合金最精确、最完整的数据记录。

# Task
请针对目标合金【alloy_id】，对比【Text Data】与【Table Data】两个来源的信息。根据提供的原始证据（source/source_content/reference_text），进行数据对齐、去重、冲突校准及互补合并，生成最终的唯一 JSON。

# Input Data
- **【Alloy ID】**: {alloy_id}
- **【Text Data】**: 基于论文正文提取的 JSON 结果，包含原始句子证据。
- **【Table Data】**: 基于论文表格提取的 JSON 结果，包含 HTML 原文、标题及引用文本。

# Arbitration Logic (仲裁原则)
1. **数值精度优先 (Precision First)**：
   - 若文本结果与表格结果描述同一指标但数值精度不同（如 28 vs 28.04），**必须保留高精度数值**。
2. **描述细节互补 (Detail Complementarity)**：
   - 文本往往包含更多细节（如 synthesis_method 的具体步骤、稳定性测试的具体循环范围）。
   - 表格往往包含更整齐的物理常数（如 Φ, Tm, △Hmix 等）。
   - **操作**：将两者的非空字段取并集。若文本有细节而表格为 null，保留文本细节。
3. **环境对齐确认**：
   - 检查【Text Data】和【Table Data】的实验条件（electrolyte, test_setup）。若一致，则合并性能指标；若不一致（极少见），请优先保留该合金核心性能所在的那个环境。
4. **清理与去重**：
   - 移除所有原始数据中的 "source" 标签。
   - 确保 `overpotential` 列表中没有重复的电流密度点。
   - 确保 `supplementary_performance` 列表中的 key 不重复。

# Constraints
- **严禁虚构**：若两方均为 null，则结果为 null。
- **原文保留**：对于文本描述（如制备方法、衰减细节），保持 verbatim（原文）提取，剔除冗余的 latex 格式，但保持专业术语准确,不需要翻译成中文，尊重原文。
- **仅输出 JSON**：不要任何前导说明或术语解释。

# Output Schema (Strict JSON)
{{
  "extraction_results": [
    {{
      "alloy_id": "Raw ID",
      "experimental_conditions": {{
        "electrolyte": {{
          "electrolyte_composition": "Electrolyte composition (e.g., 'KOH') or null",
          "concentration_molar": "Concentration (e.g., '1.0 M') or null",
          "ph_value": "pH value (e.g., '14.0') or null"
        }},
        "test_setup": {{
          "substrate": "Substrate material (e.g., 'Nickel Foam') or null",
          "ir_compensation": "iR compensation (e.g., '95%') or null",
          "scan_rate": "Scan rate (e.g., '5 mV s^-1') or null"
        }},
        "synthesis_method": {{
          "method": "Synthesis method (e.g., 'Pulsed electrodeposition') or null",
          "key_parameters": "Key parameters (e.g., '2023 K, 0.55 s') or null"
        }},
        "other_environmental_params": [
          {{ "key": "Special condition name", "value": "Content" }}
        ]
      }},
      "performance": {{
        "overpotential": [
          {{
            "value": "Value",
            "unit": "mV",
            "current_density": "Associated current density (e.g., '10 mA cm^-2')",
          }}
        ],
        "tafel_slope": {{
          "value": "Value",
          "unit": "mV dec^-1",
        }},
        "stability": {{
          "test_method": "Chronopotentiometry / CV Cycling / Unknown",
          "duration_hours": "Duration (e.g., '50')",
          "cycle_count": "Cycle number or null",
          "performance_retention": "Retention (e.g., '98%')",
          "degradation_details": "Degradation description (e.g., '5 mV shift')",
        }},
        "supplementary_performance": [
          {{ "key": "Other performance metric", "value": "Value and unit" }}
        ]
      }}
    }}
  ]
}}

---
### 待仲裁原始数据：
{input_data}
"""


# Pydantic 模型定义
class OverpotentialItem(BaseModel):
    """过电位项"""
    value: Optional[str] = None
    unit: str = "mV"
    current_density: Optional[str] = None


class TafelSlope(BaseModel):
    """Tafel 斜率"""
    value: Optional[str] = None
    unit: str = "mV dec^-1"


class Stability(BaseModel):
    """稳定性数据"""
    test_method: Optional[str] = None
    duration_hours: Optional[str] = None
    cycle_count: Optional[int] = None
    performance_retention: Optional[str] = None
    degradation_details: Optional[str] = None


class SupplementaryPerformanceItem(BaseModel):
    """补充性能指标"""
    key: str
    value: str


class Performance(BaseModel):
    """性能数据"""
    overpotential: List[OverpotentialItem] = Field(default_factory=list)
    tafel_slope: TafelSlope = Field(default_factory=TafelSlope)
    stability: Stability = Field(default_factory=Stability)
    supplementary_performance: List[SupplementaryPerformanceItem] = Field(default_factory=list)


class Electrolyte(BaseModel):
    """电解液"""
    electrolyte_composition: Optional[str] = None
    concentration_molar: Optional[str] = None
    ph_value: Optional[str] = None


class TestSetup(BaseModel):
    """测试设置"""
    substrate: Optional[str] = None
    ir_compensation: Optional[str] = None
    scan_rate: Optional[str] = None


class SynthesisMethod(BaseModel):
    """合成方法"""
    method: Optional[str] = None
    key_parameters: Optional[str] = None


class OtherEnvironmentalParam(BaseModel):
    """其他环境参数"""
    key: str
    value: str


class ExperimentalConditions(BaseModel):
    """实验条件"""
    electrolyte: Electrolyte = Field(default_factory=Electrolyte)
    test_setup: TestSetup = Field(default_factory=TestSetup)
    synthesis_method: SynthesisMethod = Field(default_factory=SynthesisMethod)
    other_environmental_params: List[OtherEnvironmentalParam] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """提取结果项"""
    alloy_id: str
    experimental_conditions: ExperimentalConditions = Field(default_factory=ExperimentalConditions)
    performance: Performance = Field(default_factory=Performance)


class ArbitrationResult(BaseModel):
    """仲裁结果"""
    extraction_results: List[ExtractionResult] = Field(default_factory=list)


def load_input_data(file_path: str) -> dict:
    """从文件加载输入数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        # 使用 ast.literal_eval 安全地解析 Python dict
        return ast.literal_eval(content)


def build_prompt(input_data: dict) -> str:
    """构造 prompt"""
    alloy_id = input_data.get('alloy_id', '')
    input_data_json = json.dumps(input_data, ensure_ascii=False, indent=2)
    
    return prompt.format(
        alloy_id=alloy_id,
        input_data=input_data_json
    )


def extract_json_from_text(text: str) -> Optional[str]:
    """从文本中提取JSON内容，去除可能的markdown代码块标记"""
    # 移除可能的markdown代码块标记
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # 尝试直接解析
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 对象
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            json_str = json_match.group(0)
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
    
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


def validate_result(response_text: str) -> Optional[ArbitrationResult]:
    """使用 Pydantic 验证返回结果"""
    try:
        # 提取 JSON
        json_str = extract_json_from_text(response_text)
        if not json_str:
            return None
        
        # 解析 JSON
        data = json.loads(json_str)
        
        # 使用 Pydantic 验证
        result = ArbitrationResult(**data)
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        return None
    except Exception as e:
        print(f"Pydantic验证错误: {str(e)}")
        return None


def get_table_source(input_data: dict) -> dict:
    """
    从输入数据中提取 table 的完整 source
    返回完整的 source 对象，包含 location、source_content、reference_text_list
    """
    source_obj = input_data.get('table', {}).get('source', {})
    return source_obj if isinstance(source_obj, dict) else {}


def extract_text_source(text_data: dict, path: list) -> list:
    """
    从 text 数据中提取指定路径的 source
    path: 例如 ['experimental_conditions', 'electrolyte', 'source']
    """
    current = text_data
    for key in path[:-1]:
        if not isinstance(current, dict):
            return []
        current = current.get(key, {})
    
    source = current.get(path[-1], []) if isinstance(current, dict) else []
    return source if isinstance(source, list) else []


def is_field_all_null(field_value) -> bool:
    """判断字段是否全部为 null"""
    if field_value is None:
        return True
    if isinstance(field_value, dict):
        # 检查字典中所有值是否都为 None（排除 source 字段）
        for key, value in field_value.items():
            if key != 'source' and value is not None:
                return False
        return True
    if isinstance(field_value, list):
        if len(field_value) == 0:
            return True
        # 检查列表中所有项是否都为 None
        for item in field_value:
            if not is_field_all_null(item):
                return False
        return True
    return False


def normalize_value(value) -> str:
    """
    标准化值用于比较（去除空格、转换为小写等）
    """
    if value is None:
        return ""
    if isinstance(value, str):
        # 去除前后空格，转换为小写，去除多余的空白字符
        return " ".join(value.lower().split())
    return str(value).lower().strip()


def _deduplicate_list(items: list) -> list:
    """去重列表，保持顺序"""
    seen = set()
    return [item for item in items if item not in seen and not seen.add(item)]


def values_match(val1, val2) -> bool:
    """
    判断两个值是否匹配（用于判断来源）
    """
    if val1 is None and val2 is None:
        return True
    if val1 is None or val2 is None:
        return False
    
    # 标准化后比较
    norm1 = normalize_value(val1)
    norm2 = normalize_value(val2)
    
    # 完全匹配
    if norm1 == norm2:
        return True
    
    # 对于数值，尝试解析后比较
    try:
        if abs(float(val1) - float(val2)) < 0.01:
            return True
    except (ValueError, TypeError):
        pass
    
    # 对于字符串，检查是否包含（部分匹配）
    if isinstance(val1, str) and isinstance(val2, str):
        if norm1 in norm2 or norm2 in norm1:
            return True
    
    return False


def check_field_source(result_field: dict, text_field: dict, table_field: dict, text_source: list, table_reference_list: list, table_source_obj: dict):
    """
    检查字段的数据来源，根据 LLM 返回的值与原始输入比较
    
    参数:
        result_field: LLM 返回的字段值（字典）
        text_field: 文本中的原始字段值（字典）
        table_field: 表格中的原始字段值（字典）
        text_source: 文本的 source 列表
        table_reference_list: 表格的 reference_text_list
        table_source_obj: 完整的表格 source 对象
    
    返回:
        - 如果只来自 text：返回列表格式 [source1, source2, ...]
        - 如果来自 table：返回字典格式 {"reference_text_list": [...], "table_source": {...}}
        - 如果为空：返回 None
    """
    if not isinstance(result_field, dict) or not result_field:
        return None
    
    from_text = False
    from_table = False
    
    # 检查 result_field 中的每个非空值是否匹配 text 或 table
    for key, result_val in result_field.items():
        if result_val is None or key == 'source':
            continue
        
        text_val = text_field.get(key) if isinstance(text_field, dict) else None
        table_val = table_field.get(key) if isinstance(table_field, dict) else None
        
        # 判断是否来自 text
        if text_val is not None and values_match(result_val, text_val):
            from_text = True
        
        # 判断是否来自 table
        if table_val is not None and values_match(result_val, table_val):
            from_table = True
    
    # 如果都不匹配，检查是否有任何非空值
    if not from_text and not from_table:
        # 如果 text_field 有非空值，可能来自 text
        if isinstance(text_field, dict):
            for val in text_field.values():
                if val is not None and val != []:
                    from_text = bool(text_source)
                    break
        # 如果 table_field 有非空值，可能来自 table
        if isinstance(table_field, dict):
            for val in table_field.values():
                if val is not None and val != []:
                    from_table = bool(table_reference_list)
                    break
    
    # 构造 source
    # 如果只来自 text（不来自 table），直接返回列表格式
    if from_text and not from_table:
        if text_source:
            unique_source = _deduplicate_list(text_source)
            return unique_source if unique_source else None
        return None
    
    # 如果来自 table（无论是否同时来自 text），都必须返回包含 table_source 的字典格式
    if from_table:
        source_dict = {}
        
        # 合并 reference_text_list（如果同时来自 text 和 table）
        reference_text_list = []
        if from_text and text_source:
            reference_text_list.extend(text_source)
        if table_reference_list:
            reference_text_list.extend(table_reference_list)
        
        unique_source = _deduplicate_list(reference_text_list)
        
        # 如果同时来自 text 和 table，添加合并后的 reference_text_list
        if from_text and unique_source:
            source_dict["reference_text_list"] = unique_source
        
        # 始终添加完整的 table source 信息（因为值来自表格）
        if table_source_obj:
            table_source_copy = table_source_obj.copy()
            source_dict["table_source"] = table_source_copy
        
        # 如果 source_dict 不为空，返回
        if source_dict:
            return source_dict
        
        # 如果只来自 table 但没有 table_source_obj，返回空字典（至少表明来自表格）
        return {}
    
    return None


def _find_matching_item(items: list, match_key: str, match_value: str) -> Optional[dict]:
    """在列表中查找匹配的项"""
    for item in items:
        if isinstance(item, dict) and item.get(match_key) == match_value:
            return item
    return None


def _add_source_to_field(result_field: dict, text_field: dict, table_field: dict, 
                         text_source: list, table_reference_list: list, 
                         table_source_obj: dict) -> None:
    """为单个字段添加 source"""
    if not is_field_all_null(result_field):
        source_dict = check_field_source(result_field, text_field, table_field, 
                                        text_source, table_reference_list, table_source_obj)
        if source_dict:
            result_field['source'] = source_dict


def add_source_to_result(result_dict: dict, input_data: dict) -> dict:
    """
    为结果添加 source 字段
    从原始输入数据中提取 source 并合并
    """
    text_data = input_data.get('text', {})
    table_data = input_data.get('table', {})
    table_source_obj = get_table_source(input_data)
    
    # 从 table_source_obj 中提取 reference_text_list 用于合并
    table_reference_list = []
    if isinstance(table_source_obj, dict):
        ref_list = table_source_obj.get('reference_text_list', [])
        if isinstance(ref_list, list):
            table_reference_list = [item for item in ref_list if item]
    
    # 调试信息：打印提取的 table_source
    print(f"  提取的 table_source: {len(table_reference_list)} 项 reference_text_list")
    if table_source_obj:
        print(f"    location: {table_source_obj.get('location', 'N/A')[:50]}...")
    
    extraction_results = result_dict.get('extraction_results', [])
    if not extraction_results:
        return result_dict
    
    # 处理每个 extraction_result
    for result_item in extraction_results:
        exp_cond = result_item.get('experimental_conditions', {})
        performance = result_item.get('performance', {})
        text_exp_cond = text_data.get('experimental_conditions', {})
        table_exp_cond = table_data.get('experimental_conditions', {})
        
        # 1-3. experimental_conditions 下的简单字段
        for field_name in ['electrolyte', 'test_setup', 'synthesis_method']:
            result_field = exp_cond.get(field_name, {})
            text_field = text_exp_cond.get(field_name, {})
            table_field = table_exp_cond.get(field_name, {})
            text_source = extract_text_source(text_data, ['experimental_conditions', field_name, 'source'])
            _add_source_to_field(result_field, text_field, table_field, 
                               text_source, table_reference_list, table_source_obj)
        
        # 4. experimental_conditions.other_environmental_params[].source
        other_params = exp_cond.get('other_environmental_params', [])
        if other_params:
            text_other_params = text_exp_cond.get('other_environmental_params', [])
            table_other_params = table_exp_cond.get('other_environmental_params', [])
            for param in other_params:
                param_key = param.get('key', '')
                text_param = _find_matching_item(text_other_params, 'key', param_key)
                table_param = _find_matching_item(table_other_params, 'key', param_key)
                text_source = text_param.get('source', []) if text_param else []
                if not isinstance(text_source, list):
                    text_source = []
                _add_source_to_field(param, text_param or {}, table_param or {}, 
                                   text_source, table_reference_list, table_source_obj)
        
        # 5. performance.overpotential[].source
        overpotential = performance.get('overpotential', [])
        if overpotential:
            text_overpotential = text_data.get('performance', {}).get('overpotential', [])
            table_overpotential = table_data.get('performance', {}).get('overpotential', [])
            for overpot_item in overpotential:
                current_density = overpot_item.get('current_density', '')
                text_overpot_item = _find_matching_item(text_overpotential, 'current_density', current_density)
                table_overpot_item = _find_matching_item(table_overpotential, 'current_density', current_density)
                text_source = text_overpot_item.get('source', []) if text_overpot_item else []
                if not isinstance(text_source, list):
                    text_source = []
                _add_source_to_field(overpot_item, text_overpot_item or {}, table_overpot_item or {}, 
                                   text_source, table_reference_list, table_source_obj)
        
        # 6. performance.tafel_slope
        tafel_slope = performance.get('tafel_slope', {})
        if isinstance(tafel_slope, dict):
            if tafel_slope.get('value') is None:
                performance['tafel_slope'] = None
            else:
                text_tafel = text_data.get('performance', {}).get('tafel_slope', {})
                table_tafel = table_data.get('performance', {}).get('tafel_slope', {})
                text_source = extract_text_source(text_data, ['performance', 'tafel_slope', 'source'])
                _add_source_to_field(tafel_slope, text_tafel, table_tafel, 
                                    text_source, table_reference_list, table_source_obj)
        
        # 7. performance.stability.source
        stability = performance.get('stability', {})
        text_stability = text_data.get('performance', {}).get('stability', {})
        table_stability = table_data.get('performance', {}).get('stability', {})
        text_source = extract_text_source(text_data, ['performance', 'stability', 'source'])
        _add_source_to_field(stability, text_stability, table_stability, 
                           text_source, table_reference_list, table_source_obj)
        
        # 8. performance.supplementary_performance[].source
        supp_perf = performance.get('supplementary_performance', [])
        if supp_perf:
            text_supp_perf = text_data.get('performance', {}).get('supplementary_performance', [])
            table_supp_perf = table_data.get('performance', {}).get('supplementary_performance', [])
            for supp_item in supp_perf:
                supp_key = supp_item.get('key', '')
                text_supp_item = _find_matching_item(text_supp_perf, 'key', supp_key)
                table_supp_item = _find_matching_item(table_supp_perf, 'key', supp_key)
                text_source = text_supp_item.get('source', []) if text_supp_item else []
                if not isinstance(text_source, list):
                    text_source = []
                _add_source_to_field(supp_item, text_supp_item or {}, table_supp_item or {}, 
                                    text_source, table_reference_list, table_source_obj)
    
    return result_dict


def get_llm_result_with_retry(prompt: str) -> Optional[ArbitrationResult]:
    """调用大模型并重试，直到获得有效结果或超过最大重试次数"""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  尝试 {attempt + 1}/{MAX_RETRIES}...")
            
            # 调用API
            response_text = call_llm_api(prompt)
            if not response_text:
                print(f"  API返回为空")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)  # 等待2秒后重试
                continue
            
            # 验证结果
            validated_result = validate_result(response_text)
            if validated_result:
                print(f"  ✓ 验证通过")
                return validated_result
            else:
                print(f"  结果验证失败")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)  # 等待2秒后重试
                continue
                
        except Exception as e:
            print(f"  发生异常 - {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            continue
    
    # 所有重试都失败
    print(f"  超过最大重试次数 ({MAX_RETRIES})，处理失败")
    return None


def main():
    """主函数"""
    # 1. 加载输入数据
    print("加载输入数据...")
    input_data = load_input_data("input_test.txt")
    print(f"✓ 输入数据加载成功\n")
    
    # 2. 构造 prompt
    print("构造 prompt...")
    full_prompt = build_prompt(input_data)
    # 把 full_prompt 写入文件
    with open("full_prompt.txt", "w", encoding="utf-8") as f:
        f.write(full_prompt)
    print(f"✓ Prompt 构造完成\n")
    
    # 3. 调用 LLM
    print("调用 LLM API...")
    result = get_llm_result_with_retry(full_prompt)
    
    if result is None:
        print("\n❌ 处理失败，无法获得有效结果")
        return
    
    # 4. 添加 source 字段
    print("\n添加 source 字段...")
    result_dict = result.model_dump()
    result_dict_with_source = add_source_to_result(result_dict, input_data)
    print(f"✓ Source 字段添加完成\n")
    
    # 5. 保存结果到 JSON 文件
    print("保存结果到 JSON 文件...")
    output_file = "arbitration_result.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict_with_source, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 结果已保存到: {output_file}")
    print(f"\n提取结果数量: {len(result.extraction_results)}")
    if result.extraction_results:
        print(f"第一个合金 ID: {result.extraction_results[0].alloy_id}")


if __name__ == "__main__":
    main()

