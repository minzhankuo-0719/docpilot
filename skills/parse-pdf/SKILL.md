---
name: parse-pdf
description: Parse a PDF file into structured blocks (paragraph/caption). Use this skill when the user asks to extract text from a PDF, parse a PDF document, or convert PDF content into structured data. Outputs JSON with pages and block-level content.
---

## parse-pdf

Parse a PDF file into structured pages and blocks using PyMuPDF.

### Input

A path to a PDF file (absolute or relative to project root).

### Output

JSON array printed to stdout. Each element represents one page:

```json
[
  {
    "page_num": 1,
    "source": "filename.pdf",
    "text": "full page text joined by \\n\\n",
    "blocks": [
      { "text": "...", "block_type": "paragraph" },
      { "text": "Figure 1: ...", "block_type": "caption" }
    ]
  }
]
```

`block_type` is one of: `paragraph`, `caption`.

### How to run

```bash
uv run python skills/parse-pdf/scripts/run.py <pdf_path>
```

Example:

```bash
uv run python skills/parse-pdf/scripts/run.py data/raw/transformer.pdf
```

To save to a file:

```bash
uv run python skills/parse-pdf/scripts/run.py data/raw/transformer.pdf > data/processed/parsed_pdf.json
```

### Notes

- Runs from the **project root** directory
- Requires `pymupdf` (already in `pyproject.toml`)
- Image-only pages with no extractable text produce an empty `blocks` list
