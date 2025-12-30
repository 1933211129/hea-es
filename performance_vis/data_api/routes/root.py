"""
根路径 API 路由
"""
from fastapi import APIRouter

from ..models import APIInfo
from ..config import API_VERSION

router = APIRouter(tags=["root"])


@router.get("/", response_model=APIInfo)
async def root():
    """根路径，返回 API 信息"""
    return APIInfo(
        message="HEA 论文性能数据 API",
        version=API_VERSION,
        endpoints={
            "GET /papers": "获取所有论文标题列表",
            "GET /papers/{identifier}": "获取论文详情",
            "GET /papers/search?q={query}": "搜索论文标题",
            "GET /papers/{identifier}/performance": "获取论文多源整合的性能数据（文本/表格/图片）"
        }
    )

