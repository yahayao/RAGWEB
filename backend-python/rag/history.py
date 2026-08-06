"""从数据库加载并校验多轮对话历史。"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

import database
from rag.settings import RAG_MAX_HISTORY_CHARS, RAG_MAX_HISTORY_TURNS


def ensure_session_access(db: Session, user_id: int, session_id: str) -> None:
    """已存在的会话必须属于当前用户，新会话允许使用。"""
    if database.session_has_records(db, session_id):
        if not database.session_has_records_for_user(db, user_id, session_id):
            raise HTTPException(status_code=403, detail="无权访问该会话")


def load_history(db: Session, user_id: int, session_id: str) -> list[dict[str, str]]:
    """加载最近 N 轮历史并转为 LLM messages。"""
    turns = (
        db.query(database.ChatSession)
        .filter(
            database.ChatSession.user_id == user_id,
            database.ChatSession.session_id == session_id,
        )
        .order_by(database.ChatSession.create_time.asc(), database.ChatSession.id.asc())
        .all()
    )

    messages: list[dict[str, str]] = []
    for turn in turns[-RAG_MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": _truncate(turn.question)})
        messages.append({"role": "assistant", "content": _truncate(turn.answer)})
    return messages[-RAG_MAX_HISTORY_TURNS * 2:]


def _truncate(content: str) -> str:
    content = (content or "").strip()
    if len(content) > RAG_MAX_HISTORY_CHARS:
        return content[:RAG_MAX_HISTORY_CHARS]
    return content
