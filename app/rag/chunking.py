import hashlib
from dataclasses import dataclass


@dataclass
class Chunk:
    content: str
    chunk_index: int
    content_hash: str
    metadata: dict


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + chunk_size
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(Chunk(
                content=chunk_content,
                chunk_index=idx,
                content_hash=_hash(chunk_content),
                metadata={"start_char": start, "end_char": end},
            ))
            idx += 1
        if end >= len(text):
            break
        start = end - chunk_overlap

    return chunks


def chunk_markdown(text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Split markdown by section (##), then further by chunk_size if needed."""
    sections = _split_by_headers(text)
    all_chunks: list[Chunk] = []
    global_index = 0

    for section in sections:
        if len(section) <= chunk_size:
            if section.strip():
                all_chunks.append(Chunk(
                    content=section.strip(),
                    chunk_index=global_index,
                    content_hash=_hash(section.strip()),
                    metadata={},
                ))
                global_index += 1
        else:
            sub_chunks = chunk_text(section, chunk_size, chunk_overlap)
            for sc in sub_chunks:
                sc.chunk_index = global_index
                global_index += 1
                all_chunks.append(sc)

    return all_chunks


def _split_by_headers(text: str) -> list[str]:
    """Split markdown text at ## headers."""
    lines = text.split("\n")
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("## ") and current:
            sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("\n".join(current))

    return [s for s in sections if s.strip()]
