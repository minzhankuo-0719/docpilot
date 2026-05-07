FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifests first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install all runtime dependencies (no dev extras)
RUN uv pip install --system --no-cache \
    pymupdf \
    python-pptx \
    "mcp[cli]" \
    rank-bm25 \
    voyageai \
    httpx \
    python-dotenv \
    numpy

# Copy source
COPY packages/ ./packages/
COPY apps/mcp_server/ ./apps/mcp_server/
COPY data/processed/chunks.jsonl ./data/processed/chunks.jsonl
COPY data/processed/bm25_index.pkl ./data/processed/bm25_index.pkl
COPY data/processed/bm25_corpus.pkl ./data/processed/bm25_corpus.pkl

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "apps/mcp_server/server.py"]
