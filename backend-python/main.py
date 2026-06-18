"""RAGWEB 后端主入口 — FastAPI 应用

挂载模块:
- /api/chat/*    聊天记录 CRUD（内联实现）
- /api/statistic 数据统计 API（statistic.py 子路由）
- /api/ip        IP 查询 API（ip2location.py 子路由）
- /dashboard     数据大屏页面
- /api/dashboard 数据大屏数据 API
- /api/alert     人工介入告警
- /ws/dashboard  数据大屏 WebSocket 实时推送
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 共享数据库模块
import database

# 子路由
from statistic import router as statistic_router
from ip2location import router as ip_router
from dashboard import router as dashboard_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表+初始化 IP 检索器，关闭时释放资源"""
    database.ensure_schema()
    database.init_searcher()
    logger.info("RAGWEB backend started")
    yield
    database.close_searcher()
    logger.info("RAGWEB backend stopped")


app = FastAPI(
    title="RAGWEB Backend",
    version="2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# 根健康检查
# ==============================

@app.get("/")
def health_check():
    return {"code": 200, "message": "RAGWEB Backend OK"}


# ==============================
# /api/chat/* 聊天记录接口
# ==============================

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from typing import Any


async def _safe_json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


@app.post("/api/chat/register")
async def register_user(request: Request) -> JSONResponse:
    """注册新用户：返回自增 id 作为用户标识，username 存展示名（可重复）"""
    body = await _safe_json_body(request)
    display_name = str(body.get("display_name") or "").strip()
    if not display_name:
        return JSONResponse(status_code=400, content={"code": 400, "message": "请输入称呼"})
    db = database.SessionLocal()
    try:
        client_ip = database.extract_client_ip(request)
        result = database.register_user(db, display_name, client_ip)
        db.commit()
        return JSONResponse(status_code=200, content={"code": 200, "message": "注册成功", "data": result})
    except Exception as exc:
        db.rollback()
        logger.exception("用户注册失败")
        return JSONResponse(status_code=500, content={"code": 500, "message": f"服务器错误: {exc}"})
    finally:
        db.close()


@app.get("/api/chat/records/{session_id:path}")
def get_records(session_id: str, request: Request) -> JSONResponse:
    """获取指定会话的历史记录"""
    user_id = database.parse_user_id(request.query_params.get("user_id"))
    db = database.SessionLocal()
    try:
        if not user_id or not database.user_exists(db, user_id):
            return JSONResponse(status_code=200, content={"code": 200, "message": "获取成功", "data": []})

        turns = (
            db.query(database.ChatSession)
            .filter(
                database.ChatSession.session_id == session_id,
                database.ChatSession.user_id == user_id,
            )
            .order_by(database.ChatSession.create_time.asc(), database.ChatSession.id.asc())
            .all()
        )

        messages: list[dict[str, Any]] = []
        for turn in turns:
            ctime = database._to_str_time(turn.create_time)
            messages.append({
                "id": f"{turn.id}-u",
                "role": "user",
                "content": turn.question,
                "create_time": ctime,
            })
            messages.append({
                "id": f"{turn.id}-a",
                "role": "assistant",
                "content": turn.answer,
                "create_time": ctime,
            })

        return JSONResponse(status_code=200, content={"code": 200, "message": "获取成功", "data": messages})
    except Exception as exc:
        logger.exception("获取记录失败")
        return JSONResponse(status_code=500, content={"code": 500, "message": f"服务器错误: {exc}"})
    finally:
        db.close()


@app.delete("/api/chat/records/{session_id:path}")
def delete_records(session_id: str, request: Request) -> JSONResponse:
    """删除指定会话的全部记录"""
    user_id = database.parse_user_id(request.query_params.get("user_id"))
    db = database.SessionLocal()
    try:
        if not user_id or not database.user_exists(db, user_id):
            return JSONResponse(status_code=200, content={"code": 200, "message": "删除成功", "data": {"affectedRows": 0}})

        affected = (
            db.query(database.ChatSession)
            .filter(
                database.ChatSession.session_id == session_id,
                database.ChatSession.user_id == user_id,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return JSONResponse(status_code=200, content={"code": 200, "message": "删除成功", "data": {"affectedRows": affected}})
    except Exception as exc:
        db.rollback()
        return JSONResponse(status_code=500, content={"code": 500, "message": f"服务器错误: {exc}"})
    finally:
        db.close()


@app.get("/api/chat/sessions/{user_id:path}")
def list_sessions(user_id: str, request: Request) -> JSONResponse:
    """获取用户的所有会话列表"""
    db = database.SessionLocal()
    try:
        uid_int = database.parse_user_id(user_id)
        if not uid_int or not database.user_exists(db, uid_int):
            return JSONResponse(status_code=404, content={"code": 404, "message": "用户不存在"})
        rows = db.execute(
            text("""
                SELECT cs.session_id,
                       MAX(cs.create_time) AS last_time,
                       MIN(cs.create_time) AS create_time,
                       (SELECT question
                        FROM chat_sessions
                        WHERE session_id = cs.session_id AND user_id = cs.user_id
                        ORDER BY create_time ASC, id ASC
                        LIMIT 1) AS first_message
                FROM chat_sessions cs
                WHERE cs.user_id = :uid
                GROUP BY cs.session_id, cs.user_id
                ORDER BY last_time DESC
            """),
            {"uid": uid_int},
        ).mappings().all()

        data: list[dict[str, Any]] = []
        for row in rows:
            data.append({
                "session_id": row.get("session_id"),
                "last_time": database._to_str_time(row.get("last_time")),
                "create_time": database._to_str_time(row.get("create_time")),
                "first_message": row.get("first_message"),
            })

        return JSONResponse(status_code=200, content={"code": 200, "message": "获取成功", "data": data})
    except Exception as exc:
        db.rollback()
        return JSONResponse(status_code=500, content={"code": 500, "message": f"服务器错误: {exc}"})
    finally:
        db.close()


@app.post("/api/chat/record")
async def save_record(request: Request) -> JSONResponse:
    """保存一轮对话记录"""
    body = await _safe_json_body(request)
    user_id = database.parse_user_id(str(body.get("user_id") or ""))
    session_id = str(body.get("session_id") or "").strip()
    question = str(body.get("question") or "").strip()
    answer = str(body.get("answer") or "").strip()

    if not user_id or not session_id or not question or not answer:
        return JSONResponse(status_code=400, content={"code": 400, "message": "缺少必要字段：user_id/session_id/question/answer"})

    db = database.SessionLocal()
    try:
        if not database.user_exists(db, user_id):
            return JSONResponse(status_code=400, content={"code": 400, "message": "用户不存在，请先注册"})
        turn = database.ChatSession(user_id=user_id, session_id=session_id, question=question, answer=answer)
        db.add(turn)
        db.flush()
        insert_id = int(turn.id)
        db.commit()
        return JSONResponse(status_code=200, content={"code": 200, "message": "保存成功", "data": {"id": insert_id}})
    except Exception as exc:
        db.rollback()
        return JSONResponse(status_code=500, content={"code": 500, "message": f"服务器错误: {exc}"})
    finally:
        db.close()


# ==============================
# 挂载子路由
# ==============================

app.include_router(statistic_router)     # /api/statistic/*
app.include_router(ip_router)            # /api/ip/*
app.include_router(dashboard_router)     # /dashboard, /api/dashboard/*, /api/alert/*, /ws/dashboard
