import logging
import re
from typing import Any, Optional

from app.config import settings as _settings
from app.rag.schemas import RAGContext

logger = logging.getLogger(__name__)

# Keywords that strongly suggest a calculation-related query.
# When detected, the top-k is expanded to surface more calcul_metier documents.
_CALCUL_KEYWORDS = re.compile(
    r"\b("
    r"calcul|formule|formule|formula|"
    r"énergie|energie|kwh|kWh|"
    r"co2|co₂|carbone|"
    r"co[uû]t|tarif|dh|dirham|"
    r"économie|economie|saving|"
    r"dimming|intensit[eé]|"
    r"alerte|seuil|température|temperature|humidité|humidity|"
    r"risque|score|priorit[eé]|"
    r"lcu|zone|"
    r"cause probable|maintenabilit[eé]|communication|"
    r"puissance|watt|ampère|tension|courant|volt"
    r")\b",
    re.IGNORECASE,
)

# Document types that are always relevant for calculation queries
_CALCUL_DOC_TYPES = {"calcul_metier"}


def _is_calcul_query(query: str) -> bool:
    """Return True if the query is likely about a calculation or formula."""
    return bool(_CALCUL_KEYWORDS.search(query))


def _boost_calcul_chunks(chunks: list[dict], query: str) -> list[dict]:
    """
    Re-rank chunks so that calcul_metier documents bubble up for calculation queries.
    The embedding similarity score remains the primary signal; this adds a small
    positional boost (0.05) so that tied or near-tied chunks from calcul_metier
    documents are preferred over generic business-rule documents.
    """
    if not _is_calcul_query(query):
        return chunks

    boosted: list[dict] = []
    for chunk in chunks:
        doc_type = (chunk.get("metadata") or {}).get("document_type", "")
        extra = 0.05 if doc_type in _CALCUL_DOC_TYPES else 0.0
        boosted.append({**chunk, "score": (chunk.get("score") or 0.0) + extra})

    boosted.sort(key=lambda c: c.get("score", 0.0), reverse=True)
    return boosted


# ── Public search function ────────────────────────────────────

def search_rag(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Search the RAG knowledge base for chunks relevant to `query`.
    Uses the backend configured in settings (jsonb or pgvector).
    Applies keyword boosting for calculation-related queries so that
    calcul_metier documents are prioritised.

    Returns a list of dicts:
        chunk_id, title, source_type, content, score, metadata
    Never raises — returns [] on any failure.
    """
    try:
        from app.rag.embeddings import embed_query
        from app.rag.storage import search_jsonb, search_pgvector

        embedding = embed_query(query, _settings.embedding_model)

        # Fetch slightly more candidates when it's a calcul query so the
        # boost re-ranking has enough material to work with.
        fetch_limit = limit + 4 if _is_calcul_query(query) else limit

        if _settings.rag_backend == "pgvector":
            try:
                chunks = search_pgvector(embedding, fetch_limit)
            except Exception as e:
                logger.warning(f"pgvector search failed, falling back to jsonb: {e}")
                chunks = search_jsonb(embedding, fetch_limit)
        else:
            chunks = search_jsonb(embedding, fetch_limit)

        chunks = _boost_calcul_chunks(chunks, query)
        return chunks[:limit]

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
