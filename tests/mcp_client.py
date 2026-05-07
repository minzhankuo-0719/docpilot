"""MCP client test script — verifies the DocPilot MCP server end-to-end.

Usage
-----
  # Start the server first (in a separate terminal):
  cd apps/mcp_server && uv run python server.py

  # Then run this script:
  uv run python tests/mcp_client.py [--url http://localhost:8000/mcp]

The script exercises all three tools and prints a human-readable report.
Exit code 0 = all assertions passed; non-zero = failure.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://localhost:8000/mcp"

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _result_text(result) -> str:
    """Extract text content from a CallToolResult."""
    if not result.content:
        return ""
    parts = []
    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
    return "\n".join(parts)


def _parse_json(result) -> object:
    """Parse tool result.

    FastMCP serialises list return values as multiple TextContent items (one
    per element), and scalar / dict values as a single TextContent.  Handle
    both cases.
    """
    texts = [item.text for item in result.content if hasattr(item, "text")]
    if not texts:
        return None
    if len(texts) == 1:
        return json.loads(texts[0])
    # Multiple items — each is a JSON-encoded element; reassemble as a list.
    return [json.loads(t) for t in texts]


def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗  {msg}")
    sys.exit(1)


# ------------------------------------------------------------------ #
# Test cases                                                          #
# ------------------------------------------------------------------ #

async def test_list_tools(session: ClientSession) -> None:
    print("\n[1] list_tools")
    resp = await session.list_tools()
    names = {t.name for t in resp.tools}
    for expected in ("search", "get_chunk", "list_documents"):
        if expected in names:
            _ok(f"tool '{expected}' present")
        else:
            _fail(f"tool '{expected}' missing — got {names}")


async def test_list_documents(session: ClientSession) -> None:
    print("\n[2] list_documents")
    result = await session.call_tool("list_documents", {})
    docs = _parse_json(result)
    assert isinstance(docs, list) and len(docs) >= 2, f"Expected ≥2 docs, got: {docs}"
    for doc in docs:
        _ok(f"  doc_id={doc['doc_id']}  chunks={doc['chunk_count']}")


async def test_search(session: ClientSession) -> tuple[str, str]:
    """Return (query, top_chunk_id) for use in get_chunk test."""
    print("\n[3] search — query: 'attention mechanism'")
    result = await session.call_tool(
        "search", {"query": "attention mechanism", "top_k": 3}
    )
    hits = _parse_json(result)
    assert isinstance(hits, list) and len(hits) >= 1, f"Expected ≥1 hit, got: {hits}"
    for hit in hits:
        snippet = hit["text"][:80].replace("\n", " ")
        _ok(f"  [{hit['score']:.4f}] {hit['doc_id']}@p{hit['page_or_slide']} — {snippet}…")
    return "attention mechanism", hits[0]["chunk_id"]


async def test_get_chunk(session: ClientSession, chunk_id: str) -> None:
    print(f"\n[4] get_chunk — chunk_id: {chunk_id}")
    result = await session.call_tool("get_chunk", {"chunk_id": chunk_id})
    chunk = _parse_json(result)
    assert chunk is not None, "Expected a chunk, got null"
    assert chunk["chunk_id"] == chunk_id
    _ok(f"  doc_id={chunk['doc_id']}  page_or_slide={chunk['page_or_slide']}")
    _ok(f"  text[:100]: {chunk['text'][:100].replace(chr(10), ' ')}…")


async def test_get_chunk_missing(session: ClientSession) -> None:
    print("\n[5] get_chunk — unknown id (expect null)")
    result = await session.call_tool("get_chunk", {"chunk_id": "does-not-exist"})
    chunk = _parse_json(result)
    assert chunk is None, f"Expected null, got: {chunk}"
    _ok("returned null for unknown chunk_id")


# ------------------------------------------------------------------ #
# Runner                                                              #
# ------------------------------------------------------------------ #

async def run(url: str) -> None:
    print(f"Connecting to {url} …")
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _ok("session initialised")

            await test_list_tools(session)
            await test_list_documents(session)
            _, top_chunk_id = await test_search(session)
            await test_get_chunk(session, top_chunk_id)
            await test_get_chunk_missing(session)

    print("\n✓ All tests passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="DocPilot MCP client test")
    parser.add_argument("--url", default=DEFAULT_URL, help="MCP server URL")
    args = parser.parse_args()
    asyncio.run(run(args.url))


if __name__ == "__main__":
    main()
