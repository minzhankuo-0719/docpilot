import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    page_or_slide: int
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_text(
    text: str,
    *,
    doc_id: str,
    source: str,
    page_or_slide: int,
    chunk_size: int = 400,   # words per chunk
    overlap: int = 50,       # word overlap between consecutive chunks
) -> list[Chunk]:
    """Split text into overlapping word-count-based chunks."""
    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_str = " ".join(words[start:end])
        chunk_id = hashlib.sha256(
            f"{doc_id}:{page_or_slide}:{idx}".encode()
        ).hexdigest()[:16]

        chunks.append(Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            source=source,
            page_or_slide=page_or_slide,
            chunk_index=idx,
            text=chunk_str,
        ))

        if end == len(words):
            break
        start = end - overlap
        idx += 1

    return chunks
