"""PDF parsing — block-level extraction with caption detection.

Uses PyMuPDF's geometric block detection so that each paragraph stays a
discrete unit. Blocks whose first line matches a figure/table caption
pattern are tagged ``block_type="caption"`` so the chunker can keep them
isolated from body text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import fitz  # pymupdf

BlockType = Literal["paragraph", "caption", "heading"]

# Caption detector. Matches all of:
#   "Figure 1: An illustration"   "Figure 1 An illustration" (no punctuation)
#   "Fig. 2."                     "Table 3: results"
#   "Figure A.1: appendix"        "Figure 1.1: subfigure"   "Figure 1A: variant"
#   "Figure\n1: multiline"        "圖 1：示意圖"   "圖1：示意圖"
# The lookahead `(?=[A-Za-z\d.]*\d)` requires at least one digit in the
# identifier, so paragraphs like "figures and tables show…" don't match.
_CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.?|table|圖|表)\s*"
    r"(?=[A-Za-z\d.]*\d)[A-Za-z\d.]+"
    r"(\s*[:.：。]|\s+\S)",
    re.IGNORECASE,
)

# Numbered section headings: "1 Introduction" (same line) or "1\nIntroduction" (two lines)
_HEADING_NUMBER_RE = re.compile(r"^\d+(\.\d+)*\.?$")

# Heuristic threshold for figure-token noise (B-02). PyMuPDF extracts text
# inside diagrams (e.g. Transformer input figures where each token sits on
# its own line) as long, single-word-per-line blocks. Drop them before they
# pollute body chunks.
FIGURE_NOISE_MIN_LINES = 10
FIGURE_NOISE_MAX_AVG_WORDS = 3.0


def _is_figure_token_noise(text: str) -> bool:
    """Return True if a block looks like figure-internal token spam."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) <= FIGURE_NOISE_MIN_LINES:
        return False
    total_words = sum(len(ln.split()) for ln in lines)
    avg = total_words / len(lines)
    return avg < FIGURE_NOISE_MAX_AVG_WORDS


def _is_sparse_short_block(text: str) -> bool:
    """Return True for single-line blocks with at most one word (e.g. stray page numbers)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) != 1:
        return False
    return len(lines[0].split()) <= 1


@dataclass
class Block:
    """A single layout block (paragraph / caption / heading)."""
    text: str
    block_type: BlockType = "paragraph"
    bbox: tuple[float, float, float, float] | None = None  # (x0, y0, x1, y1)


@dataclass
class ParsedPage:
    page_num: int                       # 1-indexed
    text: str                           # blocks joined by "\n\n" (back-compat)
    source: str                         # filename
    blocks: list[Block] = field(default_factory=list)


def _classify(text: str) -> BlockType:
    if _CAPTION_RE.match(text):
        return "caption"
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if 1 <= len(lines) <= 2:
        # "1\nIntroduction" or "3.1\nEncoder and Decoder Stacks"
        if _HEADING_NUMBER_RE.match(lines[0].strip()):
            return "heading"
    return "paragraph"


def parse_pdf(path: str | Path) -> list[ParsedPage]:
    """Extract text from every page of a PDF, preserving paragraph blocks."""
    path = Path(path)
    source = path.name
    pages: list[ParsedPage] = []

    doc = fitz.open(str(path))
    try:
        for page in doc:
            # PyMuPDF returns: (x0, y0, x1, y1, "text", block_no, block_type)
            # block_type 0 = text, 1 = image. Order is the PDF's natural reading
            # order which already handles multi-column layout reasonably.
            raw_blocks = page.get_text("blocks")

            blocks: list[Block] = []
            for x0, y0, x1, y1, btext, _bno, btype in raw_blocks:
                if btype != 0:
                    continue
                text = btext.strip()
                if not text:
                    continue
                if _is_figure_token_noise(text):
                    continue
                if _is_sparse_short_block(text):
                    continue
                blocks.append(Block(
                    text=text,
                    block_type=_classify(text),
                    bbox=(x0, y0, x1, y1),
                ))

            joined = "\n\n".join(b.text for b in blocks)
            pages.append(ParsedPage(
                page_num=page.number + 1,
                text=joined,
                source=source,
                blocks=blocks,
            ))
    finally:
        doc.close()

    return pages
