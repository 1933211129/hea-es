"""
性能数据相关业务逻辑服务
"""
from ..get_performance_data import get_performance_data
from ..models import PerformanceData
from .alloy_service import enrich_alloys_with_details
from .alloy_sorting import sort_alloys_by_density


def get_paper_performance_data(identifier: str) -> PerformanceData:
    """
    获取论文的整合性能数据（来自 result_merge.merge_result）
    并添加合金详细信息，按数据密度排序
    
    Args:
        identifier: 论文标识符
    
    Returns:
        性能数据对象（包含合金详细信息，按数据密度排序）
    
    Raises:
        Exception: 获取性能数据失败时抛出异常
    """
    try:
        performance_data = get_performance_data(identifier)
        merge_result = performance_data.get("merge_result", {})
        
        # 为 extraction_results 中的每个合金添加详细信息
        if "extraction_results" in merge_result:
            enriched_results = enrich_alloys_with_details(
                identifier,
                merge_result["extraction_results"]
            )
            # 按数据密度排序（密度高的在前）
            merge_result["extraction_results"] = sort_alloys_by_density(enriched_results)
        
        return PerformanceData(**performance_data)
    except Exception as e:
        raise Exception(f"获取性能数据失败: {str(e)}")

