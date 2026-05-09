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

# Skill safety boundary — text cleaning is cheap but loading a 1 GB file into
# memory is not.
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw extracted text.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("text_file", nargs="?", help="Path to a text file to clean")
    group.add_argument("--text", help="Raw text string to clean")
    group.add_argument("--stdin", action="store_true", help="Read raw text from stdin")
    parser.add_argument("--output", help="Output file path (default: data/processed/<stem>_cleaned.txt)")
    args = parser.parse_args()

    if args.text:
        raw = args.text
        default_out = Path.cwd() / "data" / "processed" / "cleaned_text.txt"
    elif args.stdin:
        raw = sys.stdin.read()
        default_out = Path.cwd() / "data" / "processed" / "cleaned_text.txt"
    elif args.text_file:
        path = Path(args.text_file)
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
        raw = path.read_text(encoding="utf-8")
        default_out = Path.cwd() / "data" / "processed" / f"{path.stem}_cleaned.txt"
    else:
        parser.print_help()
        sys.exit(1)

    cleaned = clean_text(raw)

    out_path = Path(args.output) if args.output else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cleaned, encoding="utf-8")
    print(f"Output saved to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
