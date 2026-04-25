"""SIMD Unified Bridge — Vector operations with optional Rust acceleration."""

from __future__ import annotations

import logging
import math
from typing import Any, List, Tuple, cast

logger = logging.getLogger(__name__)

# Lazy import Rust accelerators
_rust_available = False
_rust_module = None


def _init_rust() -> Any:
    """Lazy initialization of Rust SIMD accelerators."""
    global _rust_available, _rust_module
    if _rust_module is not None:
        return _rust_module

    try:
        from whitemagic.optimization import rust_accelerators
        _rust_module = rust_accelerators
        _rust_available = True
        logger.debug("Rust SIMD accelerators loaded")
        return _rust_module
    except ImportError:
        logger.debug("Rust SIMD unavailable, using Python fallback")
        _rust_available = False
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def batch_cosine_similarity(query: list[float], vectors: list[list[float]]) -> list[float]:
    """Compute cosine similarity between query and multiple vectors."""
    return [cosine_similarity(query, v) for v in vectors]


# Aliases for compatibility
batch_cosine = batch_cosine_similarity


def batch_normalize(vectors: list[list[float]]) -> list[list[float]]:
    """Normalize a batch of vectors to unit length."""
    result = []
    for v in vectors:
        norm = math.sqrt(sum(x * x for x in v))
        if norm == 0:
            result.append(v)
        else:
            result.append([x / norm for x in v])
    return result


def batch_topk_cosine(query: list[float], vectors: list[list[float]], k: int = 10) -> list[tuple[int, float]]:
    """Find top-k most similar vectors using cosine similarity."""
    scores = [(i, cosine_similarity(query, v)) for i, v in enumerate(vectors)]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:k]


def batch_centroid(vectors: list[list[float]]) -> list[float]:
    """Compute centroid of a batch of vectors."""
    if not vectors:
        return []
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def cosine_similarity_zig(a: list[float], b: list[float]) -> float:
    """Zig-optimized cosine similarity (fallback to Python)."""
    return cosine_similarity(a, b)


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Extract keywords from text. Uses Rust accelerator if available."""
    rust = _init_rust()
    if rust and hasattr(rust, 'keyword_extract'):
        try:
            result = rust.keyword_extract(text, top_n)
            if isinstance(result, list):
                return [str(w) for w in result]
        except Exception:
            pass

    # Python fallback
    words = text.lower().split()
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]


def grid_density_scan(points: list[list[float]], radius: float = 1.0) -> list[list[int]]:
    """Scan 2D point cloud for density grid."""
    grid_size = 50
    grid = [[0] * grid_size for _ in range(grid_size)]
    if not points:
        return grid

    # Find bounds
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Bin points
    for x, y in points:
        if max_x > min_x and max_y > min_y:
            i = int((x - min_x) / (max_x - min_x) * (grid_size - 1))
            j = int((y - min_y) / (max_y - min_y) * (grid_size - 1))
            grid[i][j] += 1

    return grid


def holographic_5d_centroid(points: list[list[float]]) -> list[float]:
    """Compute centroid of 5D holographic points."""
    if not points:
        return [0.0] * 5
    return [sum(p[i] for p in points) / len(points) for i in range(5)]


def holographic_5d_distance(a: list[float], b: list[float]) -> float:
    """Euclidean distance in 5D holographic space."""
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(min(len(a), len(b), 5))))


def holographic_5d_knn(query: list[float], points: list[list[float]], k: int = 10) -> list[tuple[int, float]]:
    """Find k-nearest neighbors in 5D holographic space."""
    scores = [(i, holographic_5d_distance(query, p)) for i, p in enumerate(points)]
    scores.sort(key=lambda x: x[1])
    return scores[:k]


def pairwise_distance_matrix(vectors: list[list[float]]) -> list[list[float]]:
    """Compute pairwise cosine similarity matrix."""
    return [[cosine_similarity(a, b) for b in vectors] for a in vectors]


def simd_constellation_status() -> dict[str, Any]:
    _init_rust()
    return {"status": "ok", "available": True, "rust_available": _rust_available}


def simd_distance_status() -> dict[str, Any]:
    _init_rust()
    return {"status": "ok", "available": True, "rust_available": _rust_available}


def simd_holographic_status() -> dict[str, Any]:
    _init_rust()
    return {"status": "ok", "available": True, "rust_available": _rust_available}


def simd_keywords_status() -> dict[str, Any]:
    _init_rust()
    return {"status": "ok", "available": True, "rust_available": _rust_available}


def simd_status() -> dict[str, Any]:
    _init_rust()
    return {"status": "ok", "python_fallback": True, "rust_accelerated": _rust_available}


def simd_vector_batch_status() -> dict[str, Any]:
    _init_rust()
    return {"status": "ok", "available": True, "rust_available": _rust_available}


def top_k_nearest(query: list[float], vectors: list[list[float]], k: int = 10) -> list[tuple[int, float]]:
    """Find top-k nearest vectors by cosine similarity."""
    return batch_topk_cosine(query, vectors, k)
