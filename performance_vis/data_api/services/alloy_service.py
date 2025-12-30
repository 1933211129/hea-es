"""
合金详细信息相关业务逻辑服务
"""
import json
from typing import Dict, Any, Optional, List
from ..database import get_db_connection, get_db_cursor


def parse_json_field(value: Any) -> Any:
    """解析 JSON 字段"""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def get_alloy_details(identifier: str, alloy_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 identifier 和 alloy_id 获取合金详细信息
    
    Args:
        identifier: 论文标识符
        alloy_id: 合金 ID
    
    Returns:
        合金详细信息，包含 id, type, aliases, composition, precursor_id
        如果未找到则返回 None
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        
        # 查询 ex_info 表的 alloy_info 字段
        cursor.execute("""
            SELECT alloy_info
            FROM public.ex_info
            WHERE identifier = %s
              AND alloy_info IS NOT NULL
              AND alloy_info::text != 'null'::text
            ORDER BY id DESC
            LIMIT 1
        """, (identifier,))
        
        row = cursor.fetchone()
        if not row or "alloy_info" not in row:
            return None
        
        # 解析 alloy_info
        alloy_result = parse_json_field(row["alloy_info"])
        if not alloy_result or not isinstance(alloy_result, dict):
            return None
        
        # 查找匹配的合金
        core_alloys = alloy_result.get("core_alloys", [])
        if not isinstance(core_alloys, list):
            return None
        
        # 根据 alloy_id 匹配合金（匹配 id 字段，支持精确匹配和部分匹配）
        for alloy in core_alloys:
            if not isinstance(alloy, dict):
                continue
            
            alloy_id_in_data = alloy.get("id")
            # 精确匹配
            if alloy_id_in_data == alloy_id:
                return {
                    "id": alloy.get("id"),
                    "type": alloy.get("type"),
                    "aliases": alloy.get("aliases", []),
                    "composition": alloy.get("composition"),
                    "precursor_id": alloy.get("precursor_id"),
                    "evidence_source": alloy.get("evidence_source", [])
                }
            # 部分匹配：如果 alloy_id 包含在 id 中，或者 id 包含在 alloy_id 中
            if alloy_id_in_data and alloy_id:
                if alloy_id in str(alloy_id_in_data) or str(alloy_id_in_data) in alloy_id:
                    return {
                        "id": alloy.get("id"),
                        "type": alloy.get("type"),
                        "aliases": alloy.get("aliases", []),
                        "composition": alloy.get("composition"),
                        "precursor_id": alloy.get("precursor_id"),
                        "evidence_source": alloy.get("evidence_source", [])
                    }
        
        return None
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def enrich_alloys_with_details(identifier: str, extraction_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为 extraction_results 中的每个合金添加详细信息
    
    Args:
        identifier: 论文标识符
        extraction_results: 性能数据中的 extraction_results 列表
    
    Returns:
        添加了详细信息的 extraction_results 列表
    """
    if not extraction_results or not isinstance(extraction_results, list):
        return extraction_results
    
    enriched_results = []
    for alloy in extraction_results:
        alloy_id = alloy.get("alloy_id")
        if alloy_id:
            details = get_alloy_details(identifier, alloy_id)
            if details:
                alloy = alloy.copy()
                alloy["alloy_details"] = details
        enriched_results.append(alloy)
    
    return enriched_results

