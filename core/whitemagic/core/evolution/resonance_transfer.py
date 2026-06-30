"""Resonance-Driven Transfer Learning (Objective I).

Uses resonance signatures to detect dynamically similar subsystems.
When an improvement succeeds for subsystem A, it can be transferred
to resonant subsystems with prior confidence proportional to resonance.

Resonance signature: frequency-domain representation of error patterns,
activity rhythms, and improvement trajectories.

This is physics-inspired transfer learning: instead of semantic similarity,
we use dynamic similarity (do these systems oscillate in phase?).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResonanceSignature:
    """Frequency-domain signature of a subsystem."""

    subsystem_id: str
    frequencies: list[float] = field(default_factory=list)  # Dominant frequencies
    amplitudes: list[float] = field(default_factory=list)  # Amplitude at each frequency
    error_pattern: list[float] = field(default_factory=list)  # Time-series error rates
    activity_rhythm: list[float] = field(default_factory=list)  # Activity over time

    def to_vector(self) -> list[float]:
        """Convert signature to a comparable vector."""
        if not self.frequencies:
            return [0.0, 0.0, 0.0]
        return [
            sum(self.frequencies) / len(self.frequencies),  # Mean frequency
            max(self.amplitudes) if self.amplitudes else 0.0,  # Peak amplitude
            len(self.frequencies),  # Complexity (number of modes)
        ]


@dataclass
class TransferProposal:
    """A proposal to transfer an improvement from one subsystem to another."""

    source_id: str
    target_id: str
    improvement_id: str
    resonance_score: float  # 0-1, higher = more resonant
    transferred_prior: float  # Prior confidence for the target
    metadata: dict[str, Any] = field(default_factory=dict)


class ResonanceTransferEngine:
    """Detects resonant subsystems and transfers improvements between them.

    Uses FFT-based cross-correlation to compute pairwise resonance.
    When an improvement succeeds for one subsystem, it's transferred
    to resonant subsystems with proportional confidence.
    """

    def __init__(self, resonance_threshold: float = 0.6) -> None:
        self._threshold = resonance_threshold
        self._signatures: dict[str, ResonanceSignature] = {}
        self._resonance_cache: dict[tuple[str, str], float] = {}
        self._transfers: list[TransferProposal] = []

    def register_signature(self, signature: ResonanceSignature) -> None:
        """Register a subsystem's resonance signature."""
        self._signatures[signature.subsystem_id] = signature
        # Invalidate cache for this subsystem
        keys_to_remove = [
            k for k in self._resonance_cache if signature.subsystem_id in k
        ]
        for k in keys_to_remove:
            del self._resonance_cache[k]

    def compute_resonance(self, id_a: str, id_b: str) -> float:
        """Compute resonance score between two subsystems.

        Uses cross-correlation of their error patterns and
        cosine similarity of their frequency vectors.

        Returns:
            Resonance score in [0, 1].
        """
        if id_a == id_b:
            return 1.0

        cached = self._resonance_cache.get((id_a, id_b))
        if cached is not None:
            return cached

        sig_a = self._signatures.get(id_a)
        sig_b = self._signatures.get(id_b)
        if sig_a is None or sig_b is None:
            return 0.0

        # 1. Cross-correlation of error patterns
        error_corr = self._cross_correlation(sig_a.error_pattern, sig_b.error_pattern)

        # 2. Cosine similarity of frequency vectors
        freq_sim = self._cosine_similarity(sig_a.to_vector(), sig_b.to_vector())

        # 3. Activity rhythm correlation
        activity_corr = self._cross_correlation(
            sig_a.activity_rhythm, sig_b.activity_rhythm
        )

        # Weighted combination
        resonance = 0.4 * abs(error_corr) + 0.3 * freq_sim + 0.3 * abs(activity_corr)
        resonance = max(0.0, min(1.0, resonance))

        self._resonance_cache[(id_a, id_b)] = resonance
        self._resonance_cache[(id_b, id_a)] = resonance
        return resonance

    def _cross_correlation(self, a: list[float], b: list[float]) -> float:
        """Compute normalized cross-correlation between two signals."""
        if not a or not b:
            return 0.0
        # Pad to same length
        n = max(len(a), len(b))
        a_padded = a + [0.0] * (n - len(a))
        b_padded = b + [0.0] * (n - len(b))

        mean_a = sum(a_padded) / n
        mean_b = sum(b_padded) / n

        numerator = sum(
            (a_padded[i] - mean_a) * (b_padded[i] - mean_b) for i in range(n)
        )
        var_a = sum((x - mean_a) ** 2 for x in a_padded)
        var_b = sum((x - mean_b) ** 2 for x in b_padded)

        if var_a == 0 or var_b == 0:
            return 0.0
        return numerator / math.sqrt(var_a * var_b)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def find_resonant_subsystems(self, source_id: str) -> list[tuple[str, float]]:
        """Find subsystems resonant with the given source.

        Returns:
            List of (subsystem_id, resonance_score) sorted by score.
        """
        results = []
        for sid in self._signatures:
            if sid == source_id:
                continue
            score = self.compute_resonance(source_id, sid)
            if score >= self._threshold:
                results.append((sid, score))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def propose_transfer(
        self,
        source_id: str,
        improvement_id: str,
        source_confidence: float = 0.8,
    ) -> list[TransferProposal]:
        """Propose transferring an improvement to resonant subsystems.

        Args:
            source_id: The subsystem where the improvement succeeded.
            improvement_id: The improvement to transfer.
            source_confidence: Confidence in the source subsystem.

        Returns:
            List of TransferProposal objects for resonant targets.
        """
        resonant = self.find_resonant_subsystems(source_id)
        proposals = []
        for target_id, resonance in resonant:
            # Transferred prior is proportional to resonance × source confidence
            transferred_prior = resonance * source_confidence
            proposal = TransferProposal(
                source_id=source_id,
                target_id=target_id,
                improvement_id=improvement_id,
                resonance_score=resonance,
                transferred_prior=transferred_prior,
            )
            proposals.append(proposal)
            self._transfers.append(proposal)
        return proposals

    def get_transfers(self, subsystem_id: str | None = None) -> list[TransferProposal]:
        """Get transfer proposals, optionally filtered by subsystem."""
        if subsystem_id is None:
            return list(self._transfers)
        return [
            t
            for t in self._transfers
            if t.source_id == subsystem_id or t.target_id == subsystem_id
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_subsystems": len(self._signatures),
            "total_transfers": len(self._transfers),
            "avg_resonance": (
                sum(t.resonance_score for t in self._transfers) / len(self._transfers)
                if self._transfers
                else 0.0
            ),
        }
