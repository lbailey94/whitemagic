# ruff: noqa: BLE001
"""Zig SIMD Cosine Similarity — Python Bridge.
=============================================================
Loads the compiled Zig shared library and exposes SIMD-accelerated
cosine similarity for embedding vectors. Falls back to pure Python
when the Zig library is not available.

Uses the universal numpy bridge for zero-copy FFI.

Usage:
    from whitemagic.core.acceleration.simd_cosine import cosine_similarity, batch_cosine
    score = cosine_similarity(vec_a, vec_b)
    scores = batch_cosine(query, [vec1, vec2, vec3])
"""

from __future__ import annotations

import ctypes
import logging
import math
import os
import struct
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from whitemagic.core.acceleration.polyglot_numpy_bridge import (
    to_flat_ptr,
    to_ptr,
)

logger = logging.getLogger(__name__)

_lib = None
_lib_lock = threading.Lock()
_HAS_ZIG = False


# TopKResult structure for wm_vector_top_k
class TopKResult(ctypes.Structure):
    """TopKResult: top k result."""

    _fields_ = [("index", ctypes.c_uint32), ("score", ctypes.c_float)]


# Pre-allocated buffer pool to avoid repeated allocations
_buffer_pool: dict[int, Any] = {}  # size -> ctypes array
_pool_lock = threading.Lock()


def _get_buffer(size: int) -> Any:
    """Get or create a pre-allocated float buffer."""
    with _pool_lock:
        if size not in _buffer_pool:
            _buffer_pool[size] = (ctypes.c_float * size)()
        return _buffer_pool[size]


def _find_zig_lib() -> str | None:
    """Locate the compiled Zig shared library."""
    base = (
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "polyglot"
        / "whitemagic-zig"
    )
    candidates = [
        os.environ.get("WM_ZIG_LIB", ""),
        # Shared lib (dynamic) — primary target
        str(base / "zig-out" / "lib" / "libwhitemagic.so"),
        str(base / "libwhitemagic.so"),
        str(base / "zig-out" / "lib" / "libwhitemagic.dylib"),
        # Legacy name (static lib name used as .so)
        str(base / "zig-out" / "lib" / "libwhitemagic-zig.so"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _load_lib() -> Any:
    """Load the Zig shared library."""
    global _lib, _HAS_ZIG
    if _lib is not None:
        return _lib
    with _lib_lock:
        if _lib is not None:
            return _lib
        path = _find_zig_lib()
        if not path:
            logger.debug("Zig SIMD library not found — using Python fallback")
            return None
        try:
            lib = ctypes.CDLL(path)

            # wm_simd_cosine(a_ptr, b_ptr, len) -> f32
            lib.wm_simd_cosine.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
            ]
            lib.wm_simd_cosine.restype = ctypes.c_float

            # wm_simd_batch_cosine(query_ptr, vectors_ptr, dim, n, scores_ptr)
            lib.wm_simd_batch_cosine.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_float),
            ]
            lib.wm_simd_batch_cosine.restype = None

            # wm_simd_lane_width() -> usize
            lib.wm_simd_lane_width.argtypes = []
            lib.wm_simd_lane_width.restype = ctypes.c_size_t

            # wm_vector_top_k(query_ptr, vectors_ptr, dim, n_vectors, k, results_ptr) -> usize
            # TopKResult = struct { index: u32, score: f32 } = 8 bytes
            lib.wm_vector_top_k.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.c_size_t,
                ctypes.c_size_t,
                ctypes.POINTER(TopKResult),
            ]
            lib.wm_vector_top_k.restype = ctypes.c_size_t

            _lib = lib
            _HAS_ZIG = True
            lane = lib.wm_simd_lane_width()
            logger.info("Zig SIMD loaded: lane_width=%d, path=%s", lane, path)
            return lib
        except Exception as e:
            logger.debug("Failed to load Zig SIMD library: %s", e)
            return None


def _to_c_array(vec: Sequence[float]) -> Any:
    """Convert a Python sequence of floats to a ctypes float array.

    Uses numpy buffer protocol for zero-copy when available (avoids
    O(n) element-by-element copy that the FFI analysis identified as
    a significant overhead for high-frequency calls).
    """
    try:
        import numpy as np

        if isinstance(vec, np.ndarray) and vec.dtype == np.float32:
            return vec.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        np_arr = np.asarray(vec, dtype=np.float32)
        return np_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    except ImportError:
        logger.debug("Optional dependency unavailable: ImportError")
    c_arr = (ctypes.c_float * len(vec))()
    for i, v in enumerate(vec):
        c_arr[i] = v
    return c_arr


def _to_c_array_fast(vec: Sequence[float]) -> Any:
    """Fast conversion using pre-allocated buffer + struct.unpack.

    For 384-d vectors, this is ~3x faster than element-by-element assignment.
    """
    n = len(vec)
    buf = _get_buffer(n)
    # struct.pack is implemented in C, much faster than Python loop
    packed = struct.pack(f"{n}f", *vec)
    ctypes.memmove(buf, packed, n * 4)
    return buf


def _py_cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Pure Python cosine similarity."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors.
    Uses Zig SIMD if available, Python fallback otherwise.

    Accepts numpy arrays for zero-copy FFI.
    """
    if len(a) != len(b) or len(a) == 0:
        return 0.0

    lib = _load_lib()
    if lib is not None:
        # Zero-copy path for numpy arrays
        if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            ca = to_ptr(a)
            cb = to_ptr(b)
            return float(lib.wm_simd_cosine(ca, cb, len(a)))
        # Fallback for Python sequences
        ca = _to_c_array(a)
        cb = _to_c_array(b)
        return float(lib.wm_simd_cosine(ca, cb, len(a)))

    return _py_cosine(a, b)


def batch_cosine(query: Sequence[float], vectors: list[Sequence[float]]) -> list[float]:
    """Compute cosine similarity between query and a batch of vectors.
    Uses Zig SIMD batch operation if available.

    Accepts numpy arrays for zero-copy FFI.
    """
    # Zero-copy path for numpy arrays
    if isinstance(vectors, np.ndarray) and isinstance(query, np.ndarray):
        dim = len(query)
        n = len(vectors)
        lib = _load_lib()
        if lib is not None:
            cq = to_ptr(query)
            flat, _ = to_flat_ptr(vectors)
            scores = (ctypes.c_float * n)()
            lib.wm_simd_batch_cosine(cq, flat, dim, n, scores)
            # Zero-copy result extraction via numpy frombuffer
            return np.ctypeslib.as_array(scores).tolist()

    if not vectors or not query:
        return []

    dim = len(query)
    n = len(vectors)

    lib = _load_lib()
    if lib is not None:
        # Use numpy for zero-copy flattening when available
        cq = np.asarray(query, dtype=np.float32)
        cq_ptr = to_ptr(cq)
        # Flatten all vectors into contiguous array in one operation
        flat_np = np.asarray(vectors, dtype=np.float32).ravel()
        flat_ptr = to_ptr(flat_np)
        scores = (ctypes.c_float * n)()
        lib.wm_simd_batch_cosine(cq_ptr, flat_ptr, dim, n, scores)
        # Zero-copy result extraction via numpy frombuffer
        return np.ctypeslib.as_array(scores).tolist()

    # Python fallback
    return [_py_cosine(query, v) for v in vectors]


def top_k_cosine(
    query: Sequence[float], vectors: list[Sequence[float]], k: int = 10
) -> list[tuple[int, float]]:
    """Find top-K most similar vectors to query using Zig SIMD.

    Returns list of (index, score) tuples sorted by descending similarity.
    Uses wm_vector_top_k for in-Zig top-K selection, avoiding full score array transfer.
    """
    if k <= 0:
        return []

    dim = len(query)
    n = len(vectors)
    if dim == 0 or n == 0:
        return []

    actual_k = min(k, n)

    lib = _load_lib()
    if lib is not None:
        # Zero-copy path
        cq = np.asarray(query, dtype=np.float32)
        cq_ptr = to_ptr(cq)
        flat_np = np.asarray(vectors, dtype=np.float32).ravel()
        flat_ptr = to_ptr(flat_np)

        results = (TopKResult * actual_k)()
        found = lib.wm_vector_top_k(cq_ptr, flat_ptr, dim, n, actual_k, results)

        return [(int(results[i].index), float(results[i].score)) for i in range(found)]

    # Python fallback: compute all scores, sort, take top-K
    scores = [_py_cosine(query, v) for v in vectors]
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    return indexed[:actual_k]


def simd_status() -> dict[str, Any]:
    """Get SIMD acceleration status."""
    lib = _load_lib()
    lane = 0
    if lib is not None:
        try:
            lane = lib.wm_simd_lane_width()
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
    return {
        "has_zig_simd": _HAS_ZIG,
        "lane_width": lane,
        "lib_path": _find_zig_lib() or "not found",
        "backend": "zig_simd" if _HAS_ZIG else "python_fallback",
    }
