from dataclasses import dataclass
from pathlib import Path

import fitz  # pymupdf


@dataclass
class ParsedPage:
    page_num: int   # 1-indexed
    text: str
    source: str     # filename


def parse_pdf(path: str | Path) -> list[ParsedPage]:
    """Extract text from every page of a PDF."""
    path = Path(path)
    source = path.name
    pages: list[ParsedPage] = []

    doc = fitz.open(str(path))
    try:
        for page in doc:
            text = page.get_text("text")
            pages.append(ParsedPage(
                page_num=page.number + 1,
                text=text,
                source=source,
            ))
    finally:
        doc.close()

    return pages
