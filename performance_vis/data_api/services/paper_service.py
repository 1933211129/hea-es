"""
论文相关业务逻辑服务
"""
import json
from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor  # type: ignore

from ..database import get_db_connection, get_db_cursor
from ..config import PRIORITY_IDENTIFIERS
from ..models import PaperListItem, PaperDetail


def parse_json_field(value: Any) -> Any:
    """
    解析 JSON 字段，支持字符串和字典格式
    
    Args:
        value: 待解析的值
    
    Returns:
        解析后的值（字典、字符串或 None）
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value  # 如果解析失败，返回原始字符串
    return value


def get_all_papers() -> List[PaperListItem]:
    """
    获取所有论文标题列表
    优先显示的论文会按照配置的顺序显示在前面，其他论文按 identifier 排序显示在后面
    
    Returns:
        包含 identifier 和 title 的论文列表
    
    Raises:
        Exception: 数据库查询失败时抛出异常
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        
        # 查询所有论文的 identifier 和 title
        cursor.execute("""
            SELECT identifier, title
            FROM public.paper_info
        """)
        
        results = cursor.fetchall()
        
        # 转换为字典列表
        all_papers = [
            {
                "identifier": row["identifier"],
                "title": row["title"] if row["title"] else ""
            }
            for row in results
        ]
        
        # 创建 identifier 到论文的映射
        paper_dict = {paper["identifier"]: paper for paper in all_papers}
        
        # 按照优先级顺序提取优先显示的论文
        priority_papers = []
        for identifier in PRIORITY_IDENTIFIERS:
            if identifier in paper_dict:
                priority_papers.append(paper_dict[identifier])
        
        # 提取其他论文（不在优先级列表中的）
        other_papers = [
            paper for paper in all_papers
            if paper["identifier"] not in PRIORITY_IDENTIFIERS
        ]
        # 其他论文按 identifier 排序
        other_papers.sort(key=lambda x: x["identifier"])
        
        # 合并：优先显示的在前，其他的在后
        papers = priority_papers + other_papers
        
        return [PaperListItem(**paper) for paper in papers]
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def search_papers(query: str) -> List[PaperListItem]:
    """
    搜索论文标题
    
    Args:
        query: 搜索关键词（支持任意字符检索）
    
    Returns:
        匹配的论文列表
    
    Raises:
        ValueError: 搜索关键词为空时抛出异常
        Exception: 数据库查询失败时抛出异常
    """
    if not query or not query.strip():
        raise ValueError("搜索关键词不能为空")
    
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        
        # 使用 ILIKE 进行不区分大小写的模糊匹配
        search_pattern = f"%{query.strip()}%"
        cursor.execute("""
            SELECT identifier, title
            FROM public.paper_info
            WHERE title ILIKE %s
            ORDER BY identifier
        """, (search_pattern,))
        
        results = cursor.fetchall()
        
        # 转换为字典列表
        papers = [
            {
                "identifier": row["identifier"],
                "title": row["title"] if row["title"] else ""
            }
            for row in results
        ]
        
        return [PaperListItem(**paper) for paper in papers]
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_paper_detail(identifier: str) -> PaperDetail:
    """
    获取论文详情
    
    Args:
        identifier: 论文标识符
    
    Returns:
        论文详细信息，包括标题、摘要、研究对象、研究概要和性能数据
    
    Raises:
        ValueError: 未找到论文时抛出异常
        Exception: 数据库查询失败时抛出异常
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        
        # 查询论文基本信息
        cursor.execute("""
            SELECT identifier, title, abstract, alloy_elements, topic
            FROM public.paper_info
            WHERE identifier = %s
        """, (identifier,))
        
        paper_info = cursor.fetchone()
        
        if not paper_info:
            raise ValueError(f"未找到 identifier 为 {identifier} 的论文")
        
        # 查询性能数据：使用 result_merge.merge_result
        cursor.execute("""
            SELECT merge_result
            FROM public.result_merge
            WHERE identifier = %s
              AND merge_result IS NOT NULL
              AND merge_result::text != 'null'::text
            ORDER BY id DESC
            LIMIT 1
        """, (identifier,))
        
        performance_row = cursor.fetchone()
        performance = performance_row["merge_result"] if performance_row and "merge_result" in performance_row else None
        
        # 构建返回结果（performance 使用 merge_result）
        result = {
            "identifier": paper_info["identifier"],
            "title": paper_info["title"] if paper_info["title"] else "",
            "abstract": parse_json_field(paper_info.get("abstract")),
            "alloy_elements": parse_json_field(paper_info.get("alloy_elements")),
            "topic": parse_json_field(paper_info.get("topic")),
            "performance": parse_json_field(performance) if performance is not None else {}
        }
        
        return PaperDetail(**result)
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_paper_filename(identifier: str) -> Optional[str]:
    """
    获取论文的 PDF 文件名
    
    Args:
        identifier: 论文标识符
    
    Returns:
        PDF 文件名（不含路径），如果未找到则返回 None
    
    Raises:
        Exception: 数据库查询失败时抛出异常
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        
        # 查询 ex_info 表中的 filename
        cursor.execute("""
            SELECT filename
            FROM public.ex_info
            WHERE identifier = %s
            ORDER BY id DESC
            LIMIT 1
        """, (identifier,))
        
        row = cursor.fetchone()
        
        if row and row.get("filename"):
            return row["filename"]
        
        return None
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

