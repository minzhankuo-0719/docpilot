"""DocPilot MCP Server — exposes knowledge base tools over Streamable HTTP.

Tools
-----
  search(query, top_k=5)    — BM25 (or hybrid if VOYAGE_API_KEY is set)
  get_chunk(chunk_id)       — fetch one chunk by ID
  list_documents()          — list indexed source documents

Transport
---------
  Streamable HTTP at  /mcp   (default FastMCP path)
  Bind host/port from HOST / PORT env vars (defaults: 0.0.0.0 / 8000).
"""
from __future__ import annotations

import base64
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, AsyncIterator

SERVER_DIR = Path(__file__).parent
ROOT = SERVER_DIR.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVER_DIR))  # so `from retrieval import kb` always resolves

from mcp.server.fastmcp import FastMCP
from mcp.types import Icon

from retrieval import kb  # relative import — server is run from its own dir


def _icon_data_uri() -> str | None:
    """Read bundled icon.png and return it as a base64 data URI, or None if absent."""
    icon_path = SERVER_DIR / "icon.png"
    if not icon_path.exists():
        return None
    encoded = base64.b64encode(icon_path.read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"

# Guardrails for the public search() tool. Tight enough that an over-eager
# agent can't blow through the free-tier instance, generous enough to cover
# every realistic natural-language query.
MAX_QUERY_CHARS = 500
MAX_TOP_K = 20

# ------------------------------------------------------------------ #
# Lifespan: load index once at startup                                #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[None]:
    kb.load()
    yield


# ------------------------------------------------------------------ #
# Server instance                                                     #
# ------------------------------------------------------------------ #

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

_icon_uri = _icon_data_uri()
_icons = [Icon(src=_icon_uri, mimeType="image/png", sizes=["128x128"])] if _icon_uri else None

mcp = FastMCP(
    name="docpilot",
    instructions=(
        "Knowledge base built from the 'Attention Is All You Need' paper and its "
        "slide deck.  Use `search` to find relevant passages, `get_chunk` to retrieve "
        "a specific chunk by ID, and `list_documents` to see what is available."
    ),
    website_url="https://github.com/minzhankuo-0719/docpilot",
    icons=_icons,
    host=HOST,
    port=PORT,
    lifespan=_lifespan,
)


# ------------------------------------------------------------------ #
# Tools                                                               #
# ------------------------------------------------------------------ #

@mcp.tool(description="Search the knowledge base with a natural-language query.")
def search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return the top-k most relevant chunks for *query*.

    Each result includes chunk_id, doc_id, source, page_or_slide, text, score,
    and metadata (block_type).
    """
    query = (query or "").strip()[:MAX_QUERY_CHARS]
    if not query:
        return []
    top_k = max(1, min(int(top_k), MAX_TOP_K))
    results = kb.search(query, top_k=top_k)
    return [asdict(r) for r in results]


@mcp.tool(description="Retrieve a single chunk by its chunk_id.")
def get_chunk(chunk_id: str) -> dict[str, Any] | None:
    """Return the full chunk record for *chunk_id*, or null if not found."""
    return kb.get_chunk(chunk_id)


@mcp.tool(description="List all indexed source documents.")
def list_documents() -> list[dict[str, Any]]:
    """Return a summary of each document: doc_id, source filename, chunk count."""
    return kb.list_documents()


# ------------------------------------------------------------------ #
# Entry point                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
