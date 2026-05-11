# docpilot — Raydium AI Engineer Take-Home

## Project Context

- **Role applied**: AI Application Engineer at Raydium
- **Candidate**: minzhankuo (GitHub: `minzhankuo-0719`)
- **Repo**: `github.com/minzhankuo-0719/docpilot`

## Assignment Requirements

> Complete the take-home task(s) below by the day before your interview. Please complete at least one task. Completing more than one is a plus.

### Task 1 — Unstructured Data Pipeline & Remote MCP Server

Build a data processing pipeline that ingests simulated, messy enterprise documents (e.g., a multi-page PDF containing tables/headers, and a PPTX slide deck). The script must extract, clean, and appropriately chunk the content. Next, package this searchable knowledge base into a remote Model Context Protocol (MCP) server. Expose specific tools or resources via the MCP server so that a standard LLM agent (e.g., Claude Desktop or a custom agent script) can connect and query the extracted information. Provide verifiable outputs (e.g., an MCP client test script, example queries, or server logs proving successful data retrieval).

### Task 2 — Data Preprocessing as Claude Skills

Package the unstructured data preprocessing capabilities (like parsing PDFs or PPTX files, cleaning text, and structured formatting) into reusable Skills. Ensure that these Skills have clear inputs/outputs, a safe execution boundary, and can be easily installed and invoked by Claude Code. Provide verifiable outputs (e.g., run logs, terminal screenshots, or a recorded demo showing Claude Code successfully executing the Skill). Skills reference (optional): https://kaochenlong.com/claude-code-skills

### Task 3 — Browser automation agent task (**not in scope for this project**)

### Requirements

- **AI-only workflow**: Complete the work using AI coding tools or an agent workflow (Claude Code preferred). Using Skills is a plus.
- **Git evidence**: Provide a repo with meaningful commit history that reflects your process.
- **Deploy online**: Deploy to a public URL (e.g., Zeabur or equivalent).
- **Documentation**: Include a short README with how to run/verify, key assumptions, and how you used the AI/agent workflow.
- **No confidential material**: Use only public or self-created code/data.

## Architecture Decisions

| Item | Decision |
|---|---|
| Scope | Task 1 + Task 2 combined; Task 3 skipped |
| Shared core | `packages/doc_preprocessor` (PDF/PPTX parse, clean, chunk) |
| Language | Python 3.11+ |
| Package manager | `uv` |
| PDF parsing | `pymupdf` |
| PPTX parsing | `python-pptx` |
| MCP framework | FastMCP (official Python SDK) |
| MCP transport | Streamable HTTP |
| Retrieval | Hybrid (BM25 + Voyage AI embeddings), falls back to BM25-only |
| Deployment | **Render** (free tier, Docker) |
| MCP verification | Claude Desktop + custom `mcp_client.py` test script |

## Source Data

- **PDF**: `data/raw/transformer.pdf` — "Attention Is All You Need" (15 pages)
- **PPTX**: `data/raw/transformer_presentation.pptx` — companion slide deck

## Stage Plan

| # | Stage | Output | Verification |
|---|---|---|---|
| 0 | Repo initialisation | Directory structure, `pyproject.toml`, `.gitignore`, GitHub remote | Repo publicly visible |
| 1 | `doc_preprocessor` library | PDF/PPTX parser, cleaner, chunker + unit tests | `pytest` passes |
| 2 | Index build | `chunks.jsonl` + BM25 index | `python scripts/build_index.py` |
| 3 | MCP Server | FastMCP tools: `search`, `get_chunk`, `list_documents` + test client | `python tests/mcp_client.py` returns results |
| 4 | Claude Skills | `parse-pdf`, `parse-pptx`, `clean-text`, `chunk-content` | Invocable from Claude Code |
| 5 | Render deployment | Dockerfile + public URL | URL reachable, MCP tools respond |
| 6 | Demo + docs | Complete README, `docs/AI_WORKFLOW.md` | Fully reproducible |

## Directory Structure

```
raydium-takehome/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── data/
│   ├── raw/
│   └── processed/
├── packages/
│   └── doc_preprocessor/
│       ├── __init__.py
│       ├── pdf.py
│       ├── pptx.py
│       ├── cleaner.py
│       └── chunker.py
├── apps/
│   └── mcp_server/
│       ├── server.py
│       ├── retrieval.py
│       └── Dockerfile
├── skills/
│   ├── parse-pdf/
│   ├── parse-pptx/
│   ├── clean-text/
│   └── chunk-content/
├── scripts/
│   └── build_index.py
├── tests/
│   ├── test_preprocessor.py
│   └── mcp_client.py
└── docs/
    └── AI_WORKFLOW.md
```

## Current Progress

All stages complete. Remote MCP server is live at `https://docpilot-5hht.onrender.com`. `mcp_client.py` passes 5/5 both locally and against the remote deployment.

| Stage | Status | Notes |
|---|---|---|
| 0 — Repo init | ✅ | Directory structure, `pyproject.toml`, `.gitignore`, GitHub remote |
| 1 — `doc_preprocessor` | ✅ | v2: block-level parse + paragraph-aware clean + sentence-aware chunk; `pytest` passes |
| 2 — Index build | ✅ | `chunks.jsonl`, `bm25_index.pkl`, `bm25_corpus.pkl` generated |
| 3 — MCP Server | ✅ | `server.py` + `retrieval.py` verified; `mcp_client.py` 5/5; `Dockerfile` complete |
| 4 — Claude Skills | ✅ | All 4 skills with `SKILL.md` + `scripts/run.py`; installed to `~/.claude/skills/` |
| 5 — Render deploy | ✅ | `https://docpilot-5hht.onrender.com`; remote test 5/5 |
| 6 — Demo + docs | ✅ | README complete; `docs/AI_WORKFLOW.md` stages 2–6 documented |

**doc_preprocessor v2 highlights**:
- `Block` dataclass with `block_type ∈ {paragraph, caption, heading}`
- PDF: PyMuPDF `get_text("blocks")` + regex caption detection (`Figure|Fig|Table`)
- PPTX: title placeholder (`placeholder_format.idx == 0`) tagged as `heading`
- `chunk_blocks`: captions/headings → standalone chunks; paragraphs → sentence-boundary split with one-sentence overlap
- Results: PDF 15 pages → 48 chunks; PPTX → 68 chunks

## Known Issues

| # | Issue | Root cause | Status |
|---|---|---|---|
| B-01 | Visualisation figure text scores high in BM25 | Pages 14–15 embed repeated token strings; BM25 rewards term frequency | Recorded as known limitation in README; Voyage hybrid search mitigates locally |
| B-02 | Figure-embedded tokens parsed as body text | PyMuPDF cannot distinguish figure text from body text | Fixed: `_is_figure_token_noise` drops blocks with >10 lines and <3 words/line average |

## Collaboration Conventions

- Commit + push only after completing a full stage; commit messages must be meaningful
- Briefly explain what a Bash command does and why before running it
- Confirm any architecture-level decisions before changing direction
- `docs/AI_WORKFLOW.md` is the primary AI collaboration record — update it at each stage
