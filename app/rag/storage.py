import json
import logging
from typing import Any, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


def _get_engine():
    from app.db import log_engine
    return log_engine


# ── Documents ────────────────────────────────────────────────


def upsert_document(
    title: str,
    source_type: str,
    content: str,
    content_hash: str,
    source_path: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> tuple[int, bool]:
    """Insert or update a RAG document. Returns (document_id, was_updated)."""
    engine = _get_engine()
    # Serialize to JSON string — CAST(:param AS jsonb) expects a text value
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, content_hash FROM rag_documents"
                " WHERE title = :title AND source_type = :stype"
            ),
            {"title": title, "stype": source_type},
        ).fetchone()

        if row is None:
            result = conn.execute(
                text("""
                    INSERT INTO rag_documents
                        (title, source_type, source_path, content, content_hash, metadata)
                    VALUES (:title, :stype, :spath, :content, :chash, CAST(:meta AS jsonb))
                    RETURNING id
                """),
                {
                    "title": title, "stype": source_type, "spath": source_path,
                    "content": content, "chash": content_hash, "meta": meta_json,
                },
            )
            doc_id = result.fetchone()[0]
            return doc_id, True

        if row[1] == content_hash:
            return row[0], False

        conn.execute(
            text("""
                UPDATE rag_documents
                SET content      = :content,
                    content_hash = :chash,
                    source_path  = :spath,
                    metadata     = CAST(:meta AS jsonb),
                    updated_at   = NOW()
                WHERE id = :id
            """),
            {
                "content": content, "chash": content_hash, "spath": source_path,
                "meta": meta_json, "id": row[0],
            },
        )
        return row[0], True


def count_documents() -> int:
    engine = _get_engine()
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM rag_documents")).scalar() or 0


# ── Chunks ───────────────────────────────────────────────────


def insert_chunk(
    document_id: int,
    chunk_index: int,
    content: str,
    content_hash: str,
    embedding: Optional[list[float]],
    metadata: Optional[dict] = None,
) -> bool:
    """
    Insert or update a single RAG chunk.
    Always stores the embedding in embedding_json (JSONB) — no pgvector column used.
    Returns True if the row was inserted/updated, False if content is unchanged.
    """
    engine = _get_engine()
    # Both columns are JSONB — serialize to JSON string and use CAST(:x AS jsonb)
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    emb_json_str = json.dumps(embedding if embedding is not None else [], ensure_ascii=False)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, content_hash FROM rag_chunks"
                " WHERE document_id = :did AND chunk_index = :cidx"
            ),
            {"did": document_id, "cidx": chunk_index},
        ).fetchone()

        if row is not None and row[1] == content_hash:
            return False

        conn.execute(
            text("""
                INSERT INTO rag_chunks
                    (document_id, chunk_index, content, content_hash, embedding_json, metadata)
                VALUES
                    (:did, :cidx, :content, :chash,
                     CAST(:ejson AS jsonb),
                     CAST(:meta  AS jsonb))
                ON CONFLICT (document_id, chunk_index) DO UPDATE
                SET content        = EXCLUDED.content,
                    content_hash   = EXCLUDED.content_hash,
                    embedding_json = EXCLUDED.embedding_json,
                    metadata       = EXCLUDED.metadata
            """),
            {
                "did":     document_id,
                "cidx":    chunk_index,
                "content": content,
                "chash":   content_hash,
                "ejson":   emb_json_str,
                "meta":    meta_json,
            },
        )
        return True


def upsert_chunk(
    document_id: int,
    chunk_index: int,
    content: str,
    content_hash: str,
    embedding: Optional[list[float]],
    embedding_json: Optional[list[float]] = None,
    metadata: Optional[dict] = None,
) -> bool:
    """Backward-compatibility alias → delegates to insert_chunk."""
    return insert_chunk(
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        content_hash=content_hash,
        embedding=embedding,
        metadata=metadata,
    )


def delete_chunks_for_document(document_id: int) -> int:
    """Delete all chunks for a document. Returns deleted count."""
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM rag_chunks WHERE document_id = :did"),
            {"did": document_id},
        )
        return result.rowcount


def delete_old_chunks(document_id: int, keep_indices: list[int]) -> int:
    """
    Remove chunks for a document whose chunk_index is not in keep_indices.
    SQLAlchemy text() doesn't support list binding directly, so we build
    the IN clause with individual named placeholders.
    """
    if not keep_indices:
        return delete_chunks_for_document(document_id)

    engine = _get_engine()
    placeholders = ", ".join(f":idx_{i}" for i in range(len(keep_indices)))
    params: dict[str, Any] = {"did": document_id}
    params.update({f"idx_{i}": v for i, v in enumerate(keep_indices)})

    with engine.begin() as conn:
        result = conn.execute(
            text(
                f"DELETE FROM rag_chunks"
                f" WHERE document_id = :did AND chunk_index NOT IN ({placeholders})"
            ),
            params,
        )
        return result.rowcount


def count_chunks() -> int:
    engine = _get_engine()
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar() or 0


# ── Search ───────────────────────────────────────────────────


def search_jsonb(query_embedding: list[float], top_k: int) -> list[dict[str, Any]]:
    """
    Search chunks by cosine similarity against JSONB-stored embeddings.
    All similarity computation is done in Python (numpy) — no pgvector used.
    """
    from app.rag.embeddings import cosine_similarity

    engine = _get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT c.id, c.content, d.title, d.source_type,
                       c.embedding_json, c.metadata
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.document_id
                WHERE c.embedding_json IS NOT NULL
            """)
        ).fetchall()

    if not rows:
        return []

    scored: list[dict[str, Any]] = []
    for r in rows:
        stored_emb = r[4]
        if stored_emb is None:
            continue
        # embedding_json arrives as a Python list from psycopg's JSONB decoder
        try:
            score = cosine_similarity(query_embedding, stored_emb)
        except Exception:
            continue
        scored.append({
            "chunk_id":    r[0],
            "id":          r[0],
            "content":     r[1],
            "title":       r[2],
            "source_type": r[3],
            "score":       score,
            "metadata":    r[5] or {},
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def search_pgvector(query_embedding: list[float], top_k: int) -> list[dict[str, Any]]:
    """
    Search chunks using pgvector cosine distance.
    Requires 04_rag_tables_pgvector.sql to have been applied (adds `embedding vector(384)`).
    Uses CAST(:emb AS vector) to avoid the :param::type psycopg parsing issue.
    """
    engine = _get_engine()
    emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT c.id, c.content, d.title, d.source_type,
                       1 - (c.embedding <=> CAST(:emb AS vector)) AS score,
                       c.metadata
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.document_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> CAST(:emb AS vector)
                LIMIT :k
            """),
            {"emb": emb_str, "k": top_k},
        ).fetchall()

    return [
        {
            "chunk_id":    r[0],
            "id":          r[0],
            "content":     r[1],
            "title":       r[2],
            "source_type": r[3],
            "score":       float(r[4]),
            "metadata":    r[5] or {},
        }
        for r in rows
    ]
