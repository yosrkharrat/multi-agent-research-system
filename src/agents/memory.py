"""
STEP 2 — Cross-session semantic memory (ChromaDB)
==================================================
Implements three memory tiers that persist across runs:

  Tier 1 — Working memory   : AgentState (already exists, no change needed)
  Tier 2 — Episodic memory  : persistence.py run store (already exists)
  Tier 3 — Semantic memory  : THIS FILE — ChromaDB vector store

How to wire it in:

  Researcher node — before calling the web:
      hits = memory.search(question, n=3)
      if hits:
          # use cached finding, skip web search

  Researcher node — after getting a new finding:
      memory.add(question, finding_text, metadata={"topic": state["topic"]})

  Memory is stored in  ./memory_store/  (gitignore this directory).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions


# ── Constants ─────────────────────────────────────────────────────────────────

MEMORY_DIR = Path("memory_store")
COLLECTION_NAME = "research_findings"

# Similarity threshold: cosine distance < this → "close enough to reuse"
# Range 0–2 (ChromaDB uses L2 by default; we configure cosine below).
# 0.25 = ~87% cosine similarity — tight match, avoids false positives.
SIMILARITY_THRESHOLD = 0.25


# ── SemanticMemory ─────────────────────────────────────────────────────────────

class SemanticMemory:
    """
    Persistent vector memory backed by ChromaDB.

    Uses the default all-MiniLM-L6-v2 embedding model that ships with
    chromadb — no API key, fully local, ~80 MB download on first use.

    Parameters
    ----------
    persist_dir : str | Path
        Directory where ChromaDB stores its files.
    similarity_threshold : float
        Maximum cosine distance to consider a hit "close enough".
    """

    def __init__(
        self,
        persist_dir: str | Path = MEMORY_DIR,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        self.threshold = similarity_threshold

        # Persistent client writes to disk automatically
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))

        # Use the bundled sentence-transformers model (downloads once)
        self._ef = embedding_functions.DefaultEmbeddingFunction()

        self._col = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},  # cosine distance
        )

    # ── write ─────────────────────────────────────────────────────────────────

    def add(
        self,
        question: str,
        finding: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store a (question, finding) pair.  Returns the document ID.

        If the exact same question+finding hash already exists, skips
        the insert (idempotent).
        """
        doc_id = _hash(question + finding)
        meta = {"question": question[:200], **(metadata or {})}

        # ChromaDB raises if you try to add a duplicate ID — check first
        existing = self._col.get(ids=[doc_id])
        if existing["ids"]:
            return doc_id  # already stored

        self._col.add(
            ids=[doc_id],
            documents=[finding],
            metadatas=[meta],
        )
        return doc_id

    # ── read ──────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n: int = 3,
        topic_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return up to *n* findings semantically similar to *query*.

        Each result dict has:
            text       : str   — the stored finding text
            question   : str   — the original question it answered
            distance   : float — cosine distance (lower = more similar)
            id         : str   — document ID

        Results with distance > threshold are filtered out.
        """
        if self._col.count() == 0:
            return []

        where = {"topic": topic_filter} if topic_filter else None

        results = self._col.query(
            query_texts=[query],
            n_results=min(n, self._col.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if dist <= self.threshold:
                hits.append(
                    {
                        "text": doc,
                        "question": meta.get("question", ""),
                        "distance": round(dist, 4),
                        "id": results["ids"][0][len(hits)],
                    }
                )
        return hits

    def search_with_mmr(
        self,
        query: str,
        n: int = 3,
        fetch_k: int = 10,
        lambda_mult: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Maximal Marginal Relevance retrieval.

        Balances relevance (similar to query) against diversity (different
        from each other).  lambda_mult=1.0 → pure relevance,
        lambda_mult=0.0 → pure diversity.

        This prevents the researcher from reading 3 nearly-identical
        findings when the memory has varied content.
        """
        if self._col.count() == 0:
            return []

        # Fetch a broader candidate set first
        raw = self._col.query(
            query_texts=[query],
            n_results=min(fetch_k, self._col.count()),
            include=["documents", "metadatas", "distances", "embeddings"],
        )

        candidates = list(
            zip(
                raw["ids"][0],
                raw["documents"][0],
                raw["metadatas"][0],
                raw["distances"][0],
                raw["embeddings"][0],
            )
        )

        if not candidates:
            return []

        # MMR greedy selection
        selected: list[dict] = []
        remaining = list(candidates)

        query_emb = self._ef([query])[0]

        while remaining and len(selected) < n:
            # Score each candidate: lambda * relevance - (1-lambda) * max_sim_to_selected
            best_score = -float("inf")
            best_idx = 0

            for i, (cid, doc, meta, dist, emb) in enumerate(remaining):
                relevance = 1.0 - dist  # cosine similarity from distance

                if selected:
                    max_sim = max(
                        _cosine_sim(emb, s["_emb"]) for s in selected
                    )
                else:
                    max_sim = 0.0

                score = lambda_mult * relevance - (1 - lambda_mult) * max_sim
                if score > best_score:
                    best_score = score
                    best_idx = i

            cid, doc, meta, dist, emb = remaining.pop(best_idx)
            if dist <= self.threshold:
                selected.append(
                    {
                        "text": doc,
                        "question": meta.get("question", ""),
                        "distance": round(dist, 4),
                        "id": cid,
                        "_emb": emb,
                    }
                )

        # Strip internal embedding from output
        return [{k: v for k, v in s.items() if k != "_emb"} for s in selected]

    # ── introspection ─────────────────────────────────────────────────────────

    def count(self) -> int:
        return self._col.count()

    def stats(self) -> dict:
        return {
            "total_findings": self.count(),
            "persist_dir": str(self.persist_dir),
            "threshold": self.threshold,
        }


# ── helpers ───────────────────────────────────────────────────────────────────

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x ** 2 for x in a) ** 0.5
    mag_b = sum(x ** 2 for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── module-level singleton (import and reuse across nodes) ────────────────────
_memory: SemanticMemory | None = None


def get_memory(persist_dir: str | Path = MEMORY_DIR) -> SemanticMemory:
    """Return a module-level singleton SemanticMemory instance."""
    global _memory
    if _memory is None:
        _memory = SemanticMemory(persist_dir=persist_dir)
    return _memory
