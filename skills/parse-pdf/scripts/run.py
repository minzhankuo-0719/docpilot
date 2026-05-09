"""parse-pdf skill — extract structured blocks from a PDF file.

Usage:
    uv run python skills/parse-pdf/scripts/run.py <pdf_path> [--pretty]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Allow running from project root
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from packages.doc_preprocessor.pdf import parse_pdf

# Skill safety boundary — keep PyMuPDF from being asked to parse a 1 GB blob.
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a PDF into structured blocks.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output", help="Output file path (default: data/processed/<stem>_parsed.json)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    path = Path(args.pdf_path)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        print(
            f"Error: {path} is {size} bytes; max allowed is {MAX_FILE_SIZE_BYTES}.",
            file=sys.stderr,
        )
        sys.exit(1)

    pages = parse_pdf(path)

    output = [
        {
            "page_num": p.page_num,
            "source": p.source,
            "text": p.text,
            "blocks": [
                {"text": b.text, "block_type": b.block_type}
                for b in p.blocks
            ],
        }
        for p in pages
    ]

    indent = 2 if args.pretty else None
    json_str = json.dumps(output, ensure_ascii=False, indent=indent)

    out_path = Path(args.output) if args.output else Path.cwd() / "data" / "processed" / f"{path.stem}_parsed.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json_str, encoding="utf-8")
    print(f"Output saved to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
