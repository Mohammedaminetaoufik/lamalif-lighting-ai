import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.rag.schemas import IngestRequest, IngestResult
from app.config import settings as _settings

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = logging.getLogger(__name__)

_ingest_running = False


@router.post("/ingest", response_model=IngestResult)
def ingest_documents(body: IngestRequest, background_tasks: BackgroundTasks):
    """
    Ingest or re-ingest all rag_docs/ markdown files into the vector store.
    Runs in background if already running.
    """
    settings = _settings
    if not settings.rag_enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled (RAG_ENABLED=false)")

    try:
        from app.rag.ingestion import ingest_all
        result = ingest_all(force=body.force_reingest)
        return result
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.get("/search")
def rag_search(q: str, limit: int = 10):
    """Debug: show which RAG chunks are retrieved for a query."""
    from app.rag.retriever import search_rag
    chunks = search_rag(q, limit=limit)
    return {
        "query": q,
        "chunks_found": len(chunks),
        "chunks": [
            {
                "title": c.get("title"),
                "score": round(c.get("score", 0), 4),
                "preview": (c.get("content") or "")[:200],
            }
            for c in chunks
        ],
    }


@router.get("/status")
def rag_status():
    """Return RAG configuration and availability status."""
    settings = _settings

    status: dict = {
        "enabled": settings.rag_enabled,
        "backend": settings.rag_backend,
        "top_k": settings.rag_top_k,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
    }

    if not settings.rag_enabled:
        return {**status, "documents": 0, "chunks": 0, "model_loaded": False}

    try:
        from app.db import log_engine
        from sqlalchemy import text

        with log_engine.connect() as conn:
            doc_count = conn.execute(text("SELECT COUNT(*) FROM rag_documents")).scalar()
            chunk_count = conn.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar()
            pgvector_ok = False
            try:
                conn.execute(text("SELECT '[1,2,3]'::vector"))
                pgvector_ok = True
            except Exception:
                pass

        status["documents"] = doc_count
        status["chunks"] = chunk_count
        status["pgvector_available"] = pgvector_ok
    except Exception as e:
        status["db_error"] = str(e)
        status["documents"] = 0
        status["chunks"] = 0

    try:
        from app.rag.embeddings import _model
        status["model_loaded"] = _model is not None
    except Exception:
        status["model_loaded"] = False

    return status
