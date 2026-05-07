"""Text cleaning — paragraph-aware.

`clean_text` preserves paragraph breaks (``\\n\\n``). Within each paragraph
it removes line-wrap newlines, fixes PDF soft-hyphen line breaks, normalises
unicode and collapses excess whitespace. `clean_block_text` cleans a single
block (no paragraph splitting), suitable for use on `Block.text`.
"""
from __future__ import annotations

import re
import unicodedata


def clean_block_text(text: str) -> str:
    """Clean text *within* a single paragraph/block.

    - NFKC unicode normalisation (full-width → half-width, ligatures)
    - PDF soft-hyphen line breaks: ``"atten-\\ntion"`` → ``"attention"``
    - Internal line wraps (``\\n``) → space
    - Strip control characters except tab/space
    - Collapse runs of spaces
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    """Normalise raw extracted text while preserving paragraph breaks.

    Paragraphs (separated by one or more blank lines) are cleaned
    independently and re-joined with ``\\n\\n``, so downstream chunkers can
    rely on ``\\n\\n`` as a paragraph delimiter.
    """
    if not text:
        return ""
    paragraphs = re.split(r"\n\s*\n+", text)
    cleaned = [clean_block_text(p) for p in paragraphs]
    cleaned = [p for p in cleaned if p]
    return "\n\n".join(cleaned)
