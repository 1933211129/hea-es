"""
Pydantic 模型定义
"""
from pydantic import BaseModel
from typing import Optional, Any, Dict, List


class PaperListItem(BaseModel):
    """论文列表项"""
    identifier: str
    title: str


class PaperDetail(BaseModel):
    """论文详情"""
    identifier: str
    title: str
    abstract: Optional[Any]  # 可能是字符串或 JSON 对象
    alloy_elements: Optional[Any]  # 可能是字符串或 JSON 对象（如 {'elements': [...]}）
    topic: Optional[Any]  # 可能是字符串或 JSON 对象
    performance: Dict[str, Any]


class PerformanceData(BaseModel):
    """性能数据"""
    identifier: str
    merge_result: Dict[str, Any]


class APIInfo(BaseModel):
    """API 信息"""
    message: str
    version: str
    endpoints: Dict[str, str]


class FeedbackRequest(BaseModel):
    """问题反馈请求"""
    identifier: str
    alloy_id: str
    location: str  # alloy, 实验条件, 实验性能, 其他
    type: str  # 文本, 表格, 图片
    problem: str

