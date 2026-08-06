"""现有检索/query rewrite 服务适配器。

只迁移调用位置，不修改索引、嵌入或检索服务协议。
"""

import logging

import httpx

from rag.settings import (
    RAG_EMBEDDING_API_URL,
    RAG_EMBEDDING_TIMEOUT,
    RAG_EMBEDDING_TOP_K,
    RAG_ENABLE_QUERY_REWRITE,
    RAG_QUERY_REWRITER_MAX,
    RAG_QUERY_REWRITER_TIMEOUT,
    RAG_QUERY_REWRITER_URL,
)

logger = logging.getLogger(__name__)


async def fetch_contexts(question: str, history: list[dict[str, str]]) -> list[dict]:
    """返回规范化后的检索上下文列表，失败时降级为空列表。"""
    queries, reranker = await _rewrite_queries(question, history)

    payload = {"query": question, "k": RAG_EMBEDDING_TOP_K}
    if len(queries) > 1:
        payload["queries"] = queries
        payload["query_reranker"] = reranker

    try:
        async with httpx.AsyncClient(timeout=RAG_EMBEDDING_TIMEOUT) as client:
            resp = await client.post(RAG_EMBEDDING_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return _normalize_contexts(data.get("contexts", []))
    except httpx.ConnectError:
        logger.error("无法连接检索服务：%s", RAG_EMBEDDING_API_URL)
        return []
    except httpx.HTTPStatusError as exc:
        logger.error("检索服务返回错误：%s %s", exc.response.status_code, exc.response.text)
        return []
    except Exception as exc:
        logger.exception("检索服务调用异常: %s", exc)
        return []


async def _rewrite_queries(
    question: str,
    history: list[dict[str, str]],
) -> tuple[list[str], str]:
    if not RAG_ENABLE_QUERY_REWRITE:
        return [question], question

    try:
        async with httpx.AsyncClient(timeout=RAG_QUERY_REWRITER_TIMEOUT) as client:
            resp = await client.post(
                RAG_QUERY_REWRITER_URL,
                json={
                    "question": question,
                    "history": history[-10:],
                    "num_queries": RAG_QUERY_REWRITER_MAX,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        queries = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
        if not queries:
            return [question], question
        return queries[:RAG_QUERY_REWRITER_MAX], str(data.get("query_reranker") or question)
    except httpx.ConnectError:
        logger.warning("Query rewriter 不可达，降级为原始 query")
        return [question], question
    except httpx.HTTPStatusError as exc:
        logger.warning("Query rewriter 返回错误 %s，降级为原始 query", exc.response.status_code)
        return [question], question
    except Exception as exc:
        logger.warning("Query rewriter 调用异常: %s", exc)
        return [question], question


def _normalize_contexts(raw_results: list) -> list[dict]:
    contexts: list[dict] = []
    for item in raw_results or []:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        try:
            similarity = float(item.get("similarity", 1.0))
        except (TypeError, ValueError):
            similarity = 1.0
        contexts.append({
            "content": content,
            "similarity": similarity,
            "source": str(item.get("source") or ""),
        })
    return contexts
