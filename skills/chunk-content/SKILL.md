---
name: chunk-content
description: Split cleaned document text or structured blocks into retrieval-ready chunks with sentence-aware boundaries and overlap. Use this skill when the user asks to chunk text for a RAG pipeline, split a document into segments, or prepare content for vector indexing. Accepts plain text or JSON blocks from parse-pdf/parse-pptx output.
---

## chunk-content

Split document content into overlapping chunks suitable for retrieval (RAG).

### Input modes

**Mode A — plain text file:**

```bash
uv run python skills/chunk-content/scripts/run.py \
  --input <text_file> \
  --doc-id <id> \
  --source <filename>
```

**Mode B — JSON blocks** (output from `parse-pdf` or `parse-pptx`):

```bash
uv run python skills/chunk-content/scripts/run.py \
  --json <parsed_json_file> \
  --doc-id <id>
```

In JSON mode `--source` and page/slide numbers are read from the parsed JSON automatically.

### Output

JSON array of chunks printed to stdout:

```json
[
  {
    "chunk_id": "a8cbb13b...",
    "doc_id": "my_doc",
    "source": "filename.pdf",
    "page_or_slide": 3,
    "chunk_index": 0,
    "text": "...",
    "metadata": { "block_type": "paragraph" }
  }
]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--max-words` | 220 | Target chunk size in words |
| `--overlap` | 1 | Sentences of overlap between consecutive chunks |
| `--pretty` | off | Pretty-print JSON output |

### End-to-end example

```bash
# 1. Parse
uv run python skills/parse-pdf/scripts/run.py data/raw/transformer.pdf > /tmp/parsed.json

# 2. Chunk from parsed JSON
uv run python skills/chunk-content/scripts/run.py \
  --json /tmp/parsed.json \
  --doc-id transformer \
  --pretty
```

### Notes

- Caption and heading blocks are always kept as standalone chunks
- Paragraph blocks are packed greedily up to `--max-words`, then sentence-split
- Runs from the **project root** directory
