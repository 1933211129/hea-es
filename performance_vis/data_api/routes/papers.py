"""
论文相关 API 路由
"""
from fastapi import APIRouter, HTTPException
from typing import List

from ..models import PaperListItem, PaperDetail
from ..services.paper_service import get_all_papers, search_papers, get_paper_detail

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=List[PaperListItem])
async def get_all_papers_endpoint():
    """
    获取所有论文标题列表
    优先显示的论文会按照配置的顺序显示在前面，其他论文按 identifier 排序显示在后面
    
    Returns:
        包含 identifier 和 title 的论文列表
    """
    try:
        return get_all_papers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")


@router.get("/search", response_model=List[PaperListItem])
async def search_papers_endpoint(q: str):
    """
    搜索论文标题
    
    Args:
        q: 搜索关键词（支持任意字符检索）
    
    Returns:
        匹配的论文列表
    """
    try:
        return search_papers(q)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")


# 注意：更具体的路由要放在前面，避免被通用路由匹配
@router.get("/{identifier}/performance")
async def get_paper_performance_endpoint(identifier: str):
    """
    获取论文的整合性能数据（来自 result_merge.merge_result）
    
    Args:
        identifier: 论文标识符
    
    Returns:
        性能数据
    """
    from ..services.performance_service import get_paper_performance_data
    
    try:
        performance_data = get_paper_performance_data(identifier)
        return performance_data.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{identifier}/pdf")
async def get_paper_pdf_path(identifier: str):
    """
    获取论文的 PDF 文件路径信息
    
    Args:
        identifier: 论文标识符
    
    Returns:
        包含 PDF 文件路径信息的字典
    """
    from ..services.paper_service import get_paper_filename
    from ..config import PDF_DIR
    import os
    
    try:
        filename = get_paper_filename(identifier)
        
        if not filename:
            raise HTTPException(status_code=404, detail=f"未找到 identifier 为 {identifier} 的论文 PDF 文件")
        
        # 构建完整路径
        pdf_path = os.path.join(PDF_DIR, f"{filename}.pdf")
        
        # 检查文件是否存在
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {pdf_path}")
        
        return {
            "identifier": identifier,
            "filename": filename,
            "path": pdf_path,
            "url": f"/static_pdfs/{filename}.pdf"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 PDF 信息失败: {str(e)}")


@router.get("/{identifier}", response_model=PaperDetail)
async def get_paper_detail_endpoint(identifier: str):
    """
    获取论文详情
    
    Args:
        identifier: 论文标识符
    
    Returns:
        论文详细信息，包括标题、摘要、研究对象、研究概要和性能数据
    """
    try:
        return get_paper_detail(identifier)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")

