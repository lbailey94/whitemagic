"""Zig Graph Bridge — Python ↔ Zig graph/search via ctypes FFI.
===============================================================
Exposes Zig-compiled graph traversal and SIMD similarity functions
from libwhitemagic.so to Python. Complements simd_cosine.py (batch
cosine) with graph-specific operations.

Functions exposed:
- wm_simd_cosine_f32   — SIMD cosine similarity (from search/simd_similarity.zig)
- wm_simd_dot_f32      — SIMD dot product
- wm_tokenize_count    — Zero-copy token count (from search/tokenizer.zig)
- wm_cosine_similarity — General cosine (from compute/distance_matrix.zig)

Falls back to pure Python/NumPy when Zig library is not available.

Usage:
    from whitemagic.core.acceleration.zig_graph_bridge import (
        zig_simd_cosine, zig_dot_product, zig_tokenize_count,
        zig_graph_bridge_status
    )
"""
from __future__ import annotations

import ctypes
import logging
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_lib: ctypes.CDLL | None = None
_lib_lock = threading.Lock()
_HAS_ZIG_GRAPH = False
_LIB_PATH: str | None = None


def _find_zig_lib() -> str | None:
    """Locate libwhitemagic.so."""
    base = Path(__file__).resolve().parent.parent.parent.parent
    candidates = [
        os.environ.get("ZIG_LIB_PATH", ""),
        str(base / "whitemagic-zig" / "zig-out" / "lib" / "libwhitemagic.so"),
        str(base / "whitemagic-zig" / "zig-out" / "lib" / "libwhitemagic.so.0"),
        "/usr/local/lib/libwhitemagic.so",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _init_lib() -> None:
    """Lazy-load the Zig shared library (thread-safe)."""
    global _lib, _HAS_ZIG_GRAPH, _LIB_PATH
    if _lib is not None or _HAS_ZIG_GRAPH:
        return
    with _lib_lock:
        if _lib is not None:
            return
        path = _find_zig_lib()
        if not path:
            logger.debug("zig_graph_bridge: libwhitemagic.so not found")
            return
        try:
            lib = ctypes.CDLL(path)

            # wm_simd_cosine_f32(a, b, dim) -> f32
            lib.wm_simd_cosine_f32.restype = ctypes.c_float
            lib.wm_simd_cosine_f32.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
            ]

            # wm_simd_dot_f32(a, b, dim) -> f32
            lib.wm_simd_dot_f32.restype = ctypes.c_float
            lib.wm_simd_dot_f32.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
            ]

            # wm_tokenize_count(text, len) -> usize
            lib.wm_tokenize_count.restype = ctypes.c_size_t
            lib.wm_tokenize_count.argtypes = [
                ctypes.c_char_p,
                ctypes.c_size_t,
            ]

            # wm_cosine_similarity(a, b, dim) -> f32 (from distance_matrix)
            lib.wm_cosine_similarity.restype = ctypes.c_float
            lib.wm_cosine_similarity.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
            ]

            _lib = lib
            _LIB_PATH = path
            _HAS_ZIG_GRAPH = True
            logger.info("zig_graph_bridge: loaded %s", path)
        except Exception as e:
            logger.debug("zig_graph_bridge: load failed: %s", e)


def _to_f32_ptr(vec: list[float] | np.ndarray) -> tuple[Any, int, np.ndarray]:
    """Convert a Python list or numpy array to a ctypes f32 pointer + length."""
    if isinstance(vec, np.ndarray):
        arr: np.ndarray = vec.astype(np.float32, copy=False)
    else:
        arr = np.array(vec, dtype=np.float32)
    ptr = arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    return ptr, len(arr), arr  # return arr to keep it alive


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def zig_simd_cosine(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
) -> float:
    """SIMD cosine similarity via Zig search/simd_similarity.zig.

    Falls back to NumPy if Zig unavailable.
    """
    _init_lib()
    if _HAS_ZIG_GRAPH and _lib is not None:
        try:
            pa, la, _a = _to_f32_ptr(a)
            pb, lb, _b = _to_f32_ptr(b)
            if la != lb or la == 0:
                return 0.0
            return float(_lib.wm_simd_cosine_f32(pa, pb, ctypes.c_size_t(la)))
        except Exception as e:
            logger.debug("zig_simd_cosine failed: %s", e)
    # NumPy fallback
    a_np = np.asarray(a, dtype=np.float32)
    b_np = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(a_np), np.linalg.norm(b_np)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / (na * nb))


def zig_dot_product(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
) -> float:
    """SIMD dot product via Zig."""
    _init_lib()
    if _HAS_ZIG_GRAPH and _lib is not None:
        try:
            pa, la, _a = _to_f32_ptr(a)
            pb, lb, _b = _to_f32_ptr(b)
            if la != lb or la == 0:
                return 0.0
            return float(_lib.wm_simd_dot_f32(pa, pb, ctypes.c_size_t(la)))
        except Exception as e:
            logger.debug("zig_dot_product failed: %s", e)
    return float(np.dot(np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)))


def zig_tokenize_count(text: str) -> int:
    """Zero-copy token count via Zig tokenizer.

    Returns number of whitespace-separated tokens. Falls back to Python split.
    """
    _init_lib()
    if _HAS_ZIG_GRAPH and _lib is not None:
        try:
            encoded = text.encode("utf-8")
            return int(_lib.wm_tokenize_count(encoded, ctypes.c_size_t(len(encoded))))
        except Exception as e:
            logger.debug("zig_tokenize_count failed: %s", e)
    return len(text.split())


def zig_batch_cosine(
    query: list[float] | np.ndarray,
    docs: list[list[float] | np.ndarray],
) -> list[float]:
    """Batch cosine similarity: query vs each doc vector.

    Uses Zig SIMD cosine for each pair. Falls back to NumPy vectorized.
    """
    _init_lib()
    if _HAS_ZIG_GRAPH and _lib is not None:
        try:
            results = []
            for doc in docs:
                results.append(zig_simd_cosine(query, doc))
            return results
        except Exception as e:
            logger.debug("zig_batch_cosine failed: %s", e)
    # NumPy vectorized fallback
    q = np.asarray(query, dtype=np.float32)
    q_norm = np.linalg.norm(q)
    if q_norm == 0:
        return [0.0] * len(docs)
    results = []
    for doc in docs:
        d = np.asarray(doc, dtype=np.float32)
        d_norm = np.linalg.norm(d)
        if d_norm == 0:
            results.append(0.0)
        else:
            results.append(float(np.dot(q, d) / (q_norm * d_norm)))
    return results


def zig_graph_bridge_status() -> dict[str, Any]:
    """Get Zig graph bridge status."""
    _init_lib()
    return {
        "available": _HAS_ZIG_GRAPH,
        "has_zig_graph": _HAS_ZIG_GRAPH,
        "lib_path": _LIB_PATH or "not found",
        "functions": ["wm_simd_cosine_f32", "wm_simd_dot_f32",
                      "wm_tokenize_count", "wm_cosine_similarity"]
        if _HAS_ZIG_GRAPH else [],
        "backend": "zig_simd_graph" if _HAS_ZIG_GRAPH else "numpy_fallback",
    }
