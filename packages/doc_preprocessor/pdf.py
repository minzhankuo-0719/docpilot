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

# "Figure 1:", "Fig. 2.", "Table 3:", plus CJK variants.
_CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.?|table|圖|表)\s*\d+\s*[:.：。]",
    re.IGNORECASE,
)


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
