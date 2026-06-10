from pydantic import BaseModel, Field
from typing import Optional, Any


class RAGChunk(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    metadata: Optional[dict[str, Any]] = None
    score: Optional[float] = None


class RAGDocument(BaseModel):
    id: int
    title: str
    source_type: str
    source_path: Optional[str] = None
    content: str
    metadata: Optional[dict[str, Any]] = None


class RAGContext(BaseModel):
    enabled: bool = True
    used: bool = False
    chunks_count: int = 0
    sources: list[str] = Field(default_factory=list)
    context_text: str = ""
    error: Optional[str] = None


class IngestRequest(BaseModel):
    force_reingest: bool = False


class IngestResult(BaseModel):
    documents_processed: int
    chunks_created: int
    chunks_updated: int
    errors: list[str] = Field(default_factory=list)
