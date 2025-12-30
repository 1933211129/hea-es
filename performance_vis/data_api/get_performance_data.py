#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
输入：identifier
输出：对应 result_merge.merge_result 的整合性能数据
"""

import json
from typing import Any, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from .database import get_db_connection, get_db_cursor


def _ensure_parsed(data: Any) -> Optional[Dict]:
    """把 JSONB/str 转成 dict，无法解析则返回 None。"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def _fetch_merge_result(identifier: str) -> Optional[Dict]:
    """从 result_merge 表读取 merge_result"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = get_db_cursor(conn)
        cur.execute(
            """
            SELECT merge_result
            FROM public.result_merge
            WHERE identifier = %s
              AND merge_result IS NOT NULL
              AND merge_result::text != 'null'::text
            ORDER BY id DESC
            LIMIT 1
            """,
            (identifier,),
        )
        row = cur.fetchone()
        if not row or "merge_result" not in row:
            return None
        return _ensure_parsed(row["merge_result"])
    except Exception:
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_performance_data(identifier: str) -> Dict[str, Any]:
    """
    获取指定 identifier 的 merge_result 数据。
    
    返回结构:
    {
        "identifier": str,
        "merge_result": dict 或 {}
    }
    """
    merge_result = _fetch_merge_result(identifier)
    return {
        "identifier": identifier,
        "merge_result": merge_result or {},
    }

