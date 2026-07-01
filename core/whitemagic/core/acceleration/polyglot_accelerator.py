# ruff: noqa: BLE001
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

# Lazy-imported evolution backend cache
_evo_backend: Any = None
_evo_backend_time: float = 0.0


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

        self._check_backends()

    def _check_backends(self):
        """Check which acceleration backends are available."""
        try:
            from importlib.util import find_spec

            if find_spec("whitemagic_rs") is not None:
                self._rust_available = True
                logger.info("🦀 Rust acceleration available")
        except ImportError:
            pass

        try:
            from whitemagic.core.acceleration.simd_cosine import simd_status

            status = simd_status()
            if status["has_zig_simd"]:
                self._zig_available = True
                logger.info(
                    "⚡ Zig SIMD available (lane_width=%s)", status["lane_width"]
                )
        except (ImportError, AttributeError):
            pass

        try:
            from whitemagic.optimization.polyglot_router import get_router

            router = get_router()
            if router._mojo_available:
                self._mojo_available = True
                logger.info("🔥 Mojo acceleration available")
        except (ImportError, AttributeError):
            pass

        if not any([self._rust_available, self._zig_available, self._mojo_available]):
            logger.warning(
                "⚠️  No native accelerators available - using Python fallback"
            )

    def cosine_similarity(self, a: Sequence[float], b: Sequence[float]) -> float:
        """Compute cosine similarity between two vectors.

        Backend priority: Rust SIMD > Zig SIMD > Python
        """
        if len(a) != len(b) or len(a) == 0:
            return 0.0

        start = time.time()

        if self._rust_available:
            try:
                import whitemagic_rs

                if hasattr(whitemagic_rs, "simd_cosine_similarity"):
                    result = float(
                        whitemagic_rs.simd_cosine_similarity(list(a), list(b))
                    )
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return result
            except Exception as e:
                logger.debug("Rust cosine failed: %s", e, exc_info=True)

        if self._zig_available:
            try:
                from whitemagic.core.acceleration import cosine_similarity_zig

                result = float(cosine_similarity_zig(list(a), list(b)))
                self.zig_calls += 1
                self.total_time_ms += (time.time() - start) * 1000
                return result
            except Exception as e:
                logger.debug("Zig cosine failed: %s", e, exc_info=True)

        # Python fallback
        result = self._py_cosine(a, b)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def batch_cosine(
        self, query: Sequence[float], vectors: list[Sequence[float]]
    ) -> list[float]:
        """Compute cosine similarity between query and batch of vectors.

        Backend priority: Rust batch > Zig batch > Python
        """
        if not vectors or not query:
            return []

        start = time.time()

        if self._rust_available:
            try:
                import whitemagic_rs

                if hasattr(whitemagic_rs, "simd_cosine_batch"):
                    vecs_list = [list(v) for v in vectors]
                    result = whitemagic_rs.simd_cosine_batch(list(query), vecs_list)
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[float], result)
            except Exception as e:
                logger.debug("Rust batch cosine failed: %s", e, exc_info=True)

        if self._zig_available:
            try:
                from whitemagic.core.acceleration.simd_cosine import (
                    batch_cosine as zig_batch,
                )

                result = zig_batch(query, vectors)
                self.zig_calls += 1
                self.total_time_ms += (time.time() - start) * 1000
                return cast(list[float], result)
            except Exception as e:
                logger.debug("Zig batch cosine failed: %s", e, exc_info=True)

        # Python fallback
        result = [self._py_cosine(query, v) for v in vectors]
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def extract_patterns(
        self, content: str | list[str], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Extract patterns from content.

        Backend priority: Rust > Python
        """
        start = time.time()

        if self._rust_available:
            try:
                import whitemagic_rs

                if hasattr(whitemagic_rs, "extract_patterns_from_content"):
                    # Rust function expects Vec<String> and Option<f64>
                    memories = content if isinstance(content, list) else [content]
                    min_conf = (
                        float(limit) / 100.0
                    )  # Convert limit to confidence threshold
                    result = whitemagic_rs.extract_patterns_from_content(
                        memories, min_conf
                    )
                    # Rust returns (total, found, solutions, anti, heuristics, opts, duration)
                    total, found, solutions, anti, heuristics, opts, duration = result
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return (
                        [{"type": "solution", "description": s} for s in solutions]
                        + [{"type": "anti_pattern", "description": s} for s in anti]
                        + [{"type": "heuristic", "description": s} for s in heuristics]
                        + [{"type": "optimization", "description": s} for s in opts]
                    )
            except Exception as e:
                logger.debug("Rust pattern extraction failed: %s", e, exc_info=True)

        # Python fallback - simple keyword extraction
        result = self._py_extract_patterns(content, limit)  # type: ignore[assignment]
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result  # type: ignore[return-value]

    def find_duplicates(
        self, texts: list[str], threshold: float = 0.9
    ) -> list[tuple[int, int, float]]:
        """Find duplicate texts using MinHash LSH.

        Backend priority: Rust > Python
        """
        start = time.time()

        if self._rust_available:
            try:
                import whitemagic_rs

                if hasattr(whitemagic_rs, "minhash_find_duplicates"):
                    result = whitemagic_rs.minhash_find_duplicates(texts, threshold)
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[tuple[int, int, float]], result)
            except Exception as e:
                logger.debug("Rust minhash failed: %s", e, exc_info=True)

        # Python fallback - simple exact match
        result = self._py_find_duplicates(texts, threshold)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def search_memories(
        self,
        query: str,
        memories: list[tuple[str, str]],
        threshold: float = 0.7,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Search memories using fast text matching.

        Backend priority: Rust > Python
        """
        start = time.time()

        if self._rust_available:
            try:
                import json as _json

                import whitemagic_rs

                if hasattr(whitemagic_rs, "search_query"):
                    # Build index — Rust expects JSON string, returns (doc_count, vocab_size)
                    docs = [{"id": m[0], "content": m[1]} for m in memories]
                    whitemagic_rs.search_build_index(_json.dumps(docs))
                    # Query — Rust returns JSON string of [{id, score}]
                    raw_results = whitemagic_rs.search_query(query, limit)
                    results = (
                        _json.loads(raw_results)
                        if isinstance(raw_results, str)
                        else raw_results
                    )
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return [(r["id"], r["score"]) for r in results]
            except Exception as e:
                logger.debug("Rust search failed: %s", e, exc_info=True)

        # Python fallback
        result = self._py_search_memories(query, memories, threshold, limit)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def _get_evo_backend(self) -> Any:
        """Try to get a RustEvolutionBackend instance."""
        global _evo_backend, _evo_backend_time
        now = time.monotonic()
        if _evo_backend is not None and (now - _evo_backend_time) < 300.0:
            return _evo_backend
        try:
            import sys
            from pathlib import Path

            _bridge = (
                Path(__file__).resolve().parent.parent.parent.parent.parent
                / "polyglot"
                / "bridges"
                / "python"
            )
            if str(_bridge) not in sys.path:
                sys.path.insert(0, str(_bridge))
            from whitemagic_polyglot import RustEvolutionBackend

            backend = RustEvolutionBackend()
            backend.call("ping", timeout=5.0)
            _evo_backend = backend
            _evo_backend_time = now
            return backend
        except Exception:
            return None

    def shannon_entropy(self, p: float) -> float:
        """Compute Shannon entropy H(p) = -p*log2(p) - (1-p)*log2(1-p)."""
        start = time.time()
        backend = self._get_evo_backend()
        if backend is not None:
            try:
                raw = backend.call("shannon_entropy", p=p)
                if raw.get("status") == "ok":
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return float(raw["result"]["entropy"])
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
        # Python fallback
        if p <= 0 or p >= 1:
            return 0.0
        result = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

    def boltzmann_select(
        self, energies: list[float], temperature: float, k: int = 1, seed: int = 42
    ) -> list[int]:
        """Select k indices using Boltzmann sampling."""
        start = time.time()
        backend = self._get_evo_backend()
        if backend is not None:
            try:
                raw = backend.call(
                    "boltzmann_select",
                    energies=energies,
                    temperature=temperature,
                    k=k,
                    seed=seed,
                )
                if raw.get("status") == "ok":
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[int], raw["result"]["selected_indices"])
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
        # Python fallback: proportional sampling
        import random

        rng = random.Random(seed)
        if not energies or temperature <= 0:
            return list(range(min(k, len(energies))))
        probs = [math.exp(-e / temperature) for e in energies]
        total = sum(probs)
        probs = [p / total for p in probs]
        selected = rng.choices(range(len(energies)), weights=probs, k=k)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return selected

    def hrr_encode(
        self, description: str, dim: int = 384, impact: float = 0.5
    ) -> list[float]:
        """Encode a hypothesis as an HRR vector."""
        start = time.time()
        backend = self._get_evo_backend()
        if backend is not None:
            try:
                raw = backend.call(
                    "hrr_encode", description=description, dim=dim, impact=impact
                )
                if raw.get("status") == "ok":
                    self.rust_calls += 1
                    self.total_time_ms += (time.time() - start) * 1000
                    return cast(list[float], raw["result"]["vector"])
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
        # Python fallback: deterministic hash-based vector
        import hashlib

        result = []
        for i in range(dim):
            h = hashlib.sha256(f"{description}:{i}:{impact}".encode()).digest()
            val = (int.from_bytes(h[:8], "little") / 2**64 - 0.5) * 2 * impact
            result.append(val)
        self.python_calls += 1
        self.total_time_ms += (time.time() - start) * 1000
        return result

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
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[
            :limit
        ]:
            patterns.append(
                {
                    "pattern": word,
                    "frequency": freq,
                    "score": freq / len(words) if words else 0.0,
                }
            )
        return patterns

    @staticmethod
    def _py_find_duplicates(
        texts: list[str], threshold: float
    ) -> list[tuple[int, int, float]]:
        """Simple Python duplicate detection."""
        duplicates = []
        for i, text in enumerate(texts):
            for j in range(i + 1, len(texts)):
                if texts[i] == texts[j]:
                    duplicates.append((i, j, 1.0))
        return duplicates

    @staticmethod
    def _py_search_memories(
        query: str, memories: list[tuple[str, str]], threshold: float, limit: int
    ) -> list[tuple[str, float]]:
        """Simple Python memory search."""
        from difflib import SequenceMatcher

        results = []
        for mid, content in memories:
            score = SequenceMatcher(None, query.lower(), content.lower()).ratio()
            if score >= threshold:
                results.append((mid, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get acceleration statistics."""
        total_calls = (
            self.rust_calls + self.zig_calls + self.mojo_calls + self.python_calls
        )
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
