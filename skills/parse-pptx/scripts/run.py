"""parse-pptx skill — extract structured blocks from a PPTX file.

Usage:
    uv run python skills/parse-pptx/scripts/run.py <pptx_path> [--pretty]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from packages.doc_preprocessor.pptx import parse_pptx


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a PPTX into structured blocks.")
    parser.add_argument("pptx_path", help="Path to the PPTX file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    path = Path(args.pptx_path)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    slides = parse_pptx(path)

    output = [
        {
            "slide_num": s.slide_num,
            "source": s.source,
            "text": s.text,
            "blocks": [
                {"text": b.text, "block_type": b.block_type}
                for b in s.blocks
            ],
        }
        for s in slides
    ]

    indent = 2 if args.pretty else None
    print(json.dumps(output, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
