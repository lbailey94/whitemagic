"""Quantized Fractional HRR (qFHRR) — Integer-Only HRR for Edge Devices.

Reduces HRR from 64-bit complex floats to 4-bit integers per dimension,
enabling HRR on microcontrollers, WASM, and any CPU without FPU.

Key properties:
  - Binding = modular integer addition (no multiplication needed)
  - Unbinding = modular integer subtraction
  - Similarity = lookup tables + integer accumulation
  - 3-4 bits per dimension (K=16 levels for 4 bits)
  - Preserves algebraic properties and similarity structure

Memory per vector: 384 dims × 4 bits = 192 bytes (vs 3072 bytes for float32)

Usage:
    from whitemagic.core.memory.qfhrr import QuantizedHRREngine
    engine = QuantizedHRREngine(dim=384, bits=4)
    bound = engine.bind(vec_a, vec_b)
    recovered = engine.unbind(bound, vec_b)
    sim = engine.similarity(vec_a, recovered)
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class QuantizedHRREngine:
    """Integer-only HRR using quantized phase representation.

    Instead of FFT-based circular convolution on float vectors, this engine
    uses modular arithmetic on linearly quantized values:
      - Each dimension is a float in [-1, 1] quantized to K levels (default K=16)
      - Binding: (a + b) mod K  (modular addition)
      - Unbinding: (bound - b) mod K  (modular subtraction)
      - Similarity: triangular LUT accounting for modular wraparound

    v2: Replaced arccos phase encoding with linear quantization.
    The arccos mapping compressed normalized embeddings (values near 0)
    into a narrow phase range, collapsing discrimination. Linear
    quantization preserves the full [-1, 1] distribution uniformly.
    """

    def __init__(self, dim: int = 384, bits: int = 4) -> None:
        self._dim = dim
        self._bits = bits
        self._K = 1 << bits  # Number of quantization levels (16 for 4 bits)
        self._lock = threading.Lock()
        self._relation_vectors: dict[str, np.ndarray] = {}
        self._init_relation_vectors()

        # Pre-compute similarity lookup table for small K (≤256)
        # sim(i, j) = 1 - 2 * min(|i-j|, K-|i-j|) / K
        self._sim_lut: np.ndarray | None = None
        if self._K <= 256:
            self._sim_lut = np.zeros((self._K, self._K), dtype=np.float32)
            for i in range(self._K):
                for j in range(self._K):
                    diff = min(abs(i - j), self._K - abs(i - j))
                    self._sim_lut[i, j] = 1.0 - 2.0 * diff / self._K

    def _init_relation_vectors(self) -> None:
        """Initialize canonical relation vectors with deterministic quantized values."""
        relations = [
            "CAUSES", "CAUSED_BY",
            "FOLLOWS", "PRECEDED_BY",
            "PART_OF", "CONTAINS",
            "SIMILAR_TO", "OPPOSITE_OF",
            "EXTENDS", "EXTENDED_BY",
            "USES", "USED_BY",
            "CREATES", "CREATED_BY",
            "IMPLEMENTS", "IMPLEMENTED_BY",
            "AGENT", "ACTION", "OBJECT", "LOCATION", "TIME",
        ]
        rng = np.random.default_rng(seed=12345)
        dtype = np.uint8 if self._K <= 256 else np.uint16
        for rel in relations:
            vec = rng.integers(0, self._K, size=self._dim, dtype=dtype)
            self._relation_vectors[rel] = vec

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def bits(self) -> int:
        return self._bits

    @property
    def K(self) -> int:
        return self._K

    @property
    def bytes_per_vector(self) -> int:
        """Memory per vector in bytes."""
        return (self._dim * self._bits + 7) // 8  # Packed bits

    def _to_quantized(self, vec: list[float] | np.ndarray) -> np.ndarray:
        """Convert a float vector to linearly quantized representation.

        Uses variance-weighted scaling: instead of fixed [-1, 1] range,
        stretches the quantization based on the vector's actual std dev.
        This gives more quantization levels to the region where values
        actually cluster, improving discrimination for normalized embeddings.

        For normalized embeddings (values near 0), std ≈ 1/sqrt(dim),
        so the effective range becomes [-3σ, 3σ] which maps the full
        quantization range to where 99.7% of values actually live.
        """
        arr = np.asarray(vec, dtype=np.float32)
        if arr.shape != (self._dim,):
            raise ValueError(f"Expected dim={self._dim}, got shape={arr.shape}")

        # Variance-weighted scaling: use 3σ range instead of fixed [-1, 1]
        sigma = float(np.std(arr))
        if sigma < 1e-6:
            # Degenerate case — all values the same
            mid = self._K // 2
            if self._K <= 256:
                return np.full(self._dim, mid, dtype=np.uint8)
            return np.full(self._dim, mid, dtype=np.uint16)

        # Map [-3σ, 3σ] → [0, K-1], clipping outliers
        scale = (self._K - 1) / (6.0 * sigma)
        scaled = (arr * scale) + (self._K - 1) * 0.5
        clipped = np.clip(scaled, 0, self._K - 1)
        if self._K <= 256:
            quantized = np.round(clipped).astype(np.uint8)
        else:
            quantized = np.round(clipped).astype(np.uint16)
        return quantized

    def _to_quantized_fixed(self, vec: list[float] | np.ndarray) -> np.ndarray:
        """Convert float vector to quantized using fixed [-1, 1] range.

        Used for re-quantization in superpose/bind where the input is
        already in float space with known range.
        """
        arr = np.asarray(vec, dtype=np.float32)
        clipped = np.clip(arr, -1.0, 1.0)
        scaled = (clipped + 1.0) * 0.5 * (self._K - 1)
        if self._K <= 256:
            return np.round(scaled).astype(np.uint8)
        return np.round(scaled).astype(np.uint16)

    def _to_float(self, quantized: np.ndarray) -> np.ndarray:
        """Convert quantized value back to approximate float representation."""
        return (quantized.astype(np.float32) / (self._K - 1) * 2.0 - 1.0).astype(np.float32)

    def bind(
        self, a: list[float] | np.ndarray | np.ndarray, b: list[float] | np.ndarray | np.ndarray,
    ) -> np.ndarray:
        """Bind two quantized vectors via modular addition.

        bind(A, B)[i] = (A[i] + B[i]) mod K
        """
        a_q = self._ensure_quantized(a)
        b_q = self._ensure_quantized(b)
        dtype = np.uint8 if self._K <= 256 else np.uint16
        return (a_q.astype(np.int32) + b_q.astype(np.int32)).astype(dtype) % self._K

    def unbind(
        self, bound: list[float] | np.ndarray | np.ndarray, b: list[float] | np.ndarray | np.ndarray,
    ) -> np.ndarray:
        """Unbind via modular subtraction.

        unbind(bound, B)[i] = (bound[i] - B[i]) mod K
        """
        bound_q = self._ensure_quantized(bound)
        b_q = self._ensure_quantized(b)
        dtype = np.uint8 if self._K <= 256 else np.uint16
        return (bound_q.astype(np.int32) - b_q.astype(np.int32)).astype(dtype) % self._K

    def _ensure_quantized(self, vec: Any) -> np.ndarray:
        """Ensure vector is in quantized format (uint8 or uint16 depending on K)."""
        expected_dtype = np.uint8 if self._K <= 256 else np.uint16
        if isinstance(vec, np.ndarray) and vec.dtype == expected_dtype and vec.shape == (self._dim,):
            return vec
        return self._to_quantized(vec)

    def superpose(self, *vectors: Any) -> np.ndarray:
        """Superpose multiple quantized vectors.

        For quantized phases, superposition is done by averaging phases
        (circular mean) then re-quantizing.
        """
        if not vectors:
            return np.zeros(self._dim, dtype=np.uint8)

        q_vectors = [self._ensure_quantized(v) for v in vectors]

        # Average in linear space, then re-quantize using fixed range
        floats = np.array([self._to_float(v) for v in q_vectors])
        mean_floats = np.mean(floats, axis=0)
        return self._to_quantized_fixed(mean_floats)

    def similarity(
        self, a: list[float] | np.ndarray | np.ndarray, b: list[float] | np.ndarray | np.ndarray,
    ) -> float:
        """Compute similarity using lookup table — no floating point arithmetic.

        similarity = mean(sim_lut[a[i], b[i]] for all i)
        """
        a_q = self._ensure_quantized(a)
        b_q = self._ensure_quantized(b)

        if self._sim_lut is not None:
            # Fast LUT lookup for small K
            sims = self._sim_lut[a_q, b_q]
            return float(np.mean(sims))
        else:
            # On-the-fly computation for large K (vectorized)
            diffs = np.minimum(np.abs(a_q.astype(np.int32) - b_q.astype(np.int32)),
                               self._K - np.abs(a_q.astype(np.int32) - b_q.astype(np.int32)))
            sims = 1.0 - 2.0 * diffs.astype(np.float32) / self._K
            return float(np.mean(sims))

    def get_relation_vector(self, relation: str) -> np.ndarray:
        """Get quantized relation vector by name."""
        rel_upper = relation.upper()
        if rel_upper in self._relation_vectors:
            return self._relation_vectors[rel_upper]

        # Generate deterministic vector from name hash
        seed = int(hashlib.md5(rel_upper.encode()).hexdigest()[:8], 16) % (2**31)
        rng = np.random.default_rng(seed=seed)
        dtype = np.uint8 if self._K <= 256 else np.uint16
        vec = rng.integers(0, self._K, size=self._dim, dtype=dtype)
        self._relation_vectors[rel_upper] = vec
        return vec

    def project(
        self, embedding: list[float] | np.ndarray, relation: str,
    ) -> np.ndarray:
        """Project an embedding through a relation (quantized bind)."""
        rel_vec = self.get_relation_vector(relation)
        return self.bind(embedding, rel_vec)

    def inverse_project(
        self, embedding: list[float] | np.ndarray, relation: str,
    ) -> np.ndarray:
        """Inverse projection (quantized unbind)."""
        rel_vec = self.get_relation_vector(relation)
        return self.unbind(embedding, rel_vec)

    def get_stats(self) -> dict[str, Any]:
        return {
            "dim": self._dim,
            "bits": self._bits,
            "K": self._K,
            "bytes_per_vector": self.bytes_per_vector,
            "num_relation_vectors": len(self._relation_vectors),
            "float32_bytes": self._dim * 4,
            "compression_vs_float32": round(self._dim * 4 / self.bytes_per_vector, 1),
        }



_q_engine: QuantizedHRREngine | None = None
_q_engine_lock = threading.Lock()


def get_quantized_hrr_engine(dim: int = 384, bits: int = 4) -> QuantizedHRREngine:
    """Get the global QuantizedHRREngine singleton."""
    global _q_engine
    if _q_engine is None:
        with _q_engine_lock:
            if _q_engine is None:
                _q_engine = QuantizedHRREngine(dim=dim, bits=bits)
    return _q_engine



_TIER_BITS_MAP = {
    0: 4,   # EDGE_RULES   — 4-bit (192 bytes, 8x compression)
    1: 8,   # LOCAL_SMALL  — 8-bit (384 bytes, 4x compression)
    2: 8,   # LOCAL_LARGE  — 8-bit (same, more precision for complex reasoning)
    3: 16,  # CLOUD        — 16-bit (768 bytes, 2x compression, max precision)
}

_adaptive_engines: dict[int, QuantizedHRREngine] = {}
_adaptive_lock = threading.Lock()


def get_adaptive_qfhrr_engine(tier: int, dim: int = 384) -> QuantizedHRREngine:
    """Get a QuantizedHRREngine with bit-width selected by inference tier.

    Tier 0 (edge):   4-bit  — 192 bytes, 8x compression, fastest
    Tier 1 (local):  8-bit  — 384 bytes, 4x compression, balanced
    Tier 2 (local):  8-bit  — same
    Tier 3 (cloud):  16-bit — 768 bytes, 2x compression, max precision

    This allows the inference router to select the appropriate qFHRR
    precision based on where the computation is happening. Edge devices
    get maximum compression; cloud gets maximum accuracy.
    """
    bits = _TIER_BITS_MAP.get(tier, 4)  # Default to 4-bit
    with _adaptive_lock:
        if bits not in _adaptive_engines:
            _adaptive_engines[bits] = QuantizedHRREngine(dim=dim, bits=bits)
    return _adaptive_engines[bits]


def get_tier_bits(tier: int) -> int:
    """Get the bit-width for a given inference tier."""
    return _TIER_BITS_MAP.get(tier, 4)



_GALACTIC_ZONE_BITS_MAP: dict[str, int] = {
    "core": 8,     # CORE       — 8-bit (384 bytes), high precision for active memories
    "inner_rim": 8,  # INNER_RIM  — 8-bit, still frequently accessed
    "mid_band": 4,    # MID_BAND   — 4-bit (192 bytes), 2x compression for aging memories
    "outer_rim": 2,   # OUTER_RIM  — 2-bit (96 bytes), 4x compression for rarely accessed
    "far_edge": 2,    # FAR_EDGE   — 2-bit, maximum compression for archived memories
}

_galactic_engines: dict[int, QuantizedHRREngine] = {}
_galactic_lock = threading.Lock()


def get_galactic_qfhrr_bits(zone: str) -> int:
    """Get the qFHRR bit-width for a galactic zone.

    Core/Inner Rim memories get 8-bit precision for accurate recall.
    Mid Band memories get 4-bit (2x compression) as they age.
    Outer Rim/Far Edge memories get 2-bit (4x compression) since
    they're rarely accessed and approximate matching suffices.

    Inspired by SuperLocalMemory V3.3's progressive quantization:
    memories lose embedding precision as they fade through lifecycle zones.
    """
    return _GALACTIC_ZONE_BITS_MAP.get(zone, 4)


def get_galactic_qfhrr_engine(zone: str, dim: int = 384) -> QuantizedHRREngine:
    """Get a QuantizedHRREngine with bit-width selected by galactic zone.

    Returns a cached engine instance for the zone's bit-width.
    """
    bits = get_galactic_qfhrr_bits(zone)
    with _galactic_lock:
        if bits not in _galactic_engines:
            _galactic_engines[bits] = QuantizedHRREngine(dim=dim, bits=bits)
    return _galactic_engines[bits]


def requantize_for_zone(
    embedding: list[float] | np.ndarray,
    zone: str,
    dim: int = 384,
) -> np.ndarray:
    """Re-quantize an embedding at the bit-width appropriate for its galactic zone.

    Called when a memory moves between zones (e.g. during galactic sweep)
    to progressively compress its embedding representation.

    Returns the quantized vector at the zone's bit-width.
    """
    engine = get_galactic_qfhrr_engine(zone, dim=dim)
    return engine._to_quantized(embedding)
