"""数据大屏模块 — WebSocket 推送 + 告警接收 + 统计API + 页面托管

独立于 Vue 前端的纯 HTML 大屏页面，使用 ECharts 渲染中国地图 IP 分布 + 词云图。
通过 WebSocket 实时接收前端人工介入告警并弹出 Toast 通知。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import Counter
from typing import Any

import jieba
from sqlalchemy import func
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse

from database import ChatUser, ChatSession, SessionLocal, extract_client_ip, lookup_geo
from email_sender import send_alert_email
from time_util import cst_today_str, cst_days_ago_str, cst_time_str

logger = logging.getLogger(__name__)

router = APIRouter(tags=["数据大屏"])

# ==================== WebSocket 连接管理 ====================

class ConnectionManager:
    """管理所有连接的大屏客户端"""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("Dashboard client connected (total: %d)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
            logger.info("Dashboard client disconnected (total: %d)", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """向所有连接的大屏客户端推送 JSON 消息"""
        payload = json.dumps(message, ensure_ascii=False)
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


manager = ConnectionManager()

# ==================== 静态页面托管 ====================

DASHBOARD_HTML_PATH = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")


GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "static", "china.json")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page() -> HTMLResponse:
    """返回数据大屏 HTML 页面，内联中国地图 GeoJSON 数据（无需外部请求）"""
    if os.path.exists(DASHBOARD_HTML_PATH):
        with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        # 读取中国地图 GeoJSON 并内联到 HTML 中
        geojson_script = ""
        if os.path.exists(GEOJSON_PATH):
            with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
                geojson_data = f.read()
            geojson_script = f"<script>window.__CHINA_GEOJSON__ = {geojson_data};</script>"
        content = content.replace("<!-- GEOJSON_PLACEHOLDER -->", geojson_script)
    else:
        content = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>数据大屏</title></head>
<body><h1>数据大屏页面未找到</h1><p>请确认 static/dashboard.html 已部署。</p></body>
</html>"""
    return HTMLResponse(content=content)


# ==================== WebSocket 端点 ====================


@router.websocket("/ws/dashboard")
async def dashboard_websocket(ws: WebSocket) -> None:
    """数据大屏 WebSocket 实时通道"""
    await manager.connect(ws)
    try:
        while True:
            # 保持连接，接收客户端心跳
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(ws)


# ==================== 告警接收端点 ====================


@router.post("/api/alert/teacher")
async def receive_alert(request: Request) -> JSONResponse:
    """接收前端人工介入告警，通过 WebSocket 推送到数据大屏

    Body 格式（来自前端 sendAlertToTeacher）:
    {
        "studentName": "用户名",
        "contact": "手机号",
        "sessionId": "会话ID",
        "intentType": "high_intent | urgent",
        "messageSnippet": "触发关键词的消息片段"
    }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    contact = str(body.get("contact") or body.get("phone") or "").strip()
    student_name = str(body.get("studentName") or "").strip()
    intent_type = str(body.get("intentType") or "high_intent").strip()
    message_snippet = str(body.get("messageSnippet") or "").strip()
    session_id = str(body.get("sessionId") or "").strip()

    if not contact:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "缺少联系方式 (contact/phone)"},
        )

    alert_time = cst_time_str()

    # 提取客户端 IP 并查询归属地
    client_ip = extract_client_ip(request)
    geo = lookup_geo(client_ip)

    # 推送到所有大屏客户端（保持现有逻辑不变）
    await manager.broadcast(
        {
            "type": "alert",
            "data": {
                "contact": contact,
                "studentName": student_name,
                "intentType": intent_type,
                "messageSnippet": message_snippet,
                "sessionId": session_id,
                "time": alert_time,
            },
        }
    )

    # 异步发送告警邮件（不阻塞响应）
    email_data = {
        "contact": contact,
        "student_name": student_name,
        "client_ip": geo.ip,
        "region": geo.region,
        "country_name": geo.country_name,
        "intent_type": intent_type,
        "message_snippet": message_snippet,
        "session_id": session_id,
        "alert_time": alert_time,
    }
    asyncio.create_task(send_alert_email(email_data))

    logger.info(
        "收到人工介入告警: contact=%s, type=%s, student=%s, ip=%s, country=%s, region=%s",
        contact,
        intent_type,
        student_name,
        geo.ip,
        geo.country_name,
        geo.region,
    )

    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "告警已推送到数据大屏",
            "data": {
                "contact": contact,
                "time": alert_time,
            },
        },
    )


# ==================== 数据 API ====================


@router.get("/api/dashboard/ip-distribution")
def ip_distribution(request: Request) -> JSONResponse:
    """获取用户 IP 归属地分布数据（用于中国地图渲染），含海外/未知统计"""
    db = SessionLocal()
    try:
        # 中国省份数据（排除海外和未知）
        rows = (
            db.query(ChatUser.region, func.count(ChatUser.id).label("user_count"))
            .filter(
                ChatUser.region.isnot(None),
                ChatUser.region != "",
                ChatUser.region != "Unknown",
                ChatUser.region != "海外",
            )
            .group_by(ChatUser.region)
            .order_by(func.count(ChatUser.id).desc())
            .limit(100)
            .all()
        )

        data: list[dict[str, Any]] = []
        for row in rows:
            data.append(
                {
                    "region": str(row.region or ""),
                    "user_count": int(row.user_count or 0),
                }
            )

        # 海外和未知统计
        overseas_count = (
            db.query(func.count(ChatUser.id))
            .filter(ChatUser.region == "海外")
            .scalar()
            or 0
        )
        unknown_count = (
            db.query(func.count(ChatUser.id))
            .filter(
                (ChatUser.region.is_(None))
                | (ChatUser.region == "")
                | (ChatUser.region == "Unknown")
            )
            .scalar()
            or 0
        )

        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "查询成功",
                "data": data,
                "summary": {
                    "overseas_count": overseas_count,
                    "unknown_count": unknown_count,
                },
            },
        )
    except Exception as exc:
        logger.exception("获取 IP 分布失败")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"服务器错误: {exc}"},
        )
    finally:
        db.close()


@router.get("/api/dashboard/keywords")
def keywords(
    request: Request,
    days: int = Query(default=7, ge=1, le=90, description="统计最近 N 天"),
    limit: int = Query(default=30, ge=5, le=100, description="返回前 N 个关键词"),
) -> JSONResponse:
    """获取用户消息关键词词频（用于词云图）"""
    db = SessionLocal()
    try:
        start_date = cst_days_ago_str(days - 1)

        rows = (
            db.query(ChatSession.question)
            .filter(func.date(ChatSession.create_time) >= start_date)
            .all()
        )

        # 汇总所有用户问题
        all_text = " ".join(
            str(row.question or "") for row in rows if row.question
        )

        if not all_text.strip():
            return JSONResponse(
                status_code=200,
                content={"code": 200, "message": "暂无数据", "data": []},
            )

        # 中文分词 + 停用词过滤
        stop_words: set[str] = {
            # 标点/空白
            "", " ", "\n", "\t",
            # 常见停用词
            "的", "了", "是", "我", "你", "在", "不", "这", "有", "和",
            "就", "都", "也", "人", "个", "上", "里", "到", "说", "去",
            "为", "要", "会", "吗", "吧", "呢", "啊", "哦", "嗯", "哈",
            "可以", "什么", "怎么", "为什么", "怎么样", "那个", "这个",
            "哪", "哪个", "哪些", "很", "还", "能", "想", "让", "把",
            "被", "从", "对", "与", "或", "但", "而", "且", "如果", "因为",
            "所以", "然后", "之后", "以前", "以后", "时候", "现在",
            "比较", "非常", "没", "没有", "不是", "是否",
            "一下", "一点", "一些", "一种", "什么", "这样", "那样",
            "请问", "问一下", "想问", "想问问", "咨询", "想了解",
        }

        words = jieba.lcut(all_text)
        filtered: list[str] = [
            w.strip() for w in words
            if len(w.strip()) >= 2 and w.strip() not in stop_words
        ]

        counter = Counter(filtered)
        top = counter.most_common(limit)

        data: list[dict[str, Any]] = [
            {"word": word, "count": count} for word, count in top
        ]

        return JSONResponse(
            status_code=200,
            content={"code": 200, "message": "查询成功", "data": data},
        )
    except Exception as exc:
        logger.exception("获取关键词失败")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"服务器错误: {exc}"},
        )
    finally:
        db.close()


@router.get("/api/dashboard/overview")
def dashboard_overview(request: Request) -> JSONResponse:
    """数据大屏概览：总用户数、总消息数、今日消息数"""
    db = SessionLocal()
    try:
        today = cst_today_str()

        total_users = db.query(func.count(ChatUser.id)).scalar() or 0
        total_messages = db.query(func.count(ChatSession.id)).scalar() or 0

        today_messages = (
            db.query(func.count(ChatSession.id))
            .filter(func.date(ChatSession.create_time) == today)
            .scalar()
            or 0
        )

        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "查询成功",
                "data": {
                    "total_users": total_users,
                    "total_messages": total_messages,
                    "today_messages": today_messages,
                },
            },
        )
    except Exception as exc:
        logger.exception("获取概览失败")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"服务器错误: {exc}"},
        )
    finally:
        db.close()