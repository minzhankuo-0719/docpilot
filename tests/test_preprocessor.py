"""Unit tests for doc_preprocessor.

Integration tests use the sample files committed to data/raw/.
"""
from pathlib import Path

import pytest

from doc_preprocessor import (
    Block,
    Chunk,
    ParsedPage,
    ParsedSlide,
    chunk_blocks,
    chunk_text,
    clean_block_text,
    clean_text,
    parse_pdf,
    parse_pptx,
)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PDF_PATH = RAW_DIR / "attention.pdf"
PPTX_PATH = RAW_DIR / "attention_presentation.pptx"


# ---------------------------------------------------------------------------
# cleaner
# ---------------------------------------------------------------------------

class TestCleanBlockText:
    def test_removes_soft_hyphen_linebreak(self):
        assert clean_block_text("atten-\ntion") == "attention"

    def test_collapses_internal_newlines_to_space(self):
        assert clean_block_text("hello\nworld") == "hello world"

    def test_collapses_spaces(self):
        assert clean_block_text("a  b   c") == "a b c"

    def test_normalises_unicode(self):
        assert clean_block_text("ｈｅｌｌｏ") == "hello"

    def test_strips_leading_trailing(self):
        assert clean_block_text("  hi  ") == "hi"

    def test_empty_string(self):
        assert clean_block_text("") == ""


class TestCleanText:
    def test_preserves_paragraph_break(self):
        # Blank-line paragraph break must survive cleaning.
        assert clean_text("hello\n\nworld") == "hello\n\nworld"

    def test_collapses_within_paragraph_newlines(self):
        # Single newline = line wrap inside a paragraph → space.
        assert clean_text("hello\nworld") == "hello world"

    def test_cleans_each_paragraph(self):
        out = clean_text("atten-\ntion is\n\nall  you  need")
        assert out == "attention is\n\nall you need"

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_drops_empty_paragraphs(self):
        assert clean_text("a\n\n\n\nb") == "a\n\nb"


# ---------------------------------------------------------------------------
# chunker — string entry point (back-compat)
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_short_text_single_chunk(self):
        chunks = chunk_text(
            "A short sentence.", doc_id="d1", source="t.txt", page_or_slide=1
        )
        assert len(chunks) == 1
        assert isinstance(chunks[0], Chunk)

    def test_paragraphs_packed_into_one_chunk_when_small(self):
        text = "Paragraph one is short.\n\nParagraph two is also short."
        chunks = chunk_text(text, doc_id="d1", source="t", page_or_slide=1)
        assert len(chunks) == 1
        assert "Paragraph one" in chunks[0].text
        assert "Paragraph two" in chunks[0].text

    def test_long_text_splits_on_sentence_boundary(self):
        text = ". ".join("alpha beta gamma delta epsilon" for _ in range(80)) + "."
        chunks = chunk_text(
            text, doc_id="d1", source="t", page_or_slide=1, chunk_size=120,
        )
        assert len(chunks) > 1

    def test_chunk_ids_are_unique(self):
        text = ". ".join(f"sentence number {i}" for i in range(200)) + "."
        chunks = chunk_text(
            text, doc_id="d1", source="t", page_or_slide=1, chunk_size=80,
        )
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_empty_text_returns_empty(self):
        assert chunk_text("", doc_id="d1", source="f", page_or_slide=1) == []

    def test_metadata_carries_block_type(self):
        chunks = chunk_text("hello world", doc_id="d1", source="f", page_or_slide=1)
        assert chunks[0].metadata.get("block_type") == "paragraph"


# ---------------------------------------------------------------------------
# chunker — block-aware entry point (the real story)
# ---------------------------------------------------------------------------

class TestChunkBlocks:
    def test_caption_isolated_from_body(self):
        blocks = [
            Block(text="Body paragraph one talks about transformers.", block_type="paragraph"),
            Block(text="Figure 1: An illustration of attention.", block_type="caption"),
            Block(text="Body paragraph two continues the discussion.", block_type="paragraph"),
        ]
        chunks = chunk_blocks(blocks, doc_id="d1", source="f", page_or_slide=1)
        captions = [c for c in chunks if c.metadata.get("block_type") == "caption"]
        bodies = [c for c in chunks if c.metadata.get("block_type") == "paragraph"]

        assert len(captions) == 1
        assert "Figure 1" in captions[0].text
        # Caption text must not bleed into body chunks.
        for c in bodies:
            assert "Figure 1" not in c.text

    def test_heading_is_standalone(self):
        blocks = [
            Block(text="Introduction", block_type="heading"),
            Block(text="Body text follows the heading.", block_type="paragraph"),
        ]
        chunks = chunk_blocks(blocks, doc_id="d1", source="f", page_or_slide=1)
        assert chunks[0].metadata["block_type"] == "heading"
        assert chunks[0].text == "Introduction"

    def test_packs_small_paragraphs(self):
        blocks = [
            Block(text=f"Tiny paragraph {i}.", block_type="paragraph")
            for i in range(5)
        ]
        chunks = chunk_blocks(
            blocks, doc_id="d1", source="f", page_or_slide=1, max_words=200,
        )
        assert len(chunks) == 1
        # Paragraph break preserved inside the packed chunk.
        assert "\n\n" in chunks[0].text

    def test_oversize_paragraph_split_on_sentences(self):
        big = ". ".join(["alpha beta gamma delta epsilon zeta eta theta"] * 60) + "."
        blocks = [Block(text=big, block_type="paragraph")]
        chunks = chunk_blocks(
            blocks, doc_id="d1", source="f", page_or_slide=1, max_words=80,
        )
        assert len(chunks) > 1
        # Each chunk should end at a sentence boundary (period).
        for c in chunks[:-1]:
            assert c.text.rstrip().endswith(".")

    def test_overlap_carries_last_sentence(self):
        # Two paragraphs each big enough to force a flush between them.
        para1 = ". ".join([f"first sentence {i}" for i in range(40)]) + "."
        para2 = ". ".join([f"second sentence {i}" for i in range(40)]) + "."
        blocks = [
            Block(text=para1, block_type="paragraph"),
            Block(text=para2, block_type="paragraph"),
        ]
        chunks = chunk_blocks(
            blocks, doc_id="d1", source="f", page_or_slide=1,
            max_words=120, overlap_sentences=1,
        )
        assert len(chunks) >= 2
        # Successive body chunks should share at least one sentence at the seam.
        for prev, curr in zip(chunks, chunks[1:]):
            if (
                prev.metadata.get("block_type") == "paragraph"
                and curr.metadata.get("block_type") == "paragraph"
            ):
                last_sent = prev.text.rstrip(".").split(".")[-1].strip()
                if last_sent:
                    assert last_sent in curr.text


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

    def test_pages_have_blocks(self):
        pages = parse_pdf(PDF_PATH)
        assert all(p.blocks for p in pages if p.text.strip())

    def test_blocks_have_bbox(self):
        pages = parse_pdf(PDF_PATH)
        first = next(b for p in pages for b in p.blocks)
        assert first.bbox is not None and len(first.bbox) == 4

    def test_caption_detected_on_attention_paper(self):
        # The Attention paper has Figure 1, Figure 2, Table 1, etc.
        pages = parse_pdf(PDF_PATH)
        captions = [b for p in pages for b in p.blocks if b.block_type == "caption"]
        assert len(captions) >= 2
        assert any(c.text.lower().startswith(("figure", "table", "fig")) for c in captions)

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

    def test_slides_have_blocks(self):
        slides = parse_pptx(PPTX_PATH)
        assert any(s.blocks for s in slides)

    def test_at_least_one_heading_present(self):
        # Any well-formed deck has at least one title slide.
        slides = parse_pptx(PPTX_PATH)
        headings = [b for s in slides for b in s.blocks if b.block_type == "heading"]
        assert len(headings) >= 1

    def test_slide_numbering(self):
        slides = parse_pptx(PPTX_PATH)
        assert slides[0].slide_num == 1

    def test_source_is_filename(self):
        slides = parse_pptx(PPTX_PATH)
        assert slides[0].source == "attention_presentation.pptx"
