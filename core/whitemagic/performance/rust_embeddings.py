# ruff: noqa: BLE001
"""
Optimized Rust Bridge for Embeddings.

Provides a high-performance Python interface to Rust-accelerated
embedding operations with automatic fallback to pure Python.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RustEmbeddingsBridge:
    """Bridge to Rust-accelerated embedding operations."""

    def __init__(self) -> None:
        self._rust_available = False
        self._rust_module: Any = None
        self._check_rust()

    def _check_rust(self) -> None:
        """Check if Rust extension is available."""
        try:
            import importlib
            self._rust_module = importlib.import_module("whitemagic_rust")
            self._rust_available = True
            logger.info("Rust embeddings bridge active")
        except ImportError:
            logger.debug("Rust embeddings not available, using Python fallback")

    @property
    def is_rust_available(self) -> bool:
        return self._rust_available

    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if self._rust_available and hasattr(self._rust_module, "cosine_similarity"):
            return self._rust_module.cosine_similarity(vec_a, vec_b)
        # Python fallback
        if not vec_a or not vec_b:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def batch_similarity(self, query: list[float], vectors: list[list[float]]) -> list[float]:
        """Batch cosine similarity."""
        if self._rust_available and hasattr(self._rust_module, "batch_cosine_similarity"):
            return list(self._rust_module.batch_cosine_similarity(query, vectors))
        return [self.cosine_similarity(query, v) for v in vectors]

    def benchmark(self, n: int = 1000) -> dict[str, Any]:
        """Benchmark Rust vs Python performance."""
        import random
        vec_a = [random.random() for _ in range(128)]
        vec_b = [random.random() for _ in range(128)]

        start = time.monotonic()
        for _ in range(n):
            self.cosine_similarity(vec_a, vec_b)
        elapsed = time.monotonic() - start

        return {
            "iterations": n,
            "total_time_s": elapsed,
            "avg_time_us": (elapsed / n) * 1e6,
            "rust_active": self._rust_available,
        }


_bridge: RustEmbeddingsBridge | None = None


def get_rust_embeddings() -> RustEmbeddingsBridge:
    global _bridge
    if _bridge is None:
        _bridge = RustEmbeddingsBridge()
    return _bridge
