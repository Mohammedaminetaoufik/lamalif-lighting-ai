import logging
from typing import Any, Optional

from app.config import settings as _settings
from app.rag.schemas import RAGContext

logger = logging.getLogger(__name__)


# ── Public search function ────────────────────────────────────

def search_rag(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Search the RAG knowledge base for chunks relevant to `query`.
    Uses the backend configured in settings (jsonb or pgvector).

    Returns a list of dicts:
        chunk_id, title, source_type, content, score, metadata
    Never raises — returns [] on any failure.
    """
    try:
        from app.rag.embeddings import embed_query
        from app.rag.storage import search_jsonb, search_pgvector

        embedding = embed_query(query, _settings.embedding_model)

        if _settings.rag_backend == "pgvector":
            try:
                return search_pgvector(embedding, limit)
            except Exception as e:
                logger.warning(f"pgvector search failed, falling back to jsonb: {e}")
                return search_jsonb(embedding, limit)
        else:
            return search_jsonb(embedding, limit)

    except Exception as e:
        logger.warning(f"search_rag failed: {e}")
        return []


# ── RAG context builder (used by routes) ─────────────────────

def build_rag_context(query: str, extra_context: Optional[str] = None) -> RAGContext:
    """
    Retrieve RAG context for a query and format it for LLM prompt injection.
    Never raises — returns a disabled/empty context on any failure.
    """
    if not _settings.rag_enabled:
        return RAGContext(enabled=False, used=False)

    try:
        return _retrieve(query, extra_context)
    except Exception as e:
        logger.warning(f"RAG retrieval failed, continuing without RAG: {e}")
        return RAGContext(enabled=True, used=False, error=str(e))


def _retrieve(query: str, extra_context: Optional[str]) -> RAGContext:
    full_query = f"{query}\n{extra_context}" if extra_context else query
    chunks = search_rag(full_query, limit=_settings.rag_top_k)

    if not chunks:
        return RAGContext(enabled=True, used=False)

    context_parts: list[str] = []
    total_chars = 0
    sources: list[str] = []

    for chunk in chunks:
        segment = f"[Source: {chunk['title']}]\n{chunk['content']}"
        if total_chars + len(segment) > _settings.rag_max_context_chars:
            break
        context_parts.append(segment)
        total_chars += len(segment)
        title = chunk["title"]
        if title not in sources:
            sources.append(title)

    if not context_parts:
        return RAGContext(enabled=True, used=False)

    return RAGContext(
        enabled=True,
        used=True,
        chunks_count=len(context_parts),
        sources=sources,
        context_text="\n\n---\n\n".join(context_parts),
    )
