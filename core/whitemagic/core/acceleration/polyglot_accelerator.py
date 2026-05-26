"""Unified Polyglot Accelerator - Smart Multi-Backend Routing.
================================================================
Provides a single interface that automatically routes operations to the
fastest available backend: Rust > Zig > Mojo > Python.

This module consolidates acceleration logic and provides graceful fallbacks
for all compute-intensive operations in WhiteMagic.

Usage:
    from whitemagic.core.acceleration.polyglot_accelerator import get_accelerator

    accel = get_accelerator()

    # Vector operations
    score = accel.cosine_similarity(vec_a, vec_b)
    scores = accel.batch_cosine(query, matrix)

    # Pattern operations
    patterns = accel.extract_patterns(content, limit=10)

    # Memory operations
    duplicates = accel.find_duplicates(memories)
"""
from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence
from typing import Any, cast

logger = logging.getLogger(__name__)


class PolyglotAccelerator:
    """Unified accelerator with smart backend routing."""

    def __init__(self):
        self._rust_available = False
        self._zig_available = False
        self._mojo_available = False

        # Metrics
        self.rust_calls = 0
        self.zig_calls = 0
        self.mojo_calls = 0
        self.python_calls = 0
        self.total_time_ms = 0.0

        # Check backend availability
        self._check_backends()

    def _check_backends(self):
        """Check which acceleration backends are available."""
        # Check Rust
        try:
            from importlib.util import find_spec
            if find_spec("whitemagic_rs") is not None:
                self._rust_available = True
                logger.info("🦀 Rust acceleration available")
        except ImportError:
            pass

        # Check Zig SIMD
        try:
            from whitemagic.core.acceleration.simd_cosine import simd_status
            status = simd_status()
            if status["has_zig_simd"]:
                self._zig_available = True
                logger.info(f"⚡ Zig SIMD available (lane_width={status['lane_width']})")
        except Exception:
            pass

        # Check Mojo
        try:
            from whitemagic.optimization.polyglot_router import get_router
            router = get_router()
            if router._mojo_available:
                self._mojo_available = True
                logger.info("🔥 Mojo acceleration available")
        except Exception:
            pass

        if not any([self._rust_available, self._zig_available, self._mojo_available]):
            logger.warning("⚠️  No native accelerators available - using Python fallback")

    # ========================================================================
    # Vector Operations
    # ========================================================================

    def cosine_similarity(self, a: Sequence[float], b: Sequence[float]) -> float:
        """Compute cosine similarity between two vectors.

        Backend priority: Rust SIMD > Zig SIMD > Python
        """
        if len(a) != len(b) or len(a) == 0:
            return 0.0

        start = time.time()

        # Try Rust first (fastest)
        if self._rust_available:
            try:
                import whitemagic_rs
                if hasattr(whitemagic_rs, 'simd_cosine_similarity'):
                    result = float(whitemagic_rs.simd_cosine_similarity(list(a), list(b)))
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return result
            except Exception as e:
                logger.debug(f"Rust cosine failed: {e}")

        # Try Zig SIMD (second fastest)
        if self._zig_available:
            try:
                from whitemagic.core.acceleration import cosine_similarity_zig
                result = float(cosine_similarity_zig(list(a), list(b)))
                self.zig_calls += 1
                self.total_time_ms += (time.time() - start) * 1000
                return result
            except Exception as e:
                logger.debug(f"Zig cosine failed: {e}")

        # Python fallback
        result = self._py_cosine(a, b)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def batch_cosine(self, query: Sequence[float], vectors: list[Sequence[float]]) -> list[float]:
        """Compute cosine similarity between query and batch of vectors.

        Backend priority: Rust batch > Zig batch > Python
        """
        if not vectors or not query:
            return []

        start = time.time()

        # Try Rust batch operation
        if self._rust_available:
            try:
                import whitemagic_rs
                if hasattr(whitemagic_rs, 'simd_cosine_batch'):
                    # Convert to list of lists for Rust
                    vecs_list = [list(v) for v in vectors]
                    result = whitemagic_rs.simd_cosine_batch(list(query), vecs_list)
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[float], result)
            except Exception as e:
                logger.debug(f"Rust batch cosine failed: {e}")

        # Try Zig batch operation
        if self._zig_available:
            try:
                from whitemagic.core.acceleration.simd_cosine import batch_cosine as zig_batch
                result = zig_batch(query, vectors)
                self.zig_calls += 1
                self.total_time_ms += (time.time() - start) * 1000
                return cast(list[float], result)
            except Exception as e:
                logger.debug(f"Zig batch cosine failed: {e}")

        # Python fallback
        result = [self._py_cosine(query, v) for v in vectors]
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    # ========================================================================
    # Pattern Operations
    # ========================================================================

    def extract_patterns(self, content: str, limit: int = 10) -> list[dict[str, Any]]:
        """Extract patterns from content.

        Backend priority: Rust > Python
        """
        start = time.time()

        # Try Rust pattern extraction
        if self._rust_available:
            try:
                import whitemagic_rs
                if hasattr(whitemagic_rs, 'extract_patterns_from_content'):
                    result = whitemagic_rs.extract_patterns_from_content(content, limit)
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[dict[str, Any]], result)
            except Exception as e:
                logger.debug(f"Rust pattern extraction failed: {e}")

        # Python fallback - simple keyword extraction
        result = self._py_extract_patterns(content, limit)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def find_duplicates(self, texts: list[str], threshold: float = 0.9) -> list[tuple[int, int, float]]:
        """Find duplicate texts using MinHash LSH.

        Backend priority: Rust > Python
        """
        start = time.time()

        # Try Rust MinHash
        if self._rust_available:
            try:
                import whitemagic_rs
                if hasattr(whitemagic_rs, 'minhash_find_duplicates'):
                    result = whitemagic_rs.minhash_find_duplicates(texts, threshold)
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[tuple[int, int, float]], result)
            except Exception as e:
                logger.debug(f"Rust minhash failed: {e}")

        # Python fallback - simple exact match
        result = self._py_find_duplicates(texts, threshold)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    # ========================================================================
    # Search Operations
    # ========================================================================

    def search_memories(self, query: str, memories: list[tuple[str, str]],
                       threshold: float = 0.7, limit: int = 10) -> list[tuple[str, float]]:
        """Search memories using fast text matching.

        Backend priority: Rust > Python
        """
        start = time.time()

        # Try Rust search
        if self._rust_available:
            try:
                import whitemagic_rs
                if hasattr(whitemagic_rs, 'search_query'):
                    # Build index and search
                    docs = [{"id": m[0], "content": m[1]} for m in memories]
                    index = whitemagic_rs.search_build_index(docs)
                    results = whitemagic_rs.search_query(index, query, limit)
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return [(r["id"], r["score"]) for r in results]
            except Exception as e:
                logger.debug(f"Rust search failed: {e}")

        # Python fallback
        result = self._py_search_memories(query, memories, threshold, limit)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    # ========================================================================
    # Python Fallbacks
    # ========================================================================

    @staticmethod
    def _py_cosine(a: Sequence[float], b: Sequence[float]) -> float:
        """Pure Python cosine similarity."""
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    @staticmethod
    def _py_extract_patterns(content: str, limit: int) -> list[dict[str, Any]]:
        """Simple Python pattern extraction."""
        words = content.lower().split()
        word_freq: dict[str, int] = {}
        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        patterns = []
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:limit]:
            patterns.append({
                "pattern": word,
                "frequency": freq,
                "score": freq / len(words) if words else 0.0
            })
        return patterns

    @staticmethod
    def _py_find_duplicates(texts: list[str], threshold: float) -> list[tuple[int, int, float]]:
        """Simple Python duplicate detection."""
        duplicates = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if texts[i] == texts[j]:
                    duplicates.append((i, j, 1.0))
        return duplicates

    @staticmethod
    def _py_search_memories(query: str, memories: list[tuple[str, str]],
                           threshold: float, limit: int) -> list[tuple[str, float]]:
        """Simple Python memory search."""
        from difflib import SequenceMatcher
        results = []
        for mid, content in memories:
            score = SequenceMatcher(None, query.lower(), content.lower()).ratio()
            if score >= threshold:
                results.append((mid, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    # ========================================================================
    # Status & Metrics
    # ========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get acceleration statistics."""
        total_calls = self.rust_calls + self.zig_calls + self.mojo_calls + self.python_calls
        native_calls = self.rust_calls + self.zig_calls + self.mojo_calls

        return {
            "backends": {
                "rust": self._rust_available,
                "zig": self._zig_available,
                "mojo": self._mojo_available,
            },
            "calls": {
                "rust": self.rust_calls,
                "zig": self.zig_calls,
                "mojo": self.mojo_calls,
                "python": self.python_calls,
                "total": total_calls,
            },
            "native_usage_pct": (native_calls / max(total_calls, 1)) * 100,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.total_time_ms / max(total_calls, 1), 4),
        }


# Global singleton
_accelerator: PolyglotAccelerator | None = None


def get_accelerator() -> PolyglotAccelerator:
    """Get the global polyglot accelerator instance."""
    global _accelerator
    if _accelerator is None:
        _accelerator = PolyglotAccelerator()
    return _accelerator


def get_acceleration_stats() -> dict[str, Any]:
    """Get current acceleration statistics."""
    return get_accelerator().get_stats()
