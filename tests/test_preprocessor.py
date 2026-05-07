"""Unit tests for doc_preprocessor.

Integration tests use the sample files committed to data/raw/.
"""
from pathlib import Path

import pytest

from doc_preprocessor import (
    Chunk,
    ParsedPage,
    ParsedSlide,
    clean_text,
    chunk_text,
    parse_pdf,
    parse_pptx,
)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PDF_PATH = RAW_DIR / "attention.pdf"
PPTX_PATH = RAW_DIR / "attention_presentation.pptx"


# ---------------------------------------------------------------------------
# cleaner
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_removes_soft_hyphen_linebreak(self):
        assert clean_text("atten-\ntion") == "attention"

    def test_collapses_newlines(self):
        assert clean_text("hello\n\nworld") == "hello world"

    def test_collapses_spaces(self):
        assert clean_text("a  b   c") == "a b c"

    def test_normalises_unicode(self):
        # Full-width ASCII → half-width
        assert clean_text("ｈｅｌｌｏ") == "hello"

    def test_strips_leading_trailing(self):
        assert clean_text("  hi  ") == "hi"

    def test_empty_string(self):
        assert clean_text("") == ""


# ---------------------------------------------------------------------------
# chunker
# ---------------------------------------------------------------------------

class TestChunkText:
    def _make_words(self, n: int) -> str:
        return " ".join(f"word{i}" for i in range(n))

    def test_short_text_single_chunk(self):
        text = self._make_words(10)
        chunks = chunk_text(text, doc_id="d1", source="test.txt", page_or_slide=1)
        assert len(chunks) == 1
        assert isinstance(chunks[0], Chunk)

    def test_long_text_multiple_chunks(self):
        text = self._make_words(1000)
        chunks = chunk_text(
            text, doc_id="d1", source="test.txt", page_or_slide=1,
            chunk_size=400, overlap=50,
        )
        assert len(chunks) > 1

    def test_chunk_ids_are_unique(self):
        text = self._make_words(1000)
        chunks = chunk_text(text, doc_id="d1", source="test.txt", page_or_slide=1)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_overlap_content(self):
        text = self._make_words(500)
        chunks = chunk_text(
            text, doc_id="d1", source="test.txt", page_or_slide=1,
            chunk_size=400, overlap=50,
        )
        if len(chunks) >= 2:
            tail_words = set(chunks[0].text.split()[-50:])
            head_words = set(chunks[1].text.split()[:50])
            assert tail_words == head_words

    def test_empty_text_returns_empty(self):
        assert chunk_text("", doc_id="d1", source="f", page_or_slide=1) == []

    def test_metadata_field_exists(self):
        chunks = chunk_text("hello world", doc_id="d1", source="f", page_or_slide=1)
        assert chunks[0].metadata == {}


# ---------------------------------------------------------------------------
# PDF parser (integration — requires data/raw/attention.pdf)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not PDF_PATH.exists(), reason="attention.pdf not in data/raw")
class TestParsePdf:
    def test_returns_pages(self):
        pages = parse_pdf(PDF_PATH)
        assert len(pages) > 0

    def test_page_type(self):
        pages = parse_pdf(PDF_PATH)
        assert all(isinstance(p, ParsedPage) for p in pages)

    def test_pages_have_text(self):
        pages = parse_pdf(PDF_PATH)
        assert any(p.text.strip() for p in pages)

    def test_page_numbering(self):
        pages = parse_pdf(PDF_PATH)
        assert pages[0].page_num == 1
        assert pages[-1].page_num == len(pages)

    def test_source_is_filename(self):
        pages = parse_pdf(PDF_PATH)
        assert pages[0].source == "attention.pdf"


# ---------------------------------------------------------------------------
# PPTX parser (integration — requires data/raw/attention_presentation.pptx)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not PPTX_PATH.exists(), reason="attention_presentation.pptx not in data/raw")
class TestParsePptx:
    def test_returns_slides(self):
        slides = parse_pptx(PPTX_PATH)
        assert len(slides) > 0

    def test_slide_type(self):
        slides = parse_pptx(PPTX_PATH)
        assert all(isinstance(s, ParsedSlide) for s in slides)

    def test_slides_have_text(self):
        slides = parse_pptx(PPTX_PATH)
        assert any(s.text.strip() for s in slides)

    def test_slide_numbering(self):
        slides = parse_pptx(PPTX_PATH)
        assert slides[0].slide_num == 1

    def test_source_is_filename(self):
        slides = parse_pptx(PPTX_PATH)
        assert slides[0].source == "attention_presentation.pptx"
