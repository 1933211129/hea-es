"""
合金数据密度排序服务
"""
from typing import Dict, Any, List


def calculate_data_density(alloy: Dict[str, Any]) -> int:
    """
    计算合金的数据密度分数
    
    根据以下指标计算：
    - 性能指标：overpotential, tafel_slope, stability, supplementary_performance
    - 实验条件：electrolyte, test_setup, synthesis_method, other_environmental_params
    
    Args:
        alloy: 合金数据字典
    
    Returns:
        数据密度分数（分数越高，数据越完整）
    """
    score = 0
    
    # 性能指标
    performance = alloy.get("performance", {})
    
    # overpotential: 数组，每个非空项 +2 分
    overpotential = performance.get("overpotential", [])
    if isinstance(overpotential, list):
        for op in overpotential:
            if isinstance(op, dict):
                if op.get("value") or op.get("unit"):
                    score += 2
    
    # tafel_slope: 对象，有值 +3 分
    tafel_slope = performance.get("tafel_slope")
    if tafel_slope and isinstance(tafel_slope, dict):
        if tafel_slope.get("value") or tafel_slope.get("unit"):
            score += 3
    
    # stability: 对象，每个非空字段 +1 分
    stability = performance.get("stability")
    if stability and isinstance(stability, dict):
        stability_fields = ["cycle_count", "test_method", "duration_hours", 
                          "degradation_details", "performance_retention"]
        for field in stability_fields:
            if stability.get(field) is not None:
                score += 1
    
    # supplementary_performance: 数组，每个非空项 +1 分
    supplementary = performance.get("supplementary_performance", [])
    if isinstance(supplementary, list):
        for sp in supplementary:
            if isinstance(sp, dict) and (sp.get("key") or sp.get("value")):
                score += 1
    
    # 实验条件
    experimental = alloy.get("experimental_conditions", {})
    
    # electrolyte: 对象，每个非空字段 +1 分
    electrolyte = experimental.get("electrolyte")
    if electrolyte and isinstance(electrolyte, dict):
        electrolyte_fields = ["electrolyte_composition", "concentration_molar", "ph_value"]
        for field in electrolyte_fields:
            if electrolyte.get(field) is not None:
                score += 1
    
    # test_setup: 对象，每个非空字段 +1 分
    test_setup = experimental.get("test_setup")
    if test_setup and isinstance(test_setup, dict):
        test_setup_fields = ["scan_rate", "substrate", "ir_compensation"]
        for field in test_setup_fields:
            if test_setup.get(field) is not None:
                score += 1
    
    # synthesis_method: 对象，每个非空字段 +1 分
    synthesis = experimental.get("synthesis_method")
    if synthesis and isinstance(synthesis, dict):
        synthesis_fields = ["method", "key_parameters"]
        for field in synthesis_fields:
            if synthesis.get(field) is not None:
                score += 1
    
    # other_environmental_params: 数组，每个非空项 +1 分
    other_params = experimental.get("other_environmental_params", [])
    if isinstance(other_params, list):
        for param in other_params:
            if isinstance(param, dict) and (param.get("key") or param.get("value")):
                score += 1
    
    return score


def sort_alloys_by_density(extraction_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    根据数据密度对合金进行排序（密度高的在前）
    
    Args:
        extraction_results: 合金数据列表
    
    Returns:
        排序后的合金列表
    """
    if not extraction_results or not isinstance(extraction_results, list):
        return extraction_results
    
    # 计算每个合金的密度分数并排序
    alloys_with_scores = []
    for alloy in extraction_results:
        score = calculate_data_density(alloy)
        alloys_with_scores.append((score, alloy))
    
    # 按分数降序排序（分数高的在前）
    alloys_with_scores.sort(key=lambda x: x[0], reverse=True)
    
    # 返回排序后的合金列表（不包含分数）
    return [alloy for _, alloy in alloys_with_scores]

