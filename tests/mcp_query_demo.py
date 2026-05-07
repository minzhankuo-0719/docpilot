"""DocPilot MCP query demo — sends natural-language prompts and saves results.

Usage
-----
  # Server must be running first:
  cd apps/mcp_server && uv run python server.py

  # Then run:
  uv run python tests/mcp_query_demo.py [--url http://localhost:8000/mcp] [--out query_results.txt]
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://localhost:8000/mcp"
DEFAULT_OUT = "data/processed/query_results.md"

QUERIES = [
    "Who are the authors of Attention Is All You Need?",
    "What is the Transformer model architecture?",
    "How does multi-head attention work?",
    "What datasets were used to evaluate the model?",
    "What are the main results and BLEU scores?",
]


def _parse_json(result) -> object:
    texts = [item.text for item in result.content if hasattr(item, "text")]
    if not texts:
        return None
    if len(texts) == 1:
        return json.loads(texts[0])
    return [json.loads(t) for t in texts]


async def run(url: str, out_path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# DocPilot MCP Query Demo")
    lines.append(f"")
    lines.append(f"- **Run at**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Server**: {url}")

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"Connected to {url}")

            for i, query in enumerate(QUERIES, 1):
                print(f"\n[{i}/{len(QUERIES)}] {query}")
                lines.append(f"")
                lines.append(f"---")
                lines.append(f"")
                lines.append(f"## Query {i}: {query}")

                result = await session.call_tool("search", {"query": query, "top_k": 3})
                hits = _parse_json(result)

                if not hits:
                    lines.append("")
                    lines.append("_(no results)_")
                    continue

                for rank, hit in enumerate(hits, 1):
                    lines.append(f"")
                    lines.append(f"### Rank {rank} &nbsp;|&nbsp; score `{hit['score']:.4f}` &nbsp;|&nbsp; `{hit['doc_id']}` p.{hit['page_or_slide']}")
                    lines.append(f"")
                    lines.append(f"**chunk_id**: `{hit['chunk_id']}`")
                    lines.append(f"")
                    lines.append(f"```")
                    lines.append(hit['text'].strip())
                    lines.append(f"```")

    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"_Done._")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="DocPilot MCP query demo")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()
    asyncio.run(run(args.url, Path(args.out)))


if __name__ == "__main__":
    main()
