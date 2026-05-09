---
name: clean-text
description: Clean raw extracted text by normalising unicode, fixing PDF soft-hyphen line breaks, removing control characters, and collapsing whitespace while preserving paragraph boundaries. Use this skill when the user asks to clean text from a PDF or document, fix encoding issues, or normalise extracted content before further processing.
---

## clean-text

Clean raw extracted text using paragraph-aware normalisation.

### Input

Either:
- A **text file path** — reads the file and cleans its content
- `--text "<string>"` — cleans a string passed directly on the command line
- `--stdin` — reads raw text from stdin

### Output

Cleaned text printed to stdout, with paragraphs preserved (`\n\n` separator).

### How to run

Clean a file:

```bash
uv run python skills/clean-text/scripts/run.py <text_file>
```

Clean an inline string:

```bash
uv run python skills/clean-text/scripts/run.py --text "atten-\ntion mech-\nanism"
```

Clean from stdin (e.g. piped from parse-pdf):

```bash
uv run python skills/parse-pdf/scripts/run.py data/raw/transformer.pdf \
  | python -c "import json,sys; print('\n\n'.join(p['text'] for p in json.load(sys.stdin)))" \
  | uv run python skills/clean-text/scripts/run.py --stdin
```

### What it fixes

| Issue | Before | After |
|---|---|---|
| PDF soft-hyphen line break | `atten-\ntion` | `attention` |
| Internal line wraps | `multi\nline text` | `multi line text` |
| Full-width / ligature chars | `ﬁle` | `file` |
| Repeated spaces | `too  many   spaces` | `too many spaces` |
| Control characters | `\x00\x0b` | _(removed)_ |

Paragraph breaks (`\n\n`) are preserved so downstream chunking still works.

### Notes

- Runs from the **project root** directory
- Input encoding assumed to be UTF-8
