"""clean-text skill — normalise raw extracted text.

Usage:
    uv run python skills/clean-text/scripts/run.py <text_file>
    uv run python skills/clean-text/scripts/run.py --text "raw string"
    uv run python skills/clean-text/scripts/run.py --stdin
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from packages.doc_preprocessor.cleaner import clean_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw extracted text.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("text_file", nargs="?", help="Path to a text file to clean")
    group.add_argument("--text", help="Raw text string to clean")
    group.add_argument("--stdin", action="store_true", help="Read raw text from stdin")
    args = parser.parse_args()

    if args.text:
        raw = args.text
    elif args.stdin:
        raw = sys.stdin.read()
    elif args.text_file:
        path = Path(args.text_file)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        raw = path.read_text(encoding="utf-8")
    else:
        parser.print_help()
        sys.exit(1)

    print(clean_text(raw))


if __name__ == "__main__":
    main()
