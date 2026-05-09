"""
demo_pipeline.py — 視覺化展示 doc_preprocessor 各階段輸出

執行後會在 data/processed/demo/ 產生：
  parse_pdf.md       — 每頁解析出的 Block 列表（含 paragraph / caption / heading 標記）
  parse_pptx.md      — 每張投影片的 Block 列表
  clean_pdf.md       — 清洗後的段落（保留段落界線）
  clean_pptx.md      — 清洗後的投影片段落
  chunks_pdf.md      — PDF 切塊結果（caption / heading 獨立成 chunk）
  chunks_pptx.md     — PPTX 切塊結果
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from doc_preprocessor import (  # noqa: E402
    Block,
    Chunk,
    ParsedPage,
    ParsedSlide,
    chunk_blocks,
    clean_block_text,
    parse_pdf,
    parse_pptx,
)

RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed" / "demo"
PDF_PATH = RAW_DIR / "transformer.pdf"
PPTX_PATH = RAW_DIR / "transformer_presentation.pptx"

# Visual badges so reviewers can see block_type at a glance.
_TYPE_BADGE = {
    "paragraph": "📝 paragraph",
    "caption":   "🖼️  caption",
    "heading":   "📌 heading",
}

CHUNK_MAX_WORDS = 220
CHUNK_OVERLAP_SENTENCES = 1


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _badge(block_type: str) -> str:
    return _TYPE_BADGE.get(block_type, block_type)


def write_parse_pdf(pages: list[ParsedPage], out: Path) -> None:
    total_blocks = sum(len(p.blocks) for p in pages)
    captions = sum(1 for p in pages for b in p.blocks if b.block_type == "caption")
    lines = [
        "# Parse PDF — Block-level 解析結果\n",
        f"> 來源：`{PDF_PATH.name}`　共 **{len(pages)}** 頁　"
        f"**{total_blocks}** 個 block（其中 **{captions}** 個 caption）\n",
        "> 每個 block 標註類型：📝 paragraph / 🖼️  caption / 📌 heading\n",
    ]
    for p in pages:
        lines.append(f"## 第 {p.page_num} 頁　({len(p.blocks)} blocks)\n")
        if not p.blocks:
            lines.append("_(此頁無文字)_\n")
            continue
        for i, b in enumerate(p.blocks, 1):
            lines.append(f"### Block {i} — {_badge(b.block_type)}\n")
            lines.append("```")
            lines.append(b.text)
            lines.append("```\n")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {out.relative_to(ROOT)}  ({total_blocks} blocks, {captions} captions)")


def write_parse_pptx(slides: list[ParsedSlide], out: Path) -> None:
    total_blocks = sum(len(s.blocks) for s in slides)
    headings = sum(1 for s in slides for b in s.blocks if b.block_type == "heading")
    lines = [
        "# Parse PPTX — Block-level 解析結果\n",
        f"> 來源：`{PPTX_PATH.name}`　共 **{len(slides)}** 張投影片　"
        f"**{total_blocks}** 個 block（其中 **{headings}** 個 heading）\n",
    ]
    for s in slides:
        lines.append(f"## 投影片 {s.slide_num}　({len(s.blocks)} blocks)\n")
        if not s.blocks:
            lines.append("_(此張無文字)_\n")
            continue
        for i, b in enumerate(s.blocks, 1):
            lines.append(f"### Block {i} — {_badge(b.block_type)}\n")
            lines.append("```")
            lines.append(b.text)
            lines.append("```\n")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {out.relative_to(ROOT)}  ({total_blocks} blocks, {headings} headings)")


def write_clean(
    items: list[ParsedPage] | list[ParsedSlide],
    out: Path,
    label: str,
    source_name: str,
) -> list[list[Block]]:
    """Clean each block; return cleaned blocks per page/slide for chunking."""
    cleaned_per_unit: list[list[Block]] = []
    lines = [
        f"# Clean {label} — 段落感知清洗結果\n",
        f"> 來源：`{source_name}`\n",
        "> 每個 block 獨立清洗：合字號斷字 / 行內換行→空白 / unicode 正規化 / "
        "壓縮多餘空白；段落界線保留\n",
    ]
    for item in items:
        num = getattr(item, "page_num", None) or item.slide_num  # type: ignore[union-attr]
        unit = "頁" if isinstance(item, ParsedPage) else "張投影片"
        cleaned_blocks: list[Block] = []
        diff_total = 0
        for b in item.blocks:
            new_text = clean_block_text(b.text)
            diff_total += len(b.text) - len(new_text)
            if new_text:
                cleaned_blocks.append(replace(b, text=new_text))
        cleaned_per_unit.append(cleaned_blocks)

        lines.append(
            f"## 第 {num} {unit}　({len(cleaned_blocks)} blocks，"
            f"清洗掉 {diff_total} 字元)\n"
        )
        if not cleaned_blocks:
            lines.append("_(清洗後無文字)_\n")
            continue
        for i, b in enumerate(cleaned_blocks, 1):
            lines.append(f"### Block {i} — {_badge(b.block_type)}\n")
            lines.append("```")
            lines.append(b.text)
            lines.append("```\n")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {out.relative_to(ROOT)}")
    return cleaned_per_unit


def write_chunks(
    cleaned_per_unit: list[list[Block]],
    doc_id: str,
    source_name: str,
    out: Path,
    label: str,
) -> None:
    all_chunks: list[Chunk] = []
    for unit_idx, blocks in enumerate(cleaned_per_unit, start=1):
        all_chunks.extend(chunk_blocks(
            blocks,
            doc_id=doc_id,
            source=source_name,
            page_or_slide=unit_idx,
            max_words=CHUNK_MAX_WORDS,
            overlap_sentences=CHUNK_OVERLAP_SENTENCES,
        ))

    by_type: dict[str, int] = {}
    for c in all_chunks:
        t = c.metadata.get("block_type", "?")
        by_type[t] = by_type.get(t, 0) + 1
    type_summary = "，".join(f"{k}={v}" for k, v in by_type.items())

    unit_word = "頁" if "pdf" in doc_id else "張"
    lines = [
        f"# Chunks {label} — 切塊結果\n",
        f"> 來源：`{source_name}`　共 **{len(all_chunks)}** 個 chunk　"
        f"({type_summary})\n",
        f"> 參數：max_words={CHUNK_MAX_WORDS}，overlap_sentences={CHUNK_OVERLAP_SENTENCES}\n",
        "> 重點：caption / heading 獨立成 chunk，不會混入內文段落\n",
    ]
    for c in all_chunks:
        block_type = c.metadata.get("block_type", "paragraph")
        lines.append(
            f"## [{c.chunk_id}]　第 {c.page_or_slide} {unit_word}　"
            f"chunk #{c.chunk_index}　— {_badge(block_type)}\n"
        )
        lines.append(
            f"- **字數**：{len(c.text.split())} words　"
            f"| **doc_id**：`{c.doc_id}`　"
            f"| **source**：`{c.source}`\n"
        )
        lines.append("```")
        lines.append(c.text)
        lines.append("```\n")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {out.relative_to(ROOT)}  ({len(all_chunks)} chunks; {type_summary})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not PDF_PATH.exists():
        print(f"[SKIP] PDF 不存在：{PDF_PATH}")
    else:
        print("\n[1/6] 解析 PDF…")
        pdf_pages = parse_pdf(PDF_PATH)
        write_parse_pdf(pdf_pages, OUT_DIR / "parse_pdf.md")

        print("[2/6] 清洗 PDF…")
        pdf_cleaned = write_clean(
            pdf_pages, OUT_DIR / "clean_pdf.md", "PDF", PDF_PATH.name
        )

        print("[3/6] 切塊 PDF…")
        write_chunks(
            pdf_cleaned, doc_id="attention_pdf",
            source_name=PDF_PATH.name,
            out=OUT_DIR / "chunks_pdf.md",
            label="PDF",
        )

    if not PPTX_PATH.exists():
        print(f"[SKIP] PPTX 不存在：{PPTX_PATH}")
    else:
        print("\n[4/6] 解析 PPTX…")
        pptx_slides = parse_pptx(PPTX_PATH)
        write_parse_pptx(pptx_slides, OUT_DIR / "parse_pptx.md")

        print("[5/6] 清洗 PPTX…")
        pptx_cleaned = write_clean(
            pptx_slides, OUT_DIR / "clean_pptx.md", "PPTX", PPTX_PATH.name
        )

        print("[6/6] 切塊 PPTX…")
        write_chunks(
            pptx_cleaned, doc_id="attention_pptx",
            source_name=PPTX_PATH.name,
            out=OUT_DIR / "chunks_pptx.md",
            label="PPTX",
        )

    print(f"\n完成！輸出目錄：{OUT_DIR.relative_to(ROOT)}/\n")


if __name__ == "__main__":
    main()
