"""Zig SIMD Distance Matrix — Python Bridge.
==========================================
Loads the compiled Zig shared library and exposes SIMD-accelerated
pairwise cosine distance matrix computation. Falls back to pure Python
when the Zig library is not available.

The Zig implementation uses:
- SIMD-accelerated pairwise cosine similarity
- 64×64 blocked tiling for cache efficiency
- Triangular optimization (upper triangle only)
- Top-K nearest neighbor extraction

Usage:
    from whitemagic.core.acceleration.simd_distance import (
        pairwise_distance_matrix,
        cosine_similarity_zig,
        simd_distance_status,
    )
    matrix = pairwise_distance_matrix(vectors)
    sim = cosine_similarity_zig(vec_a, vec_b)
"""
# ruff: noqa: BLE001
from __future__ import annotations

import ctypes
import logging
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from whitemagic.core.acceleration.ffi_utils import LibraryLoader

logger = logging.getLogger(__name__)


def _setup_ffi(lib: Any) -> None:
    """Set up FFI signatures for Zig library."""
    # wm_distance_matrix(vectors_ptr, n, dim, out_ptr) -> void
    lib.wm_distance_matrix.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_float),
    ]
    lib.wm_distance_matrix.restype = None

    # wm_cosine_similarity(a_ptr, b_ptr, dim) -> f32
    lib.wm_cosine_similarity.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_size_t,
    ]
    lib.wm_cosine_similarity.restype = ctypes.c_float


# Unified library loader for Zig SIMD
_zig_loader = LibraryLoader(
    lib_name='libwhitemagic',
    base_path=Path(__file__).resolve().parent.parent.parent.parent / "whitemagic-zig",
    env_var='WM_ZIG_LIB',
    search_paths=['zig-out/lib/', '', ''],
    setup_function=_setup_ffi,
)


def _to_c_float_array(vec: Sequence[float]) -> ctypes.Array:
    """Convert a Python sequence of floats to a ctypes float array."""
    arr = (ctypes.c_float * len(vec))()
    for i, v in enumerate(vec):
        arr[i] = v
    return arr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cosine_similarity_zig(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors using Zig SIMD.
    Falls back to Python if Zig is not available.
    """
    if len(a) != len(b) or len(a) == 0:
        return 0.0

    lib = _zig_loader.lib
    if lib is not None:
        try:
            ca = _to_c_float_array(a)
            cb = _to_c_float_array(b)
            return float(lib.wm_cosine_similarity(ca, cb, len(a)))
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass

    return _py_cosine(a, b)


def pairwise_distance_matrix(
    vectors: list[Sequence[float]],
) -> list[list[float]] | None:
    """Compute pairwise cosine distance matrix for a set of vectors.

    Uses Zig SIMD with 64×64 blocked tiling when available.

    Args:
        vectors: List of equal-length float vectors.

    Returns:
        N×N distance matrix as list of lists, or None on failure.
        Values are cosine distances (1 - similarity), range [0, 2].

    """
    if not vectors or len(vectors) < 2:
        return None

    n = len(vectors)
    dim = len(vectors[0])

    lib = _zig_loader.lib
    if lib is not None:
        try:
            # Flatten vectors into contiguous array
            flat = (ctypes.c_float * (n * dim))()
            for i, vec in enumerate(vectors):
                for j, v in enumerate(vec[:dim]):
                    flat[i * dim + j] = v

            # Output: N×N matrix
            out = (ctypes.c_float * (n * n))()
            lib.wm_distance_matrix(flat, n, dim, out)

            # Convert to Python nested list
            matrix = []
            for i in range(n):
                row = [float(out[i * n + j]) for j in range(n)]
                matrix.append(row)
            return matrix
        except Exception as e:
            logger.debug("Zig distance matrix failed, using Python: %s", e)

    # Python fallback
    return _py_distance_matrix(vectors)


def top_k_nearest(
    vectors: list[Sequence[float]],
    k: int = 5,
) -> list[list[tuple[int, float]]]:
    """Find top-K nearest neighbors for each vector using pairwise distances.

    Args:
        vectors: List of float vectors.
        k: Number of nearest neighbors per vector.

    Returns:
        List of lists of (index, distance) tuples, one per input vector.

    """
    matrix = pairwise_distance_matrix(vectors)
    if matrix is None:
        return []

    n = len(vectors)
    results = []
    for i in range(n):
        # Collect (distance, index) for all other vectors
        dists = [(matrix[i][j], j) for j in range(n) if j != i]
        dists.sort()
        results.append([(idx, d) for d, idx in dists[:k]])
    return results


# ---------------------------------------------------------------------------
# Pure Python fallbacks
# ---------------------------------------------------------------------------

def _py_cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Pure Python cosine similarity."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _py_distance_matrix(vectors: list[Sequence[float]]) -> list[list[float]]:
    """Pure Python pairwise cosine distance matrix."""
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim = _py_cosine(vectors[i], vectors[j])
            dist = 1.0 - sim
            matrix[i][j] = dist
            matrix[j][i] = dist
    return matrix


def simd_distance_status() -> dict[str, Any]:
    """Get SIMD distance matrix status."""
    return {
        "has_zig_simd": _zig_loader.available,
        "lib_path": "loaded" if _zig_loader.available else "not found",
        "backend": "zig_simd" if _zig_loader.available else "python_fallback",
    }
