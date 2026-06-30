"""Embedding Similarity — Cosine and other similarity metrics for embeddings."""

from __future__ import annotations

import math
import struct
from typing import Any


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def batch_cosine_similarity(query: list[float], vectors: list[list[float]]) -> list[float]:
    """Compute cosine similarity between a query and multiple vectors."""
    return [cosine_similarity(query, v) for v in vectors]


def batch_cosine_similarity_numpy(query: Any, vectors: Any, pre_normalized: bool = False) -> Any:
    """NumPy-accelerated batch cosine similarity (fallback to pure Python)."""
    try:
        import numpy as _np
        q = _np.asarray(query, dtype=_np.float32)
        v = _np.asarray(vectors, dtype=_np.float32)
        if v.ndim == 1:
            v = v.reshape(1, -1)
        if pre_normalized:
            # Vectors are already unit-normalized — just dot product
            scores = v @ q
        else:
            q_norm = _np.linalg.norm(q)
            v_norms = _np.linalg.norm(v, axis=1)
            denom = v_norms * q_norm
            denom[denom == 0] = 1.0  # avoid division by zero
            scores = (v @ q) / denom
        return scores
    except ImportError:
        # Fallback when numpy is not available
        q = query.tolist() if hasattr(query, "tolist") else list(query)
        vs = vectors.tolist() if hasattr(vectors, "tolist") else [list(vx) for vx in vectors]
        return batch_cosine_similarity(q, vs)


def pack_embedding(embedding: list[float]) -> bytes:
    """Pack a float embedding into bytes."""
    return struct.pack(f"<{len(embedding)}f", *embedding)


def unpack_embedding(data: bytes) -> list[float]:
    """Unpack bytes into a float embedding."""
    count = len(data) // 4
    return list(struct.unpack(f"<{count}f", data))
