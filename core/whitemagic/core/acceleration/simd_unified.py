"""Unified SIMD Bridge — Single interface to all Rust SIMD operations.

Replaces 6 separate SIMD modules with one unified bridge:
- simd_cosine.py (cosine similarity, batch operations)
- simd_distance.py (pairwise distance, top-k nearest)
- simd_holographic.py (5D holographic operations)
- simd_constellation.py (grid density scanning)
- simd_keywords.py (keyword extraction)
- simd_vector_batch.py (batch normalization, centroid, top-k)

All operations route through Rust accelerators with Python fallback.
"""
from __future__ import annotations

import logging
from typing import Any, cast, List, Tuple

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


# ============================================================================
# COSINE SIMILARITY OPERATIONS
# ============================================================================

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Rust: O(n) SIMD dot product + magnitude
    Python fallback: O(n) standard implementation
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'cosine_similarity'):
        return float(rust.cosine_similarity(vec_a, vec_b))

    # Python fallback
    import math
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def batch_cosine(query: list[float], vectors: list[list[float]]) -> list[float]:
    """Compute cosine similarity between query and multiple vectors.

    Rust: Parallel SIMD batch processing
    Python fallback: Sequential computation
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'batch_cosine'):
        return cast(List[float], rust.batch_cosine(query, vectors))

    return [cosine_similarity(query, vec) for vec in vectors]


# ============================================================================
# DISTANCE OPERATIONS
# ============================================================================

def pairwise_distance_matrix(vectors: list[list[float]]) -> list[list[float]]:
    """Compute pairwise distance matrix for all vectors.

    Rust: O(n²) SIMD with cache optimization
    Python fallback: O(n²) standard implementation
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'pairwise_distance_matrix'):
        return cast(List[List[float]], rust.pairwise_distance_matrix(vectors))

    # Python fallback
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist = 1.0 - cosine_similarity(vectors[i], vectors[j])
            matrix[i][j] = matrix[j][i] = dist
    return matrix


def top_k_nearest(query: list[float], vectors: list[list[float]], k: int = 10) -> list[tuple[int, float]]:
    """Find k nearest vectors to query by cosine similarity.

    Rust: Heap-based top-k with SIMD
    Python fallback: Sort-based approach
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'top_k_nearest'):
        return cast(List[Tuple[int, float]], rust.top_k_nearest(query, vectors, k))

    # Python fallback
    similarities = [(i, cosine_similarity(query, vec)) for i, vec in enumerate(vectors)]
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:k]


def cosine_similarity_zig(vec_a: list[float], vec_b: list[float]) -> float:
    """Zig-accelerated cosine similarity (if available).

    Falls back to Rust or Python implementation.
    """
    # Try Zig first, then Rust, then Python
    try:
        from whitemagic.optimization import rust_accelerators
        zig_acc = getattr(rust_accelerators, "zig_accelerators", None)
        if zig_acc and hasattr(zig_acc, 'cosine_similarity'):
            return float(zig_acc.cosine_similarity(vec_a, vec_b))
    except (ImportError, AttributeError):
        pass

    return cosine_similarity(vec_a, vec_b)


# ============================================================================
# HOLOGRAPHIC 5D OPERATIONS
# ============================================================================

def holographic_5d_distance(coord_a: tuple[float, ...], coord_b: tuple[float, ...]) -> float:
    """Compute 5D holographic distance between coordinates.

    Rust: SIMD 5D Euclidean distance
    Python fallback: Standard computation
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'holographic_5d_distance'):
        return float(rust.holographic_5d_distance(list(coord_a), list(coord_b)))

    # Python fallback
    import math
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(coord_a, coord_b)))


def holographic_5d_knn(query: tuple[float, ...], coords: list[tuple[float, ...]], k: int = 10) -> list[int]:
    """Find k nearest neighbors in 5D holographic space.

    Rust: Optimized k-NN with SIMD distance
    Python fallback: Brute force search
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'holographic_5d_knn'):
        return cast(List[int], rust.holographic_5d_knn(list(query), [list(c) for c in coords], k))

    # Python fallback
    distances = [(i, holographic_5d_distance(query, coord)) for i, coord in enumerate(coords)]
    distances.sort(key=lambda x: x[1])
    return [idx for idx, _ in distances[:k]]


def holographic_5d_centroid(coords: list[tuple[float, ...]]) -> tuple[float, ...]:
    """Compute centroid of 5D holographic coordinates.

    Rust: SIMD parallel reduction
    Python fallback: Standard mean computation
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'holographic_5d_centroid'):
        result = rust.holographic_5d_centroid([list(c) for c in coords])
        return tuple(result)

    # Python fallback
    if not coords:
        return (0.0, 0.0, 0.0, 0.0, 0.0)

    n = len(coords)
    sums = [0.0] * 5
    for coord in coords:
        for i, val in enumerate(coord):
            sums[i] += val
    return tuple(s / n for s in sums)


# ============================================================================
# CONSTELLATION GRID OPERATIONS
# ============================================================================

def grid_density_scan(points: list[tuple[float, float]], grid_size: int = 50) -> list[list[int]]:
    """Scan 2D point cloud for density grid.

    Rust: Parallel grid binning with SIMD
    Python fallback: Standard grid counting
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'grid_density_scan'):
        return cast(List[List[int]], rust.grid_density_scan(points, grid_size))

    # Python fallback
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


# ============================================================================
# KEYWORD EXTRACTION
# ============================================================================

def extract_keywords(text: str, top_k: int = 10) -> list[tuple[str, float]]:
    """Extract top-k keywords from text using TF-IDF.

    Rust: Optimized tokenization + TF-IDF with SIMD
    Python fallback: Basic frequency counting
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'extract_keywords'):
        return cast(List[Tuple[str, float]], rust.extract_keywords(text, top_k))

    # Python fallback - simple word frequency
    import re
    from collections import Counter

    words = re.findall(r'\b\w+\b', text.lower())
    # Filter stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = [w for w in words if w not in stopwords and len(w) > 2]

    counter = Counter(words)
    return [(str(word), float(count)) for word, count in counter.most_common(top_k)]


# ============================================================================
# VECTOR BATCH OPERATIONS
# ============================================================================

def batch_normalize(vectors: list[list[float]]) -> list[list[float]]:
    """Normalize vectors to unit length.

    Rust: Parallel SIMD normalization
    Python fallback: Sequential normalization
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'batch_normalize'):
        return cast(List[List[float]], rust.batch_normalize(vectors))

    # Python fallback
    import math
    normalized = []
    for vec in vectors:
        mag = math.sqrt(sum(x * x for x in vec))
        if mag > 0:
            normalized.append([x / mag for x in vec])
        else:
            normalized.append(vec)
    return normalized


def batch_centroid(vectors: list[list[float]]) -> list[float]:
    """Compute centroid of vector batch.

    Rust: SIMD parallel reduction
    Python fallback: Standard mean
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'batch_centroid'):
        return cast(List[float], rust.batch_centroid(vectors))

    # Python fallback
    if not vectors:
        return []

    dim = len(vectors[0])
    centroid = [0.0] * dim
    for vec in vectors:
        for i, val in enumerate(vec):
            centroid[i] += val
    return [c / len(vectors) for c in centroid]


def batch_topk_cosine(query: list[float], vectors: list[list[float]], k: int = 10) -> list[tuple[int, float]]:
    """Find top-k most similar vectors by cosine similarity.

    Rust: Heap-based top-k with parallel SIMD
    Python fallback: Sort-based approach
    """
    rust = _init_rust()
    if rust and hasattr(rust, 'batch_topk_cosine'):
        return cast(List[Tuple[int, float]], rust.batch_topk_cosine(query, vectors, k))

    return top_k_nearest(query, vectors, k)


# ============================================================================
# STATUS FUNCTIONS
# ============================================================================

def simd_status() -> dict[str, Any]:
    """Get unified SIMD status."""
    _init_rust()
    return {
        "rust_available": _rust_available,
        "operations": [
            "cosine_similarity", "batch_cosine",
            "pairwise_distance_matrix", "top_k_nearest",
            "holographic_5d_distance", "holographic_5d_knn", "holographic_5d_centroid",
            "grid_density_scan", "extract_keywords",
            "batch_normalize", "batch_centroid", "batch_topk_cosine"
        ],
        "modules_unified": 6,
        "loc_saved": "~800 LOC"
    }


# Legacy compatibility - individual status functions
def simd_cosine_status() -> dict[str, Any]:
    return {"module": "cosine", **simd_status()}

def simd_distance_status() -> dict[str, Any]:
    return {"module": "distance", **simd_status()}

def simd_holographic_status() -> dict[str, Any]:
    return {"module": "holographic", **simd_status()}

def simd_constellation_status() -> dict[str, Any]:
    return {"module": "constellation", **simd_status()}

def simd_keywords_status() -> dict[str, Any]:
    return {"module": "keywords", **simd_status()}

def simd_vector_batch_status() -> dict[str, Any]:
    return {"module": "vector_batch", **simd_status()}


__all__ = [
    # Cosine operations
    "cosine_similarity", "batch_cosine",
    # Distance operations
    "pairwise_distance_matrix", "top_k_nearest", "cosine_similarity_zig",
    # Holographic 5D operations
    "holographic_5d_distance", "holographic_5d_knn", "holographic_5d_centroid",
    # Constellation operations
    "grid_density_scan",
    # Keyword extraction
    "extract_keywords",
    # Vector batch operations
    "batch_normalize", "batch_centroid", "batch_topk_cosine",
    # Status functions
    "simd_status",
    "simd_cosine_status", "simd_distance_status", "simd_holographic_status",
    "simd_constellation_status", "simd_keywords_status", "simd_vector_batch_status",
]
