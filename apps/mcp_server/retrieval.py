"""Retrieval layer — BM25 (+ optional Voyage AI hybrid) over pre-built index.

The KnowledgeBase singleton loads everything once at server startup so that
search latency is negligible (pure in-memory).  If VOYAGE_API_KEY is set and
embeddings.npy exists, hybrid scoring (BM25 + cosine) is used automatically.
"""
from __future__ import annotations

import json
import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"

CHUNKS_JSONL = PROCESSED_DIR / "chunks.jsonl"
BM25_INDEX_PKL = PROCESSED_DIR / "bm25_index.pkl"
BM25_CORPUS_PKL = PROCESSED_DIR / "bm25_corpus.pkl"
EMBEDDINGS_NPY = PROCESSED_DIR / "embeddings.npy"
EMBEDDING_IDS_JSON = PROCESSED_DIR / "embedding_ids.json"


@dataclass
class SearchResult:
    chunk_id: str
    doc_id: str
    source: str
    page_or_slide: int
    chunk_index: int
    text: str
    metadata: dict[str, Any]
    score: float


def _tokenise(text: str) -> list[str]:
    return text.lower().split()


def _normalise(arr: "np.ndarray") -> "np.ndarray":  # type: ignore[name-defined]
    max_val = arr.max()
    if max_val == 0:
        return arr
    return arr / max_val


class KnowledgeBase:
    """Singleton that owns the in-memory index."""

    def __init__(self) -> None:
        self._chunks: list[dict[str, Any]] = []
        self._id_map: dict[str, dict[str, Any]] = {}
        self._bm25: Any = None
        self._embeddings: Any = None  # np.ndarray | None
        self._emb_ids: list[str] = []
        self._voyage_client: Any = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._load_chunks()
        self._load_bm25()
        self._load_embeddings()
        self._loaded = True

    def _load_chunks(self) -> None:
        with CHUNKS_JSONL.open(encoding="utf-8") as fh:
            self._chunks = [json.loads(line) for line in fh]
        self._id_map = {c["chunk_id"]: c for c in self._chunks}

    def _load_bm25(self) -> None:
        with BM25_INDEX_PKL.open("rb") as fh:
            self._bm25 = pickle.load(fh)

    def _load_embeddings(self) -> None:
        api_key = os.environ.get("VOYAGE_API_KEY", "")
        if not api_key or not EMBEDDINGS_NPY.exists():
            return
        try:
            import numpy as np
            import voyageai

            self._embeddings = np.load(str(EMBEDDINGS_NPY))
            with EMBEDDING_IDS_JSON.open(encoding="utf-8") as fh:
                self._emb_ids = json.load(fh)
            self._voyage_client = voyageai.Client(api_key=api_key)
        except ImportError:
            pass

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self._embeddings is not None and self._voyage_client is not None:
            return self._hybrid_search(query, top_k)
        return self._bm25_search(query, top_k)

    def _bm25_search(self, query: str, top_k: int) -> list[SearchResult]:
        import numpy as np

        tokens = _tokenise(query)
        scores: np.ndarray = np.array(self._bm25.get_scores(tokens))
        top_idx = scores.argsort()[::-1][:top_k]
        return [self._make_result(self._chunks[i], float(scores[i])) for i in top_idx]

    def _hybrid_search(self, query: str, top_k: int) -> list[SearchResult]:
        import numpy as np

        # BM25 scores
        tokens = _tokenise(query)
        bm25_scores: np.ndarray = _normalise(np.array(self._bm25.get_scores(tokens)))

        # Cosine similarity via Voyage embedding
        result = self._voyage_client.embed(
            [query], model="voyage-3-lite", input_type="query"
        )
        q_vec: np.ndarray = np.array(result.embeddings[0], dtype=np.float32)
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        safe_norms = np.where(norms == 0, 1.0, norms)
        cosine: np.ndarray = self._embeddings @ q_vec / (safe_norms.squeeze() * np.linalg.norm(q_vec))
        cosine_norm = _normalise((cosine + 1.0) / 2.0)  # shift [-1,1] → [0,1]

        # Align cosine to chunks order using embedding_ids
        emb_idx = {cid: i for i, cid in enumerate(self._emb_ids)}
        combined = np.zeros(len(self._chunks))
        for i, chunk in enumerate(self._chunks):
            cid = chunk["chunk_id"]
            bm = bm25_scores[i]
            cos = cosine_norm[emb_idx[cid]] if cid in emb_idx else 0.0
            combined[i] = 0.5 * bm + 0.5 * cos

        top_idx = combined.argsort()[::-1][:top_k]
        return [self._make_result(self._chunks[i], float(combined[i])) for i in top_idx]

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self._id_map.get(chunk_id)

    @property
    def search_mode(self) -> str:
        if self._embeddings is not None and self._voyage_client is not None:
            return "hybrid"
        return "bm25"

    def list_documents(self) -> list[dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for chunk in self._chunks:
            doc_id = chunk["doc_id"]
            if doc_id not in summary:
                summary[doc_id] = {
                    "doc_id": doc_id,
                    "source": chunk["source"],
                    "chunk_count": 0,
                }
            summary[doc_id]["chunk_count"] += 1
        docs = list(summary.values())
        docs.append({"search_mode": self.search_mode})
        return docs

    @staticmethod
    def _make_result(chunk: dict[str, Any], score: float) -> SearchResult:
        return SearchResult(
            chunk_id=chunk["chunk_id"],
            doc_id=chunk["doc_id"],
            source=chunk["source"],
            page_or_slide=chunk["page_or_slide"],
            chunk_index=chunk["chunk_index"],
            text=chunk["text"],
            metadata=chunk.get("metadata", {}),
            score=score,
        )


# Module-level singleton loaded at server startup via lifespan.
kb = KnowledgeBase()
