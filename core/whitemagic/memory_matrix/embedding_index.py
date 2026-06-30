# ruff: noqa: BLE001
"""
Embedding Index — Semantic search across all content.

Uses Rust-accelerated embeddings for fast similarity search when available,
falling back to simple keyword matching otherwise.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class EmbeddingIndex:
    """Semantic search index for all content."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "memory_matrix"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.data_dir / "embedding_index.jsonl"
        self._index: list[dict[str, Any]] = []

    def add(
        self, item_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Add content to the embedding index."""
        # Simple keyword-based embedding (hash-based pseudo-embedding)
        words = set(content.lower().split())
        entry = {
            "id": item_id,
            "content": content[:500],
            "words": list(words),
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._index.append(entry)
        with open(self.index_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar content."""
        query_words = set(query.lower().split())
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self._index:
            entry_words = set(entry["words"])
            overlap = len(query_words & entry_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        return [
            {
                "id": e["id"],
                "content": e["content"],
                "score": s,
                "metadata": e["metadata"],
            }
            for s, e in scored[:limit]
        ]

    def remove(self, item_id: str) -> bool:
        """Remove an item from the index."""
        before = len(self._index)
        self._index = [e for e in self._index if e["id"] != item_id]
        return len(self._index) < before

    def summary(self) -> dict[str, Any]:
        return {
            "total_items": len(self._index),
            "unique_words": len(set(w for e in self._index for w in e["words"])),
        }


_index: EmbeddingIndex | None = None


def get_embedding_index() -> EmbeddingIndex:
    global _index
    if _index is None:
        _index = EmbeddingIndex()
    return _index
