import hashlib
import logging
from pathlib import Path

from app.config import settings as _app_settings
from app.rag.chunking import chunk_markdown
from app.rag.embeddings import embed_texts
from app.rag.schemas import IngestResult
from app.rag.storage import delete_old_chunks, insert_chunk, upsert_document

logger = logging.getLogger(__name__)

RAG_DOCS_DIR = Path(__file__).parent.parent.parent / "rag_docs"


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _embed_chunks(chunk_texts: list[str], model: str, filename: str) -> list:
    try:
        return embed_texts(chunk_texts, model)
    except Exception as e:
        logger.warning(f"Embedding failed for {filename}: {e}. Storing without embeddings.")
        return [None] * len(chunk_texts)


def _extract_frontmatter_metadata(content: str) -> dict:
    """Extract YAML frontmatter metadata if present (--- ... ---)."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    frontmatter = content[3:end].strip()
    meta: dict = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def _ingest_file(md_file: Path, force: bool, result: IngestResult, settings) -> None:
    content = md_file.read_text(encoding="utf-8")
    content_hash = _file_hash(content)
    title = md_file.stem.replace("_", " ").title()

    # Enrich metadata from YAML frontmatter + file path
    frontmatter = _extract_frontmatter_metadata(content)
    relative_path = str(md_file.relative_to(RAG_DOCS_DIR))
    metadata = {
        "filename": md_file.name,
        "relative_path": relative_path,
        "document_type": frontmatter.get("document_type", "markdown"),
        "domain": frontmatter.get("domain", "smart_lighting"),
        "module": frontmatter.get("module", ""),
        "source_code": frontmatter.get("source_code", ""),
        "audience": frontmatter.get("audience", ""),
        "language": frontmatter.get("language", "fr"),
        "version": frontmatter.get("version", "1.0"),
    }

    # Use frontmatter module as a better title when available
    if frontmatter.get("module"):
        title = frontmatter["module"].replace("_", " ").title()

    doc_id, was_updated = upsert_document(
        title=title,
        source_type="markdown",
        content=content,
        content_hash=content_hash,
        source_path=relative_path,
        metadata=metadata,
    )

    if not was_updated and not force:
        logger.debug(f"Skipping unchanged document: {md_file.name}")
        return

    chunks = chunk_markdown(content, settings.rag_chunk_size, settings.rag_chunk_overlap)
    if not chunks:
        logger.warning(f"No chunks generated for {md_file.name}")
        return

    embeddings = _embed_chunks([c.content for c in chunks], settings.embedding_model, md_file.name)

    keep_indices = []
    for chunk, emb in zip(chunks, embeddings):
        created = insert_chunk(
            document_id=doc_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            embedding=emb,
            metadata=chunk.metadata,
        )
        keep_indices.append(chunk.chunk_index)
        if created:
            result.chunks_created += 1
        else:
            result.chunks_updated += 1

    delete_old_chunks(doc_id, keep_indices)
    result.documents_processed += 1
    logger.info(f"Ingested {md_file.name}: {len(chunks)} chunks")


def ingest_all(force: bool = False) -> IngestResult:
    settings = _app_settings
    result = IngestResult(documents_processed=0, chunks_created=0, chunks_updated=0)

    if not RAG_DOCS_DIR.exists():
        result.errors.append(f"rag_docs directory not found: {RAG_DOCS_DIR}")
        logger.error(result.errors[-1])
        return result

    # rglob("**/*.md") discovers files in all subdirectories (metier/calculs/, etc.)
    md_files = sorted(RAG_DOCS_DIR.rglob("*.md"))
    if not md_files:
        logger.warning("No markdown files found in rag_docs/ (including subdirectories)")
        return result

    logger.info(f"Found {len(md_files)} markdown files to ingest")

    for md_file in md_files:
        try:
            _ingest_file(md_file, force, result, settings)
        except Exception as e:
            msg = f"Error ingesting {md_file.name}: {e}"
            logger.error(msg)
            result.errors.append(msg)

    return result
