from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class MemoryEntry:
    state: str  # Combined comment + state string
    comment: str  # Original comment
    state_metrics: str  # State metrics string
    reasoning: str
    plan: str
    persona: str


class SimpleVectorStore:
    """
    Vector store for (comment+state, reasoning, plan) triples.
    Uses combined comment + state as the key for semantic similarity.
    Supports TF-IDF (default) and optional SBERT embeddings if sentence-transformers is available.
    Includes simple JSON persistence.
    """

    def __init__(self, backend: str = "tfidf", embed_model: Optional[str] = None):
        self.entries: List[MemoryEntry] = []
        self.backend = backend
        self.embed_model_name = embed_model
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = None
        self._sbert = None
        self._embed_matrix = None

        if self.backend == "sbert":
            try:
                from sentence_transformers import SentenceTransformer

                model_name = embed_model or "sentence-transformers/all-MiniLM-L6-v2"
                self._sbert = SentenceTransformer(model_name)
            except Exception:
                self.backend = "tfidf"

    def _fit(self):
        # Use combined comment + state for vectorization
        corpus = [e.state for e in self.entries]
        if not corpus:
            return
        if self.backend == "tfidf":
            self.matrix = self.vectorizer.fit_transform(corpus)
        else:
            embeddings = self._sbert.encode(corpus, convert_to_numpy=True, normalize_embeddings=True)  # type: ignore
            self._embed_matrix = embeddings

    def add(self, entry: MemoryEntry) -> None:
        self.entries.append(entry)
        self._fit()

    def bulk_load(self, entries: List[MemoryEntry]) -> None:
        self.entries.extend(entries)
        self._fit()

    def _search_tfidf(self, query: str) -> np.ndarray:
        query_vec = self.vectorizer.transform([query])
        return cosine_similarity(query_vec, self.matrix).flatten()

    def _search_sbert(self, query: str) -> np.ndarray:
        qvec = self._sbert.encode([query], convert_to_numpy=True, normalize_embeddings=True)  # type: ignore
        return (qvec @ self._embed_matrix.T).flatten()  # cosine because normalized

    def search(self, query: str, top_k: int = 3, min_similarity: float = 0.05) -> List[Dict[str, str]]:
        if not self.entries:
            return []
        if self.backend == "tfidf":
            if self.matrix is None:
                return []
            sims = self._search_tfidf(query)
        else:
            if self._embed_matrix is None:
                return []
            sims = self._search_sbert(query)

        ranked_idx = np.argsort(sims)[::-1]
        results = []
        for idx in ranked_idx[:top_k]:
            if sims[idx] < min_similarity:
                continue
            e = self.entries[idx]
            results.append(
                {
                    "comment": e.comment,
                    "state_metrics": e.state_metrics,
                    "reasoning": e.reasoning,
                    "plan": e.plan,
                    "persona": e.persona,
                    "similarity": float(sims[idx]),
                }
            )
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "state": e.state,
                "comment": e.comment,
                "state_metrics": e.state_metrics,
                "reasoning": e.reasoning,
                "plan": e.plan,
                "persona": e.persona,
            }
            for e in self.entries
        ]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Handle old data format
        entries = []
        for r in raw:
            # Old format might not have comment/state_metrics separated
            if "comment" in r and "state_metrics" in r:
                # New format
                entries.append(
                    MemoryEntry(
                        state=r.get("state", ""),
                        comment=r.get("comment", ""),
                        state_metrics=r.get("state_metrics", ""),
                        reasoning=r.get("reasoning", ""),
                        plan=r.get("plan", ""),
                        persona=r.get("persona", "firm_professional"),
                    )
                )
            else:
                # Old format - reconstruct
                state_str = r.get("state", "")
                entries.append(
                    MemoryEntry(
                        state=state_str,
                        comment="",  # Unknown in old format
                        state_metrics=state_str,  # Use state as metrics
                        reasoning=r.get("reasoning", ""),
                        plan=r.get("plan", ""),
                        persona=r.get("persona", "firm_professional"),
                    )
                )
        self.bulk_load(entries)
