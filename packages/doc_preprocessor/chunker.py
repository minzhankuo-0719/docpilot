"""Chunking — paragraph & sentence aware, caption / heading isolated.

The chunker treats blocks as the atomic unit, preserves caption / heading
blocks as standalone chunks (so figure captions never bleed into body
text), packs paragraph blocks greedily up to ``max_words``, sub-splits
oversize paragraphs on sentence boundaries, and overlaps successive body
chunks by ``overlap_sentences`` for retrieval continuity.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from .pdf import Block

# Sentence boundary: end-punctuation (incl. CJK) followed by whitespace.
_SENT_BOUNDARY_RE = re.compile(r"(?<=[.!?。！？])\s+")


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    page_or_slide: int
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _make_chunk_id(doc_id: str, page: int, idx: int) -> str:
    return hashlib.sha256(f"{doc_id}:{page}:{idx}".encode()).hexdigest()[:16]


def _split_sentences(text: str) -> list[str]:
    parts = _SENT_BOUNDARY_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


def _split_by_words(text: str, max_words: int, overlap_words: int = 30) -> list[str]:
    """Last-resort word-level split for sentences with no internal boundary."""
    words = text.split()
    if not words:
        return []
    parts: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        parts.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - overlap_words, start + 1)
    return parts


def _split_long_paragraph(
    text: str, max_words: int, overlap_sentences: int = 1
) -> list[str]:
    """Sentence-boundary split for an over-sized paragraph, with overlap."""
    sentences = _split_sentences(text)
    if not sentences:
        return _split_by_words(text, max_words)

    chunks: list[str] = []
    buf: list[str] = []
    buf_words = 0
    for s in sentences:
        sw = len(s.split())
        if sw >= max_words:
            if buf:
                chunks.append(" ".join(buf))
                buf, buf_words = [], 0
            chunks.extend(_split_by_words(s, max_words))
            continue
        if buf_words + sw > max_words and buf:
            chunks.append(" ".join(buf))
            # Overlap: seed the next chunk with the last N sentences.
            if overlap_sentences > 0:
                tail = _split_sentences(chunks[-1])[-overlap_sentences:]
                buf = list(tail)
                buf_words = sum(len(t.split()) for t in tail)
            else:
                buf, buf_words = [], 0
        buf.append(s)
        buf_words += sw
    if buf:
        chunks.append(" ".join(buf))
    return chunks


def chunk_blocks(
    blocks: list[Block],
    *,
    doc_id: str,
    source: str,
    page_or_slide: int,
    max_words: int = 220,
    overlap_sentences: int = 1,
) -> list[Chunk]:
    """Block-aware chunker.

    Behaviour:
      * Caption / heading blocks → standalone chunks, tagged in
        ``metadata["block_type"]``. They reset the overlap buffer.
      * Paragraph blocks are packed greedily up to ``max_words``.
      * Paragraphs exceeding ``max_words`` are sub-split on sentence
        boundaries (overlap applied between sub-chunks).
      * Successive body chunks share their last ``overlap_sentences``
        sentences across paragraph boundaries too.
    """
    chunks: list[Chunk] = []
    idx = 0

    # `pending` queues paragraph text for the next body chunk.
    # `has_fresh` is True iff pending contains *new* content (not just
    # overlap carried over from the previously-emitted chunk) — we never
    # flush pure overlap as its own chunk.
    pending: list[str] = []
    pending_words = 0
    has_fresh = False

    def emit(text: str, block_type: str) -> None:
        nonlocal idx
        chunks.append(Chunk(
            chunk_id=_make_chunk_id(doc_id, page_or_slide, idx),
            doc_id=doc_id,
            source=source,
            page_or_slide=page_or_slide,
            chunk_index=idx,
            text=text,
            metadata={"block_type": block_type},
        ))
        idx += 1

    def seed_overlap_from(text: str) -> None:
        """After emitting a body chunk, seed pending with overlap sentences."""
        nonlocal pending, pending_words, has_fresh
        pending, pending_words, has_fresh = [], 0, False
        if overlap_sentences <= 0:
            return
        tail = _split_sentences(text)[-overlap_sentences:]
        tail_words = sum(len(s.split()) for s in tail)
        if tail and tail_words < max_words:
            pending = [" ".join(tail)]
            pending_words = tail_words

    def emit_body(text: str) -> None:
        emit(text, "paragraph")
        seed_overlap_from(text)

    def flush_body() -> None:
        if pending and has_fresh:
            emit_body("\n\n".join(pending))

    def reset_pending() -> None:
        nonlocal pending, pending_words, has_fresh
        pending, pending_words, has_fresh = [], 0, False

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        if block.block_type in ("caption", "heading"):
            flush_body()
            reset_pending()
            emit(text, block.block_type)
            continue

        words = len(text.split())
        if words >= max_words:
            # Prepend any overlap from the previous chunk, then sentence-split.
            combined = " ".join([*pending, text]) if pending else text
            reset_pending()
            subs = _split_long_paragraph(combined, max_words, overlap_sentences)
            for i, sub in enumerate(subs):
                if i == len(subs) - 1:
                    emit_body(sub)  # last sub seeds overlap for the next block
                else:
                    emit(sub, "paragraph")
            continue

        if pending_words + words > max_words and has_fresh:
            flush_body()

        pending.append(text)
        pending_words += words
        has_fresh = True

    flush_body()
    return chunks


def chunk_text(
    text: str,
    *,
    doc_id: str,
    source: str,
    page_or_slide: int,
    chunk_size: int = 220,
    overlap: int = 1,
) -> list[Chunk]:
    """Backward-compatible string entry point.

    Splits ``text`` on blank lines into paragraphs and delegates to
    :func:`chunk_blocks`. ``chunk_size`` is in *words*; ``overlap`` is now
    in *sentences* (changed from words, to preserve semantic boundaries).
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        return []

    blocks = [Block(text=p, block_type="paragraph") for p in paragraphs]
    return chunk_blocks(
        blocks,
        doc_id=doc_id,
        source=source,
        page_or_slide=page_or_slide,
        max_words=chunk_size,
        overlap_sentences=overlap,
    )
