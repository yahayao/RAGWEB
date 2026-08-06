"""RAG 编排层 HTTP 路由。"""

import logging
import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import database
from rag.auth import get_current_user
from rag.history import ensure_session_access, load_history
from rag.llm_client import LLMUpstreamError, call_llm, stream_llm
from rag.prompt_builder import (
    NO_CONTEXT_REPLY,
    build_system_prompt,
    get_identity_guard_reply,
)
from rag.retrieval import fetch_contexts
from rag.schemas import RagChatRequest
from rag.streaming import rag_stream_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/chat")
async def rag_chat(
    http_request: Request,
    body: RagChatRequest,
    user: database.ChatUser = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """公开前端唯一的 RAG 对话入口。"""
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    ensure_session_access(db, user.id, body.session_id)
    history = load_history(db, user.id, body.session_id)

    guard_reply = get_identity_guard_reply(question)
    if guard_reply:
        return _reply_response(question, guard_reply, body.stream)

    contexts = await fetch_contexts(question, history)
    if not contexts:
        return _reply_response(question, NO_CONTEXT_REPLY, body.stream)

    system_prompt = build_system_prompt(contexts)
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": question},
    ]

    request_id = uuid4().hex
    created_time = int(time.time())
    if body.stream:
        llm_stream = stream_llm(messages)
        return StreamingResponse(
            rag_stream_response(
                http_request,
                llm_stream,
                request_id,
                created_time,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        content, finish_reason, usage = await call_llm(messages)
    except LLMUpstreamError as exc:
        logger.error("LLM 上游调用失败: %s", exc)
        raise HTTPException(status_code=502, detail="生成服务暂时不可用") from exc

    return {
        "id": request_id,
        "object": "rag.completion",
        "created": created_time,
        "question": question,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": finish_reason,
        }],
        "usage": usage,
    }


def _reply_response(
    question: str,
    content: str,
    stream: bool,
):
    """固定话术/无检索结果不调用 LLM，直接返回。"""
    request_id = uuid4().hex
    created_time = int(time.time())
    if stream:
        async def fixed_stream():
            payload = {
                "id": request_id,
                "object": "rag.completion.chunk",
                "created": created_time,
                "choices": [{
                    "index": 0,
                    "delta": {"content": content},
                    "finish_reason": "stop",
                }],
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            fixed_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return {
        "id": request_id,
        "object": "rag.completion",
        "created": created_time,
        "question": question,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
