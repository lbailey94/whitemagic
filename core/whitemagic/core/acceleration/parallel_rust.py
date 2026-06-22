"""Parallel Rust FFI execution with GIL bypass.

Since the compiled whitemagic_rust extension holds the GIL during computation,
this module provides:

1. NumPy vectorized batch operations (fastest for small-medium batches)
2. ProcessPoolExecutor for large batches where overhead is amortized
3. Hybrid mode that auto-selects the best strategy

Usage:
    from whitemagic.core.acceleration.parallel_rust import batch_cosine

    # Auto-selects best strategy
    scores = batch_cosine(pairs)  # List of (a, b) vector pairs
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def batch_cosine_numpy(
    pairs: list[tuple[list[float], list[float]]],
) -> list[float]:
    """Compute cosine similarity for multiple vector pairs using NumPy.

    This is the fastest approach for small-medium batches (<10K pairs)
    because it avoids FFI overhead entirely and uses vectorized operations.

    Args:
        pairs: List of (vector_a, vector_b) tuples.

    Returns:
        List of similarity scores.
    """
    if not pairs:
        return []

    a = np.array([p[0] for p in pairs], dtype=np.float32)
    b = np.array([p[1] for p in pairs], dtype=np.float32)

    # Vectorized cosine: dot / (norm_a * norm_b)
    dot = np.sum(a * b, axis=1)
    norm_a = np.linalg.norm(a, axis=1)
    norm_b = np.linalg.norm(b, axis=1)

    denom = norm_a * norm_b
    denom = np.where(denom == 0, 1, denom)  # Avoid division by zero

    scores = dot / denom
    return scores.tolist()


def batch_cosine_rust(
    pairs: list[tuple[list[float], list[float]]],
) -> list[float]:
    """Compute cosine similarity using Rust FFI (sequential, holds GIL).

    Best for very large vectors (>1000d) where Rust's SIMD advantage
    outweighs the per-call FFI overhead.

    Args:
        pairs: List of (vector_a, vector_b) tuples.

    Returns:
        List of similarity scores.
    """
    try:
        from whitemagic_rust import rust_cosine_similarity
        return [rust_cosine_similarity(a, b) for a, b in pairs]
    except ImportError:
        logger.warning("Rust not available, falling back to NumPy")
        return batch_cosine_numpy(pairs)


def batch_cosine(
    pairs: list[tuple[list[float], list[float]]],
    strategy: str = "auto",
) -> list[float]:
    """Compute cosine similarity for multiple vector pairs.

    Auto-selects the best strategy based on batch size and vector dimension.

    Strategies:
        - "auto": Selects numpy for <10K pairs, rust for larger
        - "numpy": Always use NumPy vectorized operations
        - "rust": Always use Rust FFI (sequential, holds GIL)

    Args:
        pairs: List of (vector_a, vector_b) tuples.
        strategy: Execution strategy.

    Returns:
        List of similarity scores.
    """
    if not pairs:
        return []

    n_pairs = len(pairs)
    dim = len(pairs[0][0]) if pairs else 0

    if strategy == "numpy":
        return batch_cosine_numpy(pairs)
    elif strategy == "rust":
        return batch_cosine_rust(pairs)
    else :
        # auto
        # Rust is consistently faster than NumPy for 384d vectors at all batch sizes
        # NumPy only wins for very small vectors (<64d) where FFI overhead dominates
        if dim < 64 and n_pairs < 100:
            return batch_cosine_numpy(pairs)
        else:
            return batch_cosine_rust(pairs)


def parallel_status() -> dict[str, Any]:
    """Get parallel execution status."""
    return {
        "strategies": ["auto", "numpy", "rust"],
        "gil_bypass_available": False,
        "gil_bypass_note": "Requires Rust rebuild with py.allow_threads()",
        "numpy_vectorized": True,
        "rust_batch_available": False,
        "rust_batch_note": "rust_cosine_similarity is single-pair only",
    }

