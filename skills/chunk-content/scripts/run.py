"""chunk-content skill — split document text or blocks into retrieval chunks.

Usage:
    # Plain text mode
    uv run python skills/chunk-content/scripts/run.py \
        --input <text_file> --doc-id <id> --source <filename>

    # JSON blocks mode (output from parse-pdf / parse-pptx)
    uv run python skills/chunk-content/scripts/run.py \
        --json <parsed_json_file> --doc-id <id>
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from packages.doc_preprocessor.chunker import chunk_blocks, chunk_text
from packages.doc_preprocessor.pdf import Block


def _chunks_from_text(
    text: str,
    doc_id: str,
    source: str,
    max_words: int,
    overlap: int,
) -> list[dict]:
    chunks = chunk_text(
        text,
        doc_id=doc_id,
        source=source,
        page_or_slide=1,
        chunk_size=max_words,
        overlap=overlap,
    )
    return [asdict(c) for c in chunks]


def _chunks_from_json(
    pages_or_slides: list[dict],
    doc_id: str,
    max_words: int,
    overlap: int,
) -> list[dict]:
    all_chunks = []
    for page in pages_or_slides:
        page_num = page.get("page_num") or page.get("slide_num", 1)
        source = page.get("source", "unknown")
        blocks = [
            Block(text=b["text"], block_type=b["block_type"])
            for b in page.get("blocks", [])
        ]
        if not blocks:
            continue
        chunks = chunk_blocks(
            blocks,
            doc_id=doc_id,
            source=source,
            page_or_slide=page_num,
            max_words=max_words,
            overlap_sentences=overlap,
        )
        all_chunks.extend(asdict(c) for c in chunks)
    return all_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk document content for retrieval.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", metavar="TEXT_FILE", help="Plain text file to chunk")
    input_group.add_argument("--json", metavar="JSON_FILE", help="Parsed JSON from parse-pdf/parse-pptx")
    parser.add_argument("--doc-id", required=True, help="Document identifier (e.g. 'attention')")
    parser.add_argument("--source", help="Source filename (required for --input mode)")
    parser.add_argument("--max-words", type=int, default=220, help="Target chunk size in words")
    parser.add_argument("--overlap", type=int, default=1, help="Sentences of overlap between chunks")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    if args.input:
        if not args.source:
            print("Error: --source is required when using --input", file=sys.stderr)
            sys.exit(1)
        path = Path(args.input)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
        chunks = _chunks_from_text(text, args.doc_id, args.source, args.max_words, args.overlap)

    else:  # --json
        path = Path(args.json)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
        chunks = _chunks_from_json(data, args.doc_id, args.max_words, args.overlap)

    indent = 2 if args.pretty else None
    print(json.dumps(chunks, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
