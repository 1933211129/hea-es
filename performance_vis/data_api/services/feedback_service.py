"""
反馈服务模块
"""
from typing import Optional
from ..database import get_db_connection, get_db_cursor


def submit_feedback(identifier: str, alloy_id: str, location: str, type: str, problem: str) -> bool:
    """
    提交问题反馈
    
    Args:
        identifier: 论文标识符
        alloy_id: 合金ID
        location: 问题位置 (alloy, 实验条件, 实验性能, 其他)
        type: 错误类型 (文本, 表格, 图片)
        problem: 问题描述
    
    Returns:
        bool: 提交是否成功
    
    Raises:
        Exception: 数据库操作失败时抛出异常
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        
        # 插入反馈数据
        cursor.execute("""
            INSERT INTO public.feedback (identifier, alloy_id, location, type, problem)
            VALUES (%s, %s, %s, %s, %s)
        """, (identifier, alloy_id, location, type, problem))
        
        connection.commit()
        return True
        
    except Exception as e:
        if connection:
            connection.rollback()
        raise Exception(f"提交反馈失败: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

