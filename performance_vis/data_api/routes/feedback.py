"""
反馈相关路由
"""
from fastapi import APIRouter, HTTPException
from ..models import FeedbackRequest
from ..services.feedback_service import submit_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
async def create_feedback(feedback: FeedbackRequest):
    """
    提交问题反馈
    
    Args:
        feedback: 反馈数据
    
    Returns:
        包含成功信息的字典
    
    Raises:
        HTTPException: 提交失败时抛出异常
    """
    try:
        success = submit_feedback(
            identifier=feedback.identifier,
            alloy_id=feedback.alloy_id,
            location=feedback.location,
            type=feedback.type,
            problem=feedback.problem
        )
        
        if success:
            return {
                "success": True,
                "message": "反馈提交成功"
            }
        else:
            raise HTTPException(status_code=500, detail="提交反馈失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")

