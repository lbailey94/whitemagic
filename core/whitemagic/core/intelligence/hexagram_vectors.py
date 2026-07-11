"""Hexagram HRR vectorization — Python fallback with Rust acceleration.

Encodes each of the 64 I Ching hexagrams as a holographic reduced representation
(HRR) vector using circular convolution binding of trigram vectors. Provides
interaction scoring, synergy detection, and superposition operations.

When the Rust extension (whitemagic_rs) is available, all operations are
accelerated ~10-100x. Falls back to numpy-based implementations otherwise.

Usage::

    from whitemagic.core.intelligence.hexagram_vectors import HexagramVectors

    hv = HexagramVectors()
    score = hv.interaction_score(1, 2)  # Similarity between hexagrams 1 and 2
    synergies = hv.top_synergies(10)    # Top 10 most synergistic pairs
    vec = hv.get_vector(15)             # 64-dim HRR vector for hexagram 15
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

HRR_DIM = 64

# Trigram seeds (must match Rust hexagram_hrr.rs)
_TRIGRAM_SEEDS = {
    "Qian": 1, "Kun": 2, "Zhen": 3, "Xun": 4,
    "Kan": 5, "Li": 6, "Gen": 7, "Dui": 8,
}

# King Wen → binary lookup (must match Rust king_wen_to_binary)
_KING_WEN_TO_BINARY: list[int] = [
     2, 24,  7, 19, 15, 36, 46, 11,
    16, 51, 40, 54, 62, 55, 32, 34,
     8,  3, 29, 60, 39, 63, 48,  5,
    45, 17, 47, 58, 31, 49, 28, 43,
    23, 27,  4, 41, 52, 22, 18, 26,
    35, 21, 64, 38, 56, 30, 50, 14,
    20, 42, 59, 61, 53, 37, 57,  9,
    12, 25,  6, 10, 33, 13, 44,  1,
]


def _seeded_vector(seed: int, dim: int = HRR_DIM) -> np.ndarray:
    """Deterministic random vector from seed (LCG, matches Rust)."""
    state = np.uint64(seed)
    vals = np.empty(dim, dtype=np.float64)
    for i in range(dim):
        state = state * np.uint64(6364136223846793005) + np.uint64(1442695040888963407)
        vals[i] = ((state >> np.uint64(33)) / float(1 << 31)) * 2.0 - 1.0
    norm = np.linalg.norm(vals)
    if norm > 0:
        vals /= norm
    return vals


def _binary_to_trigrams(binary: int) -> tuple[str, str]:
    """Split 6-bit binary into (lower, upper) trigram names."""
    lower_bits = binary & 0b111
    upper_bits = (binary >> 3) & 0b111
    _BIT_TO_TRIGRAM = {
        0b111: "Qian", 0b000: "Kun", 0b001: "Zhen", 0b110: "Xun",
        0b010: "Kan", 0b101: "Li", 0b100: "Gen", 0b011: "Dui",
    }
    return _BIT_TO_TRIGRAM[lower_bits], _BIT_TO_TRIGRAM[upper_bits]


def _king_wen_to_binary(kw: int) -> int:
    """Convert King Wen number (1-64) to 6-bit binary."""
    for binary, kw_val in enumerate(_KING_WEN_TO_BINARY):
        if kw_val == kw:
            return binary
    return 0


def _circular_convolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Circular convolution via direct computation (O(n²), fine for dim=64)."""
    n = len(a)
    result = np.zeros(n)
    for i in range(n):
        for j in range(n):
            result[(i + j) % n] += a[i] * b[j]
    norm = np.linalg.norm(result)
    if norm > 0:
        result /= norm
    return result


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na > 0 and nb > 0:
        return dot / (na * nb)
    return 0.0


class HexagramVectors:
    """Hexagram HRR vectorization with Rust acceleration and numpy fallback.

    All 64 hexagrams are encoded as 64-dimensional HRR vectors via circular
    convolution binding of their lower and upper trigram vectors. The vectors
    are deterministic and unit-normalized.

    Methods:
        get_vector(king_wen): Get HRR vector for a hexagram
        interaction_score(kw1, kw2): Cosine similarity between two hexagrams
        top_synergies(k): Top-K most synergistic hexagram pairs
        detect_synergies(threshold): All pairs above a similarity threshold
        superpose(kw1, kw2): Superpose two hexagram vectors
        interaction_matrix(): Full 64×64 similarity matrix
    """

    def __init__(self) -> None:
        self._vectors: dict[int, np.ndarray] = {}
        self._use_rust = self._check_rust()
        self._init_vectors()
        logger.info(
            "HexagramVectors initialized: %d hexagrams, backend=%s",
            len(self._vectors),
            "rust" if self._use_rust else "numpy",
        )

    def _check_rust(self) -> bool:
        """Check if Rust HRR functions are available."""
        try:
            import whitemagic_rs

            return hasattr(whitemagic_rs, "hexagram_hrr_by_number_py")
        except ImportError:
            return False

    def _init_vectors(self) -> None:
        """Pre-compute all 64 hexagram vectors."""
        if self._use_rust:
            import whitemagic_rs

            for kw in range(1, 65):
                v = whitemagic_rs.hexagram_hrr_by_number_py(kw)
                self._vectors[kw] = np.array(v, dtype=np.float64)
        else:
            for kw in range(1, 65):
                binary = _king_wen_to_binary(kw)
                lower_name, upper_name = _binary_to_trigrams(binary)
                lower_v = _seeded_vector(_TRIGRAM_SEEDS[lower_name])
                upper_v = _seeded_vector(_TRIGRAM_SEEDS[upper_name])
                self._vectors[kw] = _circular_convolve(lower_v, upper_v)

    def get_vector(self, king_wen: int) -> list[float]:
        """Get the HRR vector for a hexagram (King Wen number 1-64).

        Returns:
            64-dimensional unit-normalized float vector.
        """
        if king_wen < 1 or king_wen > 64:
            raise ValueError(f"king_wen must be 1-64, got {king_wen}")
        return self._vectors[king_wen].tolist()

    def interaction_score(self, kw1: int, kw2: int) -> float:
        """Cosine similarity between two hexagrams (King Wen numbers 1-64).

        Returns:
            Float in [-1, 1]. 1.0 = identical, 0.0 = orthogonal, -1.0 = opposite.
        """
        if self._use_rust:
            import whitemagic_rs

            return whitemagic_rs.hexagram_interaction_score_py(kw1, kw2)
        return _cosine_sim(self._vectors[kw1], self._vectors[kw2])

    def top_synergies(self, k: int = 10) -> list[dict[str, Any]]:
        """Top-K most synergistic hexagram pairs by HRR cosine similarity.

        Args:
            k: Number of top pairs to return.

        Returns:
            List of {"hexagram_a": int, "hexagram_b": int, "similarity": float},
            sorted by similarity descending.
        """
        if self._use_rust:
            import whitemagic_rs

            pairs = whitemagic_rs.hexagram_top_synergies_py(k)
            return [
                {"hexagram_a": a, "hexagram_b": b, "similarity": s}
                for a, b, s in pairs
            ]

        pairs = []
        for i in range(1, 65):
            for j in range(i + 1, 65):
                sim = _cosine_sim(self._vectors[i], self._vectors[j])
                pairs.append({"hexagram_a": i, "hexagram_b": j, "similarity": sim})
        pairs.sort(key=lambda p: p["similarity"], reverse=True)
        return pairs[:k]

    def detect_synergies(self, threshold: float = 0.3) -> list[dict[str, Any]]:
        """Find all hexagram pairs with similarity above a threshold.

        Args:
            threshold: Minimum cosine similarity (default 0.3).

        Returns:
            List of {"hexagram_a": int, "hexagram_b": int, "similarity": float},
            sorted by similarity descending.
        """
        if self._use_rust:
            import whitemagic_rs

            pairs = whitemagic_rs.hexagram_detect_synergies_py(threshold)
            return [
                {"hexagram_a": a, "hexagram_b": b, "similarity": s}
                for a, b, s in pairs
            ]

        pairs = []
        for i in range(1, 65):
            for j in range(i + 1, 65):
                sim = _cosine_sim(self._vectors[i], self._vectors[j])
                if sim > threshold:
                    pairs.append({"hexagram_a": i, "hexagram_b": j, "similarity": sim})
        pairs.sort(key=lambda p: p["similarity"], reverse=True)
        return pairs

    def superpose(self, kw1: int, kw2: int) -> list[float]:
        """Superpose two hexagram vectors (addition + normalization).

        Represents combining two hexagram influences into a single state.

        Args:
            kw1, kw2: King Wen numbers (1-64).

        Returns:
            64-dimensional unit-normalized float vector.
        """
        v1 = self._vectors[kw1]
        v2 = self._vectors[kw2]
        result = v1 + v2
        norm = np.linalg.norm(result)
        if norm > 0:
            result /= norm
        return result.tolist()

    def interaction_matrix(self) -> list[list[float]]:
        """Full 64×64 interaction matrix of cosine similarities.

        Returns:
            64×64 matrix as list of lists. matrix[i][j] = similarity
            between hexagram (i+1) and hexagram (j+1).
        """
        if self._use_rust:
            import whitemagic_rs

            flat = whitemagic_rs.hexagram_interaction_matrix_py()
            return [flat[i * 64:(i + 1) * 64] for i in range(64)]

        matrix = [[0.0] * 64 for _ in range(64)]
        for i in range(64):
            for j in range(64):
                matrix[i][j] = _cosine_sim(self._vectors[i + 1], self._vectors[j + 1])
        return matrix

    def nearest_hexagrams(self, vector: list[float], k: int = 5) -> list[dict[str, Any]]:
        """Find the k nearest hexagrams to a given vector.

        Useful for finding which hexagram(s) best represent an arbitrary
        point in HRR space (e.g., a memory embedding projected into hexagram space).

        Args:
            vector: A float vector (any dimensionality, will be truncated/padded to 64).
            k: Number of nearest hexagrams to return.

        Returns:
            List of {"hexagram": int, "similarity": float}, sorted by similarity descending.
        """
        target = np.array(vector[:HRR_DIM], dtype=np.float64)
        if len(target) < HRR_DIM:
            target = np.pad(target, (0, HRR_DIM - len(target)))
        norm = np.linalg.norm(target)
        if norm > 0:
            target /= norm

        results = []
        for kw in range(1, 65):
            sim = _cosine_sim(target, self._vectors[kw])
            results.append({"hexagram": kw, "similarity": sim})
        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results[:k]


# ── Singleton ─────────────────────────────────────────────────────────

_instance: HexagramVectors | None = None


def get_hexagram_vectors() -> HexagramVectors:
    """Get the singleton HexagramVectors instance."""
    global _instance
    if _instance is None:
        _instance = HexagramVectors()
    return _instance
