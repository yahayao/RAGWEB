"""RAG 编排层请求/响应模型。"""

from pydantic import BaseModel, Field


class RagChatRequest(BaseModel):
    """前端 RAG 请求体，只允许携带用户问题、会话和流式标记。"""

    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=64)
    stream: bool = False


class RagChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class RagChatResponse(BaseModel):
    id: str
    object: str = "rag.completion"
    created: int
    question: str
    choices: list[dict]
    usage: RagChatUsage
