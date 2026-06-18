"""时区工具模块：集中管理东八区 (Asia/Shanghai) 时间

所有数据库时间戳统一使用东八区（UTC+8），本模块提供一致的时间获取与格式化函数，
不依赖操作系统时区设置，确保 Python 端与 PostgreSQL 端时间基准一致。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# 东八区固定偏移 +08:00
CST = timezone(timedelta(hours=8), "Asia/Shanghai")


def cst_now() -> datetime:
    """返回当前 CST 时间（naive datetime，与 DB DateTime(timezone=False) 一致）"""
    return datetime.now(CST).replace(tzinfo=None)


def cst_today_str() -> str:
    """返回今天的 CST 日期字符串，格式 YYYY-MM-DD"""
    return datetime.now(CST).strftime("%Y-%m-%d")


def cst_days_ago_str(days: int) -> str:
    """返回 N 天前的 CST 日期字符串，格式 YYYY-MM-DD"""
    return (datetime.now(CST) - timedelta(days=days)).strftime("%Y-%m-%d")


def cst_time_str() -> str:
    """返回当前 CST 时间的 HH:MM:SS"""
    return datetime.now(CST).strftime("%H:%M:%S")


def to_str_time(value: Any) -> str:
    """统一格式化时间为 YYYY-MM-DD HH:MM:SS（CST 时间）

    兼容 naive 和 aware datetime：
    - naive datetime 直接格式化
    - aware datetime 先转换为 CST 再格式化
    """
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(CST)
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)
