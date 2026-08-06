"""RAG 编排层服务端配置。

这些配置只允许在部署环境或后端 .env 中修改，前端不暴露任何入口。
"""

import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "180"))

RAG_EMBEDDING_API_URL = os.getenv(
    "RAG_EMBEDDING_API_URL",
    "http://127.0.0.1:6006/retrieve",
)
RAG_EMBEDDING_TOP_K = int(os.getenv("RAG_EMBEDDING_TOP_K", "10"))
RAG_EMBEDDING_TIMEOUT = int(os.getenv("RAG_EMBEDDING_TIMEOUT", "30"))

RAG_QUERY_REWRITER_URL = os.getenv(
    "RAG_QUERY_REWRITER_URL",
    "http://127.0.0.1:5000/rewrite",
)
RAG_QUERY_REWRITER_TIMEOUT = int(os.getenv("RAG_QUERY_REWRITER_TIMEOUT", "15"))
RAG_ENABLE_QUERY_REWRITE = os.getenv(
    "RAG_ENABLE_QUERY_REWRITE",
    "true",
).lower() in {"1", "true", "yes", "on"}
RAG_QUERY_REWRITE_MAX = int(os.getenv("RAG_QUERY_REWRITE_MAX", "5"))

RAG_MAX_HISTORY_TURNS = int(os.getenv("RAG_MAX_HISTORY_TURNS", "20"))
RAG_MAX_QUESTION_CHARS = int(os.getenv("RAG_MAX_QUESTION_CHARS", "2000"))
RAG_MAX_HISTORY_CHARS = int(os.getenv("RAG_MAX_HISTORY_CHARS", "2000"))
RAG_MAX_CONTEXT_ITEMS = int(os.getenv("RAG_MAX_CONTEXT_ITEMS", "20"))
RAG_MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "20000"))
