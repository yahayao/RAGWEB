"""编排层 SSE 转发。"""

import json
import logging
from typing import AsyncGenerator

from starlette.requests import Request

logger = logging.getLogger(__name__)


async def rag_stream_response(
    http_request: Request,
    llm_stream: AsyncGenerator[dict, None],
    request_id: str,
    created_time: int,
) -> AsyncGenerator[str, None]:
    """将内部 LLM 正文 chunk 转成前端 SSE。"""
    try:
        async for chunk in llm_stream:
            if await http_request.is_disconnected():
                break
            content = chunk.get("content") or ""
            finish_reason = chunk.get("finish_reason")
            if not content and not finish_reason:
                continue
            delta = {"content": content} if content else {}
            payload = {
                "id": request_id,
                "object": "rag.completion.chunk",
                "created": created_time,
                "choices": [{
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }],
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    except Exception as exc:
        logger.exception("RAG 流式转发失败: %s", exc)
        error_chunk = {
            "id": request_id,
            "object": "error",
            "created": created_time,
            "error": {"type": "upstream_error", "message": "生成服务暂时不可用"},
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"
