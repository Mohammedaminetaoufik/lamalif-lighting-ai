from pydantic import BaseModel
from typing import Any


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AIQueryRequest(BaseModel):
    question: str
    language: str = "fr"
    max_rows: int = 100
    conversation_history: list[ConversationMessage] | None = None


class ChartSpec(BaseModel):
    type: str = "table"
    x: str | None = None
    y: str | None = None


class RAGInfo(BaseModel):
    enabled: bool = False
    used: bool = False
    chunks_count: int = 0
    sources: list[str] = []


class AIQueryResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    summary: str
    analysis: str | None = None
    recommendation: str
    priority: str | None = "medium"
    chat_response: str | None = None
    chart: ChartSpec
    confidence: float
    execution_time_ms: int
    rag: RAGInfo | None = None


class SQLValidateRequest(BaseModel):
    sql: str


class SQLValidateResponse(BaseModel):
    valid: bool
    safe_sql: str | None = None
    message: str | None = None
    error: str | None = None


class AIHistoryItem(BaseModel):
    id: int
    user_id: int | None = None
    question: str
    generated_sql: str | None = None
    status: str
    row_count: int
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: Any
