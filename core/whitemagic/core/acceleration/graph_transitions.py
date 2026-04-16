"""Zig SIMD Graph Transitions — Python Bridge.
===========================================
Loads the compiled Zig shared library and exposes SIMD-accelerated
transition probability computation for graph walker.

Usage:
    from whitemagic.core.acceleration.graph_transitions import (
        transition_batch, transition_single, graph_transitions_status
    )
    probs = transition_batch(semantic, gravity, recency, staleness, weights)
"""
from __future__ import annotations

import ctypes
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lib = None
_lib_lock = threading.Lock()
_HAS_ZIG = False


def _find_zig_lib() -> str | None:
    """Locate the compiled Zig shared library."""
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

            # wm_graph_transition_batch(semantic_ptr, gravity_ptr, recency_ptr, staleness_ptr, weights_ptr, n, probs_out)
            lib.wm_graph_transition_batch.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_float),
            ]
            lib.wm_graph_transition_batch.restype = None

            # wm_graph_transition_single(semantic_sim, galactic_gravity, recency, staleness, w_semantic, w_gravity, w_recency, w_staleness)
            lib.wm_graph_transition_single.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ]
            lib.wm_graph_transition_single.restype = ctypes.c_float

            _lib = lib
            _HAS_ZIG = True
            logger.info("Zig SIMD graph transitions loaded: path=%s", path)
            return lib
        except Exception as e:
            logger.debug("Failed to load Zig graph transitions: %s", e)
            return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transition_single(
    semantic_sim: float,
    galactic_gravity: float,
    recency: float,
    staleness: float,
    weights: tuple[float, float, float, float] = (0.4, 0.3, 0.2, 0.1),
) -> float:
    """Compute transition probability for a single edge.

    Args:
        semantic_sim: Semantic similarity score (0.0 to 1.0)
        galactic_gravity: Galactic gravity score (0.0 to 1.0)
        recency: Recency score (0.0 to 1.0)
        staleness: Staleness score (0.0 to 1.0, lower is better)
        weights: Tuple of (w_semantic, w_gravity, w_recency, w_staleness)

    Returns:
        Transition probability in [0.0, 1.0]
    """
    lib = _load_lib()
    if lib is not None:
        try:
            return float(lib.wm_graph_transition_single(
                semantic_sim, galactic_gravity, recency, staleness,
                weights[0], weights[1], weights[2], weights[3]
            ))
        except Exception as e:
            logger.debug("Zig transition_single failed: %s", e)

    # Python fallback
    prob = (
        weights[0] * semantic_sim +
        weights[1] * galactic_gravity +
        weights[2] * recency +
        weights[3] * (1.0 - staleness)
    )
    return max(0.0, min(1.0, prob))


def transition_batch(
    semantic: list[float],
    gravity: list[float],
    recency: list[float],
    staleness: list[float],
    weights: tuple[float, float, float, float] = (0.4, 0.3, 0.2, 0.1),
) -> list[float]:
    """Compute transition probabilities for a batch of edges.

    Args:
        semantic: List of semantic similarity scores
        gravity: List of galactic gravity scores
        recency: List of recency scores
        staleness: List of staleness scores
        weights: Tuple of (w_semantic, w_gravity, w_recency, w_staleness)

    Returns:
        List of transition probabilities in [0.0, 1.0]
    """
    n = len(semantic)
    if n == 0:
        return []
    if not (len(gravity) == len(recency) == len(staleness) == n):
        raise ValueError("All input arrays must have the same length")

    lib = _load_lib()
    if lib is not None:
        try:
            sem_arr = (ctypes.c_float * n)(*semantic)
            grav_arr = (ctypes.c_float * n)(*gravity)
            rec_arr = (ctypes.c_float * n)(*recency)
            stal_arr = (ctypes.c_float * n)(*staleness)
            weights_arr = (ctypes.c_float * 4)(*weights)
            probs_arr = (ctypes.c_float * n)()

            lib.wm_graph_transition_batch(
                sem_arr, grav_arr, rec_arr, stal_arr,
                weights_arr, n, probs_arr
            )
            return [float(probs_arr[i]) for i in range(n)]
        except Exception as e:
            logger.debug("Zig transition_batch failed: %s", e)

    # Python fallback
    return [
        max(0.0, min(1.0,
            weights[0] * semantic[i] +
            weights[1] * gravity[i] +
            weights[2] * recency[i] +
            weights[3] * (1.0 - staleness[i])
        ))
        for i in range(n)
    ]


def graph_transitions_status() -> dict[str, Any]:
    """Get graph transitions acceleration status."""
    _load_lib()
    return {
        "has_zig_simd": _HAS_ZIG,
        "lib_path": _find_zig_lib() or "not found",
        "backend": "zig_simd" if _HAS_ZIG else "python_fallback",
    }
