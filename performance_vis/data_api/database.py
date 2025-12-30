"""
数据库连接管理模块
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from .config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT


def get_db_connection():
    """
    获取数据库连接
    
    Returns:
        psycopg2.connection: 数据库连接对象
    """
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )


def get_db_cursor(connection) -> RealDictCursor:
    """
    获取数据库游标
    
    Args:
        connection: 数据库连接对象
    
    Returns:
        RealDictCursor: 游标对象
    """
    return connection.cursor(cursor_factory=RealDictCursor)


def execute_query(query: str, params: Optional[tuple] = None):
    """
    执行数据库查询（上下文管理器方式）
    
    Args:
        query: SQL 查询语句
        params: 查询参数
    
    Yields:
        cursor: 数据库游标对象
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = get_db_cursor(connection)
        cursor.execute(query, params or ())
        yield cursor
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

