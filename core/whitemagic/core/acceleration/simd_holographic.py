"""Zig SIMD Holographic 5D — Python Bridge.
=========================================
Loads the compiled Zig shared library and exposes SIMD-accelerated 5D
holographic coordinate operations. Falls back to pure Python when the
Zig library is not available.

The Zig implementation provides:
- Weighted 5D distance computation (SIMD vectorized)
- K-nearest-neighbor search in 5D space
- Zone classification from galactic distance
- Centroid and spread computation for clusters

Usage:
    from whitemagic.core.acceleration.simd_holographic import (
        holographic_5d_distance, holographic_5d_knn, simd_holographic_status
    )
"""
from __future__ import annotations

import ctypes
import logging
import math
import threading
from pathlib import Path
from typing import Any, cast

import numpy as np

logger = logging.getLogger(__name__)

_lib = None
_lib_lock = threading.Lock()
_HAS_ZIG = False


def _find_zig_lib() -> str | None:
    """Locate the compiled Zig shared library."""
    import os
    base = Path(__file__).resolve().parent.parent.parent.parent / "whitemagic-zig"
    candidates = [
        os.environ.get("WM_ZIG_LIB", ""),
        str(base / "zig-out" / "lib" / "libwhitemagic.so"),
        str(base / "libwhitemagic.so"),
        str(base / "zig-out" / "lib" / "libwhitemagic.dylib"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _load_lib() -> Any:
    """Load the Zig shared library and set up holographic 5D FFI."""
    global _lib, _HAS_ZIG
    if _lib is not None:
        return _lib
    with _lib_lock:
        if _lib is not None:
            return _lib
        path = _find_zig_lib()
        if not path:
            logger.debug("Zig SIMD library not found — using Python fallback for holographic 5D")
            return None
        try:
            lib = ctypes.CDLL(path)

            # Check for holographic 5D exports
            if not hasattr(lib, "wm_holographic_5d_distance"):
                logger.debug("Zig library missing holographic 5D symbols — using Python fallback")
                return None

            # wm_holographic_5d_distance(a_ptr, b_ptr, weights_ptr) -> f32
            lib.wm_holographic_5d_distance.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
            ]
            lib.wm_holographic_5d_distance.restype = ctypes.c_float

            # Circular Convolution (HRR Bind)
            if hasattr(lib, "simd_circular_convolution"):
                lib.simd_circular_convolution.argtypes = [
                    ctypes.POINTER(ctypes.c_float),
                    ctypes.POINTER(ctypes.c_float),
                    ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_float),
                ]
                lib.simd_circular_convolution.restype = None

            # Circular Correlation (HRR Unbind)
            if hasattr(lib, "simd_circular_correlation"):
                lib.simd_circular_correlation.argtypes = [
                    ctypes.POINTER(ctypes.c_float),
                    ctypes.POINTER(ctypes.c_float),
                    ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_float),
                ]
                lib.simd_circular_correlation.restype = None

            _lib = lib
            _HAS_ZIG = True
            logger.info("Zig SIMD holographic 5D loaded: path=%s", path)
            return lib
        except Exception as e:
            logger.debug("Failed to load Zig holographic 5D: %s", e)
            return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Default 5D weights: X(logic/emotion), Y(micro/macro), Z(time), W(importance), V(vitality)
_DEFAULT_WEIGHTS = (1.0, 1.0, 0.8, 1.2, 1.5)


def holographic_5d_distance(
    a: tuple[float, ...],
    b: tuple[float, ...],
    weights: tuple[float, ...] = _DEFAULT_WEIGHTS,
) -> float:
    """Compute weighted 5D distance between two holographic coordinates."""
    lib = _load_lib()
    if lib is not None:
        try:
            a_arr = (ctypes.c_float * 5)(*a[:5])
            b_arr = (ctypes.c_float * 5)(*b[:5])
            w_arr = (ctypes.c_float * 5)(*weights[:5])
            return float(lib.wm_holographic_5d_distance(a_arr, b_arr, w_arr))
        except Exception as e:
            logger.debug("Zig holographic_5d_distance failed, using Python: %s", e)

    return _py_weighted_distance(a, b, weights)


def circular_convolution(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """SIMD-accelerated circular convolution via Zig."""
    dim = len(a)
    lib = _load_lib()
    if lib is not None and hasattr(lib, "simd_circular_convolution"):
        try:
            out: np.ndarray = np.zeros(dim, dtype=np.float32)
            a_ptr = a.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            b_ptr = b.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            out_ptr = out.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            lib.simd_circular_convolution(a_ptr, b_ptr, dim, out_ptr)
            return out
        except Exception as e:
            logger.debug("Zig circular_convolution failed: %s", e)
    
    # Fallback to FFT
    result: np.ndarray = np.real(np.fft.ifft(np.fft.fft(a) * np.fft.fft(b))).astype(np.float32)
    return cast(np.ndarray, result)


def circular_correlation(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """SIMD-accelerated circular correlation via Zig."""
    dim = len(a)
    lib = _load_lib()
    if lib is not None and hasattr(lib, "simd_circular_correlation"):
        try:
            out: np.ndarray = np.zeros(dim, dtype=np.float32)
            a_ptr = a.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            b_ptr = b.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            out_ptr = out.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            lib.simd_circular_correlation(a_ptr, b_ptr, dim, out_ptr)
            return out
        except Exception as e:
            logger.debug("Zig circular_correlation failed: %s", e)
            
    # Fallback to FFT correlation
    result = np.real(np.fft.ifft(np.conj(np.fft.fft(b)) * np.fft.fft(a))).astype(np.float32)
    return cast(np.ndarray, result)


def _py_weighted_distance(
    a: tuple[float, ...],
    b: tuple[float, ...],
    weights: tuple[float, ...],
) -> float:
    """Pure Python weighted Euclidean distance in 5D."""
    total = 0.0
    for i in range(min(5, len(a), len(b))):
        w = weights[i] if i < len(weights) else 1.0
        diff = a[i] - b[i]
        total += w * diff * diff
    return math.sqrt(total)


def holographic_5d_knn(
    query: tuple[float, ...],
    points: list[tuple[str, tuple[float, ...]]],
    k: int = 10,
    weights: tuple[float, ...] = _DEFAULT_WEIGHTS,
) -> list[tuple[str, float]]:
    """Find K nearest neighbors in 5D holographic space.

    Args:
        query: 5D coordinate to search from.
        points: List of (id, coordinate) pairs.
        k: Number of neighbors to return.
        weights: Dimension weights for distance computation.

    Returns:
        List of (id, distance) pairs sorted by distance.

    """
    distances = []
    for pid, coord in points:
        d = holographic_5d_distance(query, coord, weights)
        distances.append((pid, d))
    distances.sort(key=lambda x: x[1])
    return distances[:k]


def holographic_5d_centroid(
    points: list[tuple[float, ...]],
) -> tuple[float, ...]:
    """Compute the centroid of a set of 5D points."""
    if not points:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    n = len(points)
    centroid = [0.0] * 5
    for p in points:
        for i in range(min(5, len(p))):
            centroid[i] += p[i]
    return tuple(c / n for c in centroid)


def simd_holographic_status() -> dict[str, Any]:
    """Get SIMD holographic 5D status."""
    _load_lib()
    return {
        "has_zig_simd": _HAS_ZIG,
        "lib_path": _find_zig_lib() or "not found",
        "backend": "zig_simd" if _HAS_ZIG else "python_fallback",
    }
