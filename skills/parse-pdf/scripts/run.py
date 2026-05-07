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


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a PDF into structured blocks.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    path = Path(args.pdf_path)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
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
    print(json.dumps(output, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
