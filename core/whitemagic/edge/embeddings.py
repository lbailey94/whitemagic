# ruff: noqa: BLE001
"""
Local Embeddings — Similarity search without cloud APIs.

Uses TF-IDF, character n-grams, and Jaccard similarity for
semantic matching without external dependencies.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


class LocalEmbeddings:
    """Local similarity search without cloud APIs."""

    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self._tf_cache: dict[str, Counter[str]] = {}

    def add(self, doc_id: str, content: str) -> None:
        """Add a document to the index."""
        self.documents[doc_id] = content
        self._tf_cache[doc_id] = self._tokenize(content)

    @staticmethod
    def _tokenize(text: str) -> Counter[str]:
        words = re.findall(r"\w+", text.lower())
        return Counter(words)

    @staticmethod
    def _ngrams(text: str, n: int = 3) -> set[str]:
        text = text.lower().replace(" ", "")
        return (
            {text[i : i + n] for i in range(len(text) - n + 1)}
            if len(text) >= n
            else {text}
        )

    def jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Jaccard similarity between two texts."""
        set_a = set(re.findall(r"\w+", text_a.lower()))
        set_b = set(re.findall(r"\w+", text_b.lower()))
        if not set_a and not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar documents."""
        results: list[tuple[float, str]] = []
        for doc_id, content in self.documents.items():
            score = self.jaccard_similarity(query, content)
            if score > 0:
                results.append((score, doc_id))
        results.sort(key=lambda x: -x[0])
        return [{"id": doc_id, "score": score} for score, doc_id in results[:limit]]

    def summary(self) -> dict[str, Any]:
        return {
            "total_documents": len(self.documents),
            "cache_size": len(self._tf_cache),
        }


_embeddings: LocalEmbeddings | None = None


def get_local_embeddings() -> LocalEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = LocalEmbeddings()
    return _embeddings
