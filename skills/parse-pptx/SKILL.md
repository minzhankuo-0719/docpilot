---
name: parse-pptx
description: Parse a PPTX file into structured blocks (heading/paragraph). Use this skill when the user asks to extract text from a PowerPoint file, parse a PPTX presentation, or convert slide content into structured data. Outputs JSON with slides and block-level content.
---

## parse-pptx

Parse a PPTX file into structured slides and blocks using python-pptx.

### Input

A path to a PPTX file (absolute or relative to project root).

### Output

JSON array printed to stdout. Each element represents one slide:

```json
[
  {
    "slide_num": 1,
    "source": "filename.pptx",
    "text": "full slide text joined by \\n\\n",
    "blocks": [
      { "text": "Slide Title", "block_type": "heading" },
      { "text": "Body content...", "block_type": "paragraph" }
    ]
  }
]
```

`block_type` is one of: `heading` (title placeholder), `paragraph`.

### How to run

```bash
uv run python skills/parse-pptx/scripts/run.py <pptx_path>
```

Example:

```bash
uv run python skills/parse-pptx/scripts/run.py data/raw/transformer_presentation.pptx
```

To save to a file:

```bash
uv run python skills/parse-pptx/scripts/run.py data/raw/transformer_presentation.pptx > data/processed/parsed_pptx.json
```

### Notes

- Runs from the **project root** directory
- Requires `python-pptx` (already in `pyproject.toml`)
- Slides with no text shapes produce an empty `blocks` list
