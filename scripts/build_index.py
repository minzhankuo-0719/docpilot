"""Build searchable index from raw documents.

Reads
-----
  data/raw/attention.pdf
  data/raw/attention_presentation.pptx

Writes
------
  data/processed/chunks.jsonl          one JSON object per chunk
  data/processed/bm25_index.pkl        serialised BM25Okapi instance
  data/processed/bm25_corpus.pkl       tokenised corpus (parallel to chunks)
  data/processed/embeddings.npy        Voyage AI embeddings  (requires VOYAGE_API_KEY)
  data/processed/embedding_ids.json    chunk_id list parallel to embeddings
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from packages.doc_preprocessor import (
    Chunk,
    clean_block_text,
    chunk_blocks,
    parse_pdf,
    parse_pptx,
)

PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = ROOT / "data" / "raw" / "attention.pdf"
PPTX_PATH = ROOT / "data" / "raw" / "attention_presentation.pptx"

# BM25 tokeniser: lowercase + whitespace split; fast, no NLTK dependency.
def _tokenise(text: str) -> list[str]:
    return text.lower().split()


def _build_pdf_chunks() -> list[Chunk]:
    print(f"[PDF] parsing {PDF_PATH.name} …")
    pages = parse_pdf(PDF_PATH)
    chunks: list[Chunk] = []
    doc_id = PDF_PATH.stem  # "attention"
    for page in pages:
        cleaned_blocks = []
        for block in page.blocks:
            cleaned = block.__class__(
                text=clean_block_text(block.text),
                block_type=block.block_type,
                bbox=block.bbox,
            )
            cleaned_blocks.append(cleaned)
        page_chunks = chunk_blocks(
            cleaned_blocks,
            doc_id=doc_id,
            source=page.source,
            page_or_slide=page.page_num,
        )
        chunks.extend(page_chunks)
    print(f"[PDF] {len(pages)} pages → {len(chunks)} chunks")
    return chunks


def _build_pptx_chunks() -> list[Chunk]:
    print(f"[PPTX] parsing {PPTX_PATH.name} …")
    slides = parse_pptx(PPTX_PATH)
    chunks: list[Chunk] = []
    doc_id = PPTX_PATH.stem  # "attention_presentation"
    for slide in slides:
        cleaned_blocks = []
        for block in slide.blocks:
            cleaned = block.__class__(
                text=clean_block_text(block.text),
                block_type=block.block_type,
            )
            cleaned_blocks.append(cleaned)
        slide_chunks = chunk_blocks(
            cleaned_blocks,
            doc_id=doc_id,
            source=slide.source,
            page_or_slide=slide.slide_num,
        )
        chunks.extend(slide_chunks)
    print(f"[PPTX] {len(slides)} slides → {len(chunks)} chunks")
    return chunks


def _save_chunks_jsonl(chunks: list[Chunk], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    print(f"[JSONL] wrote {len(chunks)} chunks → {path.relative_to(ROOT)}")


def _build_bm25(chunks: list[Chunk]) -> None:
    from rank_bm25 import BM25Okapi

    corpus = [_tokenise(c.text) for c in chunks]
    index = BM25Okapi(corpus)

    index_path = PROCESSED_DIR / "bm25_index.pkl"
    corpus_path = PROCESSED_DIR / "bm25_corpus.pkl"

    with index_path.open("wb") as fh:
        pickle.dump(index, fh)
    with corpus_path.open("wb") as fh:
        pickle.dump(corpus, fh)

    print(f"[BM25] index saved → {index_path.relative_to(ROOT)}")
    print(f"[BM25] corpus saved → {corpus_path.relative_to(ROOT)}")


def _build_voyage_embeddings(chunks: list[Chunk]) -> None:
    api_key = os.environ.get("VOYAGE_API_KEY", "")
    if not api_key:
        print("[Voyage] VOYAGE_API_KEY not set — skipping embedding index")
        return

    try:
        import voyageai
        import numpy as np
    except ImportError:
        print("[Voyage] voyageai / numpy not installed — skipping")
        return

    print(f"[Voyage] embedding {len(chunks)} chunks with voyage-3-lite …")
    client = voyageai.Client(api_key=api_key)

    # Voyage API accepts up to 128 texts per call.
    BATCH = 128
    all_embeddings: list[list[float]] = []
    for start in range(0, len(chunks), BATCH):
        batch = chunks[start : start + BATCH]
        result = client.embed(
            [c.text for c in batch],
            model="voyage-3-lite",
            input_type="document",
        )
        all_embeddings.extend(result.embeddings)
        print(f"[Voyage]   embedded {min(start + BATCH, len(chunks))}/{len(chunks)}")

    import numpy as np
    emb_array = np.array(all_embeddings, dtype=np.float32)
    ids = [c.chunk_id for c in chunks]

    emb_path = PROCESSED_DIR / "embeddings.npy"
    ids_path = PROCESSED_DIR / "embedding_ids.json"

    np.save(str(emb_path), emb_array)
    with ids_path.open("w", encoding="utf-8") as fh:
        json.dump(ids, fh)

    print(f"[Voyage] embeddings {emb_array.shape} saved → {emb_path.relative_to(ROOT)}")
    print(f"[Voyage] ids saved → {ids_path.relative_to(ROOT)}")


def main() -> None:
    all_chunks: list[Chunk] = []
    all_chunks.extend(_build_pdf_chunks())
    all_chunks.extend(_build_pptx_chunks())

    jsonl_path = PROCESSED_DIR / "chunks.jsonl"
    _save_chunks_jsonl(all_chunks, jsonl_path)
    _build_bm25(all_chunks)
    _build_voyage_embeddings(all_chunks)

    print(f"\n✓ Stage 2 complete — {len(all_chunks)} total chunks indexed")


if __name__ == "__main__":
    main()
