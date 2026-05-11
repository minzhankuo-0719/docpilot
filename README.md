<p align="center">
  <img src="docs/docpilot-logo.png" width="180" alt="docpilot logo"/>
</p>

<h1 align="center">docpilot</h1>

<p align="center">
  <strong>Turn messy enterprise documents into a queryable knowledge base.</strong><br/>
  <em>Unstructured document pipeline · Remote MCP Server · Claude Code Skills</em>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"/></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/package%20manager-uv-DE5FE9" alt="uv"/></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Model%20Context%20Protocol-5e6ad2" alt="MCP"/></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/built%20with-Claude%20Code-D97757" alt="Built with Claude Code"/></a>
  <a href="https://docpilot-5hht.onrender.com"><img src="https://img.shields.io/badge/deploy-Render-46E3B7.svg" alt="Deploy: Render"/></a>
</p>

---

## Assignment

This project completes **Task 1** and **Task 2** from the Raydium AI Engineer take-home:

**Task 1 — Unstructured Data Pipeline & Remote MCP Server**

> Build a data processing pipeline that ingests simulated, messy enterprise documents (e.g., a multi-page PDF containing tables/headers, and a PPTX slide deck). The script must extract, clean, and appropriately chunk the content. Next, package this searchable knowledge base into a remote Model Context Protocol (MCP) server. Expose specific tools or resources via the MCP server so that a standard LLM agent (e.g., Claude Desktop or a custom agent script) can connect and query the extracted information. Provide verifiable outputs (e.g., an MCP client test script, example queries, or server logs proving successful data retrieval).

**Task 2 — Data Preprocessing as Claude Skills**

> Package the unstructured data preprocessing capabilities (like parsing PDFs or PPTX files, cleaning text, and structured formatting) into reusable Skills. Ensure that these Skills have clear inputs/outputs, a safe execution boundary, and can be easily installed and invoked by Claude Code. Provide verifiable outputs (e.g., run logs, terminal screenshots, or a recorded demo showing Claude Code successfully executing the Skill).

---

## Demo & Verification

### Video walkthrough

<!-- TODO: paste Loom / YouTube link here -->
> 📹 [Watch demo](https://...)  *(Task 1: MCP client 5/5 pass · Task 2: Claude Code invoking Skills)*

### MCP Server — remote test (Task 1)

Run the test client against the live Render deployment:

```bash
uv run python tests/mcp_client.py --url https://docpilot-5hht.onrender.com/mcp
```

<!-- TODO: replace with actual screenshot -->
![MCP client 5/5 pass](docs/screenshots/mcp_client_pass.png)

### Claude Code Skills — invocation (Task 2)

<!-- TODO: replace with actual screenshot -->
![Claude Code invoking parse-pdf skill](docs/screenshots/skill_parse_pdf.png)

---

## Task Completion Checklist

### Task 1 — Unstructured Data Pipeline & Remote MCP Server

| Requirement | Status | Evidence |
|---|---|---|
| Ingest messy enterprise documents (PDF + PPTX) | ✅ | `data/raw/transformer.pdf` (15 pages) + `data/raw/transformer_presentation.pptx` |
| Extract, clean, and chunk content | ✅ | `packages/doc_preprocessor/` — block-level parse → paragraph-aware clean → sentence-boundary chunk |
| Searchable knowledge base | ✅ | `data/processed/chunks.jsonl` + BM25 index; hybrid BM25 + Voyage AI when `VOYAGE_API_KEY` is set |
| Remote MCP Server with tools | ✅ | FastMCP server exposing `search`, `get_chunk`, `list_documents` via Streamable HTTP |
| LLM agent can connect and query | ✅ | Claude Desktop connects via `mcp-remote`; custom test client in `tests/mcp_client.py` |
| Verifiable outputs | ✅ | `uv run python tests/mcp_client.py --url https://docpilot-5hht.onrender.com/mcp` — 5/5 tests pass |

### Task 2 — Data Preprocessing as Claude Skills

| Requirement | Status | Evidence |
|---|---|---|
| Reusable Skills for PDF/PPTX parsing, text cleaning, structured formatting | ✅ | `parse-pdf`, `parse-pptx`, `clean-text`, `chunk-content` — four independent skills |
| Clear inputs/outputs | ✅ | Each skill has a `SKILL.md` documenting accepted arguments and output schema |
| Safe execution boundary | ✅ | Each skill enforces `MAX_FILE_SIZE_BYTES` hard-cap validation before processing |
| Easily installed and invoked by Claude Code | ✅ | One `cp -r` per skill to install; invoked by natural language in Claude Code |
| Verifiable outputs | ✅ | Output files written to `data/processed/` on every run |

---

## Getting Started

**Prerequisites:** Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), and optionally a `VOYAGE_API_KEY` (enables hybrid BM25 + Voyage AI search; falls back to pure BM25 without it).

```bash
# 1. Install dependencies (includes dev extras: pytest, ruff)
uv sync --all-extras

# 2. Build the search index
uv run python scripts/build_index.py

# 3. Start the MCP server locally
uv run python apps/mcp_server/server.py
# → http://localhost:8000/mcp

# 4. Run all tests
uv run pytest                          # 56 unit tests
uv run python tests/mcp_client.py      # MCP integration, 5/5
```

**(Optional) Enable hybrid BM25 + Voyage AI search** — create a `.env` file at the repo root containing `VOYAGE_API_KEY=your-key-here`, then prepend `--env-file .env` to the `build_index.py` and `server.py` commands so uv loads the key into the process:

```bash
uv run --env-file .env python scripts/build_index.py
uv run --env-file .env python apps/mcp_server/server.py
```

Without the key, both fall back to BM25-only silently.

**Install Claude Skills** (copy to Claude Code's skills directory):

```bash
cp -r skills/parse-pdf      ~/.claude/skills/
cp -r skills/parse-pptx     ~/.claude/skills/
cp -r skills/clean-text     ~/.claude/skills/
cp -r skills/chunk-content  ~/.claude/skills/
```

After installing, invoke any skill with natural language inside Claude Code — for example:

> "Parse data/raw/transformer.pdf"

Results are auto-saved to `data/processed/` and the output path is printed on completion.

---

## Implementation

### Task 1 — Document Pipeline & MCP Server

The pipeline runs in four stages:

```
Raw Docs (PDF / PPTX)
  → parse   block-level extraction  (paragraph | caption | heading)
  → clean   unicode fix, soft-hyphen repair, paragraph-aware whitespace
  → chunk   sentence-boundary split, caption isolation, sentence-level overlap
  → index   BM25  +  Voyage AI embeddings
                │
                ▼
         FastMCP Server (/mcp)  ←  LLM Agent
```

**Parsing** — PDF uses PyMuPDF `get_text("blocks")` to extract paragraph-level blocks; captions are detected by regex matching `Figure|Fig|Table` plus Chinese `圖|表` and compound identifiers (`Figure A.1`, `Figure 1.1`, `Figure 1A`). PPTX title placeholders (`placeholder_format.idx == 0`) are tagged as `heading`. A noise filter (`_is_figure_token_noise`) drops blocks with >10 lines and <3 words/line average, removing embedded visualisation tokens.

**Chunking** — Captions and headings always become standalone chunks. Body paragraphs are greedily packed up to 220 words, split at sentence boundaries when oversized, and stitched together with one-sentence overlap so context is not lost at chunk boundaries.

**Retrieval** — `KnowledgeBase` in `retrieval.py` enables hybrid search when both `VOYAGE_API_KEY` is set and `embeddings.npy` is present; otherwise it falls back silently to BM25-only. The embeddings file is checked into the repo (whitelisted in `.gitignore`) and shipped in the Docker image, so the remote Render deployment runs in hybrid mode whenever its `VOYAGE_API_KEY` env var is configured.

**MCP tools** exposed via Streamable HTTP:

| Tool | Parameters | Returns |
|---|---|---|
| `search` | `query: str`, `top_k: int = 5` | Ranked chunks with score, text, source, page_or_slide |
| `get_chunk` | `chunk_id: str` | Full chunk record, or `null` if not found |
| `list_documents` | — | Document list with source filename and chunk count |

### Task 2 — Claude Code Skills

Four skills wrap each stage of the preprocessing pipeline:

| Skill | What it does | Output |
|---|---|---|
| `parse-pdf` | Extracts blocks from a PDF | JSON — blocks typed `paragraph` / `caption` |
| `parse-pptx` | Extracts blocks from a PPTX | JSON — blocks typed `heading` / `paragraph` |
| `clean-text` | Cleans raw text (unicode, soft-hyphens, line breaks) | Cleaned text |
| `chunk-content` | Splits blocks into RAG-ready chunks | JSON chunks with overlap |

Each skill enforces a `MAX_FILE_SIZE_BYTES` hard cap before processing and ships with a `SKILL.md` documenting all accepted arguments and the output schema.

The entire project was built using **Claude Code** as the primary coding agent. See [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) for a stage-by-stage log of AI-assisted design decisions, debugging, and verification.

---

## Project Structure

```
docpilot/
├── packages/doc_preprocessor/   core parse / clean / chunk library
│   ├── pdf.py                   PyMuPDF block extractor + noise filter
│   ├── pptx.py                  python-pptx block extractor
│   ├── cleaner.py               paragraph-aware text cleaner
│   └── chunker.py               sentence-boundary chunker
├── apps/mcp_server/
│   ├── server.py                FastMCP tool definitions
│   ├── retrieval.py             KnowledgeBase (BM25 + Voyage AI)
│   └── Dockerfile
├── skills/                      4 Claude Code Skills
│   ├── parse-pdf/
│   ├── parse-pptx/
│   ├── clean-text/
│   └── chunk-content/
├── scripts/
│   ├── build_index.py           builds chunks.jsonl + BM25/embedding index
│   └── demo_pipeline.py         visual pipeline walkthrough → data/processed/demo/
├── tests/
│   ├── test_preprocessor.py     56 unit tests
│   └── mcp_client.py            MCP integration test (5 assertions)
├── data/
│   ├── raw/                     transformer.pdf + transformer_presentation.pptx
│   └── processed/               chunks.jsonl, BM25 index files
└── docs/AI_WORKFLOW.md          stage-by-stage AI collaboration log
```

---

## AI Collaboration Workflow

This entire project was built using **Claude Code** as the primary coding agent — from initial architecture decisions to debugging and deployment. The workflow followed a stage-by-stage structure where each stage was planned, implemented, and verified before moving on.

See [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) for a detailed log covering:
- How each stage was designed in collaboration with the AI agent
- Key design decisions and trade-offs surfaced during development
- Debugging sessions and how issues were diagnosed and resolved
- Verification steps taken at each stage before committing

---

## Future Work

| # | Feature | Description |
|---|---|---|
| T-01 | Table extraction | Use `page.find_tables()` (PyMuPDF ≥ 1.23) to detect table regions and convert them to Markdown, preserving column/row structure as a `table` block type |
| T-02 | Two-column layout fix | Sort blocks by `x0` to detect left/right columns, then merge in correct reading order |
| T-03 | Spatial chunk grouping | Group blocks with similar `y0` coordinates into visual units to avoid merging content across section breaks |
