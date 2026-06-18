"""数据大屏统计 API — 独立子路由，挂载到主服务 main.py"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, text

from database import ChatSession, ChatUser, SessionLocal, _to_str_time
from time_util import cst_today_str, cst_days_ago_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/statistic", tags=["数据统计"])


def _json_ok(data: Any, message: str = "查询成功") -> JSONResponse:
    return JSONResponse(status_code=200, content={"code": 200, "message": message, "data": data})


def _json_err(message: str, code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=code, content={"code": code, "message": message})


# ==================== 概览统计 ====================


@router.get("/overview")
def overview(request: Request):
    """数据大屏概览：总用户数、总会话轮次、今日会话数、今日新增用户"""
    db = SessionLocal()
    try:
        today = cst_today_str()

        total_users = db.query(func.count(ChatUser.id)).scalar() or 0
        total_sessions = db.query(func.count(ChatSession.id)).scalar() or 0

        today_sessions = (
            db.query(func.count(ChatSession.id))
            .filter(func.date(ChatSession.create_time) == today)
            .scalar()
            or 0
        )

        today_new_users = (
            db.query(func.count(ChatUser.id))
            .filter(func.date(ChatUser.create_time) == today)
            .scalar()
            or 0
        )

        return _json_ok(
            {
                "total_users": total_users,
                "total_sessions": total_sessions,
                "today_sessions": today_sessions,
                "today_new_users": today_new_users,
            }
        )
    except Exception as exc:
        logger.exception("获取概览统计失败")
        return _json_err(f"服务器错误: {exc}")
    finally:
        db.close()


# ==================== 日趋势统计 ====================


@router.get("/trends")
def trends(
    request: Request,
    days: int = Query(default=7, ge=1, le=365, description="统计最近 N 天，默认 7 天"),
):
    """每日会话量趋势"""
    db = SessionLocal()
    try:
        start_date = cst_days_ago_str(days - 1)

        rows = (
            db.query(
                func.date(ChatSession.create_time).label("date"),
                func.count(ChatSession.id).label("count"),
            )
            .filter(func.date(ChatSession.create_time) >= start_date)
            .group_by(func.date(ChatSession.create_time))
            .order_by(func.date(ChatSession.create_time).asc())
            .all()
        )

        data: list[dict[str, Any]] = []
        for row in rows:
            data.append({"date": str(row.date), "count": row.count})

        return _json_ok(data)
    except Exception as exc:
        logger.exception("获取日趋势失败")
        return _json_err(f"服务器错误: {exc}")
    finally:
        db.close()


# ==================== 活跃用户排行 ====================


@router.get("/top-users")
def top_users(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100, description="返回前 N 名，默认 10"),
    days: int = Query(default=7, ge=1, le=365, description="统计最近 N 天，默认 7 天"),
):
    """活跃用户排行（按对话轮次降序）"""
    db = SessionLocal()
    try:
        start_date = cst_days_ago_str(days - 1)

        rows = (
            db.query(
                ChatUser.username,
                ChatUser.region,
                func.count(ChatSession.id).label("message_count"),
            )
            .join(ChatSession, ChatUser.id == ChatSession.user_id)
            .filter(func.date(ChatSession.create_time) >= start_date)
            .group_by(ChatUser.id, ChatUser.username, ChatUser.region)
            .order_by(func.count(ChatSession.id).desc())
            .limit(limit)
            .all()
        )

        data: list[dict[str, Any]] = []
        for row in rows:
            data.append(
                {
                    "username": row.username,
                    "region": row.region or "Unknown",
                    "message_count": row.message_count,
                }
            )

        return _json_ok(data)
    except Exception as exc:
        logger.exception("获取活跃用户排行失败")
        return _json_err(f"服务器错误: {exc}")
    finally:
        db.close()


# ==================== 区域分布 ====================


@router.get("/region-distribution")
def region_distribution(request: Request):
    """用户区域分布统计"""
    db = SessionLocal()
    try:
        rows = (
            db.query(
                ChatUser.region,
                func.count(ChatUser.id).label("user_count"),
            )
            .filter(ChatUser.region.isnot(None), ChatUser.region != "")
            .group_by(ChatUser.region)
            .order_by(func.count(ChatUser.id).desc())
            .limit(50)
            .all()
        )

        data: list[dict[str, Any]] = []
        for row in rows:
            data.append({"region": row.region or "Unknown", "user_count": row.user_count})

        return _json_ok(data)
    except Exception as exc:
        logger.exception("获取区域分布失败")
        return _json_err(f"服务器错误: {exc}")
    finally:
        db.close()


# ==================== 内容统计 ====================


@router.get("/content-stats")
def content_stats(
    request: Request,
    days: int = Query(default=7, ge=1, le=365, description="统计最近 N 天，默认 7 天"),
):
    """内容统计：平均问答长度、总字数等"""
    db = SessionLocal()
    try:
        start_date = cst_days_ago_str(days - 1)

        stats = (
            db.query(
                func.count(ChatSession.id).label("total_rounds"),
                func.coalesce(func.avg(func.length(ChatSession.question)), 0).label("avg_question_len"),
                func.coalesce(func.avg(func.length(ChatSession.answer)), 0).label("avg_answer_len"),
                func.coalesce(func.max(func.length(ChatSession.question)), 0).label("max_question_len"),
                func.coalesce(func.max(func.length(ChatSession.answer)), 0).label("max_answer_len"),
                func.coalesce(func.sum(func.length(ChatSession.question)), 0).label("total_question_chars"),
                func.coalesce(func.sum(func.length(ChatSession.answer)), 0).label("total_answer_chars"),
            )
            .filter(func.date(ChatSession.create_time) >= start_date)
            .first()
        )

        if stats is None:
            return _json_ok({})

        return _json_ok(
            {
                "total_rounds": stats.total_rounds,
                "avg_question_len": round(float(stats.avg_question_len), 1),
                "avg_answer_len": round(float(stats.avg_answer_len), 1),
                "max_question_len": stats.max_question_len,
                "max_answer_len": stats.max_answer_len,
                "total_question_chars": stats.total_question_chars,
                "total_answer_chars": stats.total_answer_chars,
            }
        )
    except Exception as exc:
        logger.exception("获取内容统计失败")
        return _json_err(f"服务器错误: {exc}")
    finally:
        db.close()


# ==================== 按小时活跃度 ====================


@router.get("/hourly-activity")
def hourly_activity(
    request: Request,
    days: int = Query(default=7, ge=1, le=365, description="统计最近 N 天，默认 7 天"),
):
    """按小时统计活跃度（0-23 时）"""
    db = SessionLocal()
    try:
        start_date = cst_days_ago_str(days - 1)

        rows = (
            db.query(
                func.extract("hour", ChatSession.create_time).label("hour"),
                func.count(ChatSession.id).label("count"),
            )
            .filter(func.date(ChatSession.create_time) >= start_date)
            .group_by(func.extract("hour", ChatSession.create_time))
            .order_by(func.extract("hour", ChatSession.create_time).asc())
            .all()
        )

        # 补全 0-23 每个小时的数据
        hourly_map: dict[int, int] = {h: 0 for h in range(24)}
        for row in rows:
            hourly_map[int(row.hour)] = row.count

        data = [{"hour": h, "count": hourly_map[h]} for h in range(24)]
        return _json_ok(data)
    except Exception as exc:
        logger.exception("获取按小时活跃度失败")
        return _json_err(f"服务器错误: {exc}")
    finally:
        db.close()
