FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifest first (better layer caching)
COPY pyproject.toml ./

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
COPY data/processed/embeddings.npy ./data/processed/embeddings.npy
COPY data/processed/embedding_ids.json ./data/processed/embedding_ids.json

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "apps/mcp_server/server.py"]
