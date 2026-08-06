"""内部 LLM 服务客户端。

调用另一个实现方按契约提供的 `POST /v1/internal/chat`。
"""

import json
import logging
from typing import Any, AsyncGenerator

import httpx

from rag.settings import (
    INTERNAL_API_KEY,
    LLM_BASE_URL,
    LLM_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class LLMUpstreamError(Exception):
    """LLM 服务不可用或返回错误。"""


async def call_llm(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    top_p: float = 0.8,
) -> tuple[str, str, dict[str, int]]:
    """调用内部 LLM 非流式接口，返回 (content, finish_reason, usage)。"""
    payload = {
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/v1/internal/chat",
                json=payload,
                headers={"X-Internal-Key": INTERNAL_API_KEY},
            )
            if resp.status_code >= 400:
                raise LLMUpstreamError(
                    f"LLM 服务返回 {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.exception("LLM 服务请求失败: %s", exc)
        raise LLMUpstreamError("LLM 服务不可用") from exc

    content = _extract_content(data)
    finish_reason = _extract_finish_reason(data)
    usage = _extract_usage(data)
    return content, finish_reason, usage


async def stream_llm(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    top_p: float = 0.8,
) -> AsyncGenerator[dict[str, Any], None]:
    """流式转发内部 LLM 的 SSE chunk。"""
    payload = {
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                f"{LLM_BASE_URL}/v1/internal/chat",
                json=payload,
                headers={"X-Internal-Key": INTERNAL_API_KEY},
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", errors="ignore")
                    raise LLMUpstreamError(
                        f"LLM 服务返回 {resp.status_code}: {body[:200]}"
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if not raw:
                        continue
                    if raw == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    choice = (chunk.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    content = delta.get("content") or ""
                    finish_reason = choice.get("finish_reason")
                    if content or finish_reason:
                        yield {
                            "content": content,
                            "finish_reason": finish_reason,
                        }
    except httpx.HTTPError as exc:
        logger.exception("LLM 流式请求失败: %s", exc)
        raise LLMUpstreamError("LLM 服务不可用") from exc


def _extract_content(data: dict) -> str:
    content = data.get("content")
    if isinstance(content, str):
        return content
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        value = message.get("content")
        if isinstance(value, str):
            return value
    return ""


def _extract_finish_reason(data: dict) -> str:
    value = data.get("finish_reason")
    if value:
        return str(value)
    choices = data.get("choices") or []
    if choices:
        value = choices[0].get("finish_reason")
        if value:
            return str(value)
    return "stop"


def _extract_usage(data: dict) -> dict[str, int]:
    usage = data.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "total_tokens": int(usage.get("total_tokens", 0)),
    }
