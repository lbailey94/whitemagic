"""HRR Bridge — Python interface to Rust hexagram HRR engine.

Connects the Rust hexagram_hrr module (Holographic Reduced Representations)
to the Python oracle system. Provides synergy detection, interaction scoring,
and hexagram superposition via PyO3 bindings.

Gracefully degrades to pure-Python fallback when the Rust extension is unavailable.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

_rust_available = False
try:
    import whitemagic_rs as _wmr

    _rust_available = True
except ImportError:
    _wmr = None  # type: ignore[assignment]

# Lazy-loaded Python fallback vectors (only computed if Rust unavailable)
_py_vectors: dict[int, list[float]] | None = None
_HRR_DIM = 64


def _seeded_vector(seed: int, dim: int) -> list[float]:
    """Generate a deterministic unit vector from a seed (Python fallback)."""
    import random

    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1e-12
    return [v / norm for v in vec]


def _king_wen_to_index(kw: int) -> int:
    """Convert King Wen number (1-64) to vector index (0-63)."""
    return kw - 1


def _get_py_vectors() -> dict[int, list[float]]:
    """Build Python-fallback HRR vectors for all 64 hexagrams."""
    global _py_vectors
    if _py_vectors is not None:
        return _py_vectors
    _py_vectors = {}
    for kw in range(1, 65):
        seed = kw * 7919  # Prime-based deterministic seed
        _py_vectors[kw] = _seeded_vector(seed, _HRR_DIM)
    return _py_vectors


def _py_cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    return dot / (na * nb)


class HRRBridge:
    """Bridge to Rust hexagram HRR engine with Python fallback.

    Provides:
    - synergy_for(kw): Find hexagrams that resonate with a given hexagram
    - interaction_score(kw1, kw2): HRR cosine similarity between two hexagrams
    - superpose_hexagrams(kw1, kw2): Superpose two hexagram HRR vectors
    - interaction_matrix(): Full 64x64 interaction matrix
    """

    def __init__(self) -> None:
        self._available = _rust_available

    @property
    def available(self) -> bool:
        """True if the Rust HRR engine is available."""
        return self._available

    def synergy_for(self, king_wen: int, threshold: float = 0.3) -> list[dict[str, Any]]:
        """Get synergistic hexagrams for a given primary hexagram.

        Args:
            king_wen: King Wen number of the primary hexagram (1-64).
            threshold: Minimum HRR cosine similarity to count as synergistic.

        Returns:
            List of {"hexagram": int, "similarity": float} sorted by similarity descending.
        """
        if self._available:
            try:
                all_syn = _wmr.hexagram_detect_synergies_py(threshold)
                results = [
                    {"hexagram": int(b if a == king_wen else a), "similarity": float(sim)}
                    for a, b, sim in all_syn
                    if a == king_wen or b == king_wen
                ]
                results.sort(key=lambda x: x["similarity"], reverse=True)
                return results
            except Exception as exc:
                logger.debug("Rust synergy_for failed, falling back: %s", exc)

        # Python fallback
        vectors = _get_py_vectors()
        results = []
        for kw in range(1, 65):
            if kw == king_wen:
                continue
            sim = _py_cosine_sim(vectors.get(king_wen, []), vectors.get(kw, []))
            if sim > threshold:
                results.append({"hexagram": kw, "similarity": round(sim, 6)})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    def interaction_score(self, kw1: int, kw2: int) -> float:
        """Get HRR interaction score (cosine similarity) between two hexagrams.

        Args:
            kw1: King Wen number of first hexagram (1-64).
            kw2: King Wen number of second hexagram (1-64).

        Returns:
            Cosine similarity in [-1, 1].
        """
        if self._available:
            try:
                return float(_wmr.hexagram_interaction_score_py(kw1, kw2))
            except Exception as exc:
                logger.debug("Rust interaction_score failed, falling back: %s", exc)

        vectors = _get_py_vectors()
        return _py_cosine_sim(vectors.get(kw1, []), vectors.get(kw2, []))

    def superpose_hexagrams(self, kw1: int, kw2: int) -> list[float]:
        """Superpose two hexagram HRR vectors.

        Args:
            kw1: King Wen number of first hexagram (1-64).
            kw2: King Wen number of second hexagram (1-64).

        Returns:
            The superposed HRR vector (list of floats).
        """
        if self._available:
            try:
                v1 = _wmr.hexagram_hrr_by_number_py(kw1)
                v2 = _wmr.hexagram_hrr_by_number_py(kw2)
                return list(_wmr.hexagram_superpose_py(v1, v2))
            except Exception as exc:
                logger.debug("Rust superpose failed, falling back: %s", exc)

        # Python fallback: element-wise average
        vectors = _get_py_vectors()
        v1 = vectors.get(kw1, [0.0] * _HRR_DIM)
        v2 = vectors.get(kw2, [0.0] * _HRR_DIM)
        return [(a + b) / 2.0 for a, b in zip(v1, v2)]

    def interaction_matrix(self) -> list[float]:
        """Get the full 64x64 hexagram interaction matrix (flattened).

        Returns:
            List of 4096 floats (64*64), row-major order.
        """
        if self._available:
            try:
                return list(_wmr.hexagram_interaction_matrix_py())
            except Exception as exc:
                logger.debug("Rust interaction_matrix failed, falling back: %s", exc)

        # Python fallback
        vectors = _get_py_vectors()
        matrix = []
        for i in range(1, 65):
            for j in range(1, 65):
                matrix.append(_py_cosine_sim(vectors[i], vectors[j]))
        return matrix

    def hexagram_vector(self, king_wen: int) -> list[float]:
        """Get the raw HRR vector for a hexagram.

        Args:
            king_wen: King Wen number (1-64).

        Returns:
            The HRR vector (list of floats).
        """
        if self._available:
            try:
                return list(_wmr.hexagram_hrr_by_number_py(king_wen))
            except Exception as exc:
                logger.debug("Rust hexagram_vector failed, falling back: %s", exc)

        vectors = _get_py_vectors()
        return vectors.get(king_wen, [0.0] * _HRR_DIM)


_bridge: HRRBridge | None = None


def get_hrr_bridge() -> HRRBridge:
    """Get the singleton HRRBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = HRRBridge()
    return _bridge
