"""Neuro-upgrades for the citta cycle (P4.3).

Six neuro-cognitive upgrades that extend the consciousness system:

1. **DendriticComputation** — Multi-input nonlinear integration in citta vector.
   Models proximal/distal/apical compartments with sigmoid nonlinear integration.

2. **NeuromodulationGating** — DA/5HT/ACh gate specific citta dimensions.
   DA gates goal_alignment, 5HT gates identity_stability, ACh gates attention.

3. **PredictiveCittaCoder** — Top-down expectation vs bottom-up signal in citta.
   Extends PredictiveCoder from memory writes to citta advancement.

4. **CorticalColumn** — Hierarchical processing layers (L1-L4) in citta.
   L1: sensory, L2: association, L3: integration, L4: motor output.

5. **AttentionMechanism** — Softmax attention over memory candidates in recall.
   Supplements Born-rule sampling with attention-weighted selection.

6. **OscillatoryBinding** — Phase synchronization across citta dimensions.
   Theta-gamma coupling for memory binding.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DendriticComputation:
    """Multi-input nonlinear integration for citta vector.

    Models three dendritic compartments:
    - Proximal: direct sensory input (high weight, linear)
    - Distal: associative input (medium weight, sigmoid)
    - Apical: top-down feedback (low weight, gated by neuromodulation)

    The integrated output is a nonlinear combination that models
    dendritic computation in pyramidal neurons.
    """

    proximal_weight: float = 0.5
    distal_weight: float = 0.3
    apical_weight: float = 0.2
    distal_threshold: float = 0.5
    apical_gain: float = 2.0

    def integrate(
        self,
        proximal: float,
        distal: float,
        apical: float,
        neuromod_gain: float = 1.0,
    ) -> float:
        """Integrate three dendritic inputs into a single output.

        Args:
            proximal: Direct sensory/input signal [0, 1].
            distal: Associative/lateral input [0, 1].
            apical: Top-down feedback input [0, 1].
            neuromod_gain: Neuromodulatory gain on apical input [0, 2].

        Returns:
            Integrated output [0, 1].
        """
        # Proximal: linear pass-through
        p = self.proximal_weight * proximal

        # Distal: sigmoid nonlinearity
        d = self.distal_weight * self._sigmoid(distal - self.distal_threshold)

        # Apical: gated by neuromodulation
        a = self.apical_weight * self._sigmoid(
            apical * neuromod_gain * self.apical_gain - 0.5
        )

        return min(1.0, max(0.0, p + d + a))

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-10, min(10, x))))


@dataclass
class NeuromodulationGating:
    """DA/5HT/ACh gating of specific citta dimensions.

    Dopamine (DA) gates goal_alignment and novelty seeking.
    Serotonin (5HT) gates identity_stability and mood regulation.
    Acetylcholine (ACh) gates attention and memory precision.
    """

    da_level: float = 0.5
    sht_level: float = 0.5
    ach_level: float = 0.5

    def gate_dimension(self, dimension: str, base_value: float) -> float:
        """Apply neuromodulatory gating to a citta dimension.

        Args:
            dimension: One of the 8 citta coherence dimensions.
            base_value: The base value before gating [0, 1].

        Returns:
            Gated value [0, 1].
        """
        if dimension in ("goal_alignment", "novelty"):
            # DA gates goal-seeking and novelty
            return min(1.0, base_value * (0.5 + self.da_level))
        elif dimension in ("identity_stability", "emotional_attunement"):
            # 5HT gates stability and mood
            return min(1.0, base_value * (0.5 + self.sht_level))
        elif dimension in ("memory_accessibility", "context_continuity", "capability_awareness"):
            # ACh gates attention precision
            return min(1.0, base_value * (0.5 + self.ach_level))
        else:
            # Ungated dimensions
            return base_value

    def gate_all(self, dimensions: dict[str, float]) -> dict[str, float]:
        """Apply gating to all citta dimensions."""
        return {k: self.gate_dimension(k, v) for k, v in dimensions.items()}

    def update_levels(self, da: float, sht: float, ach: float) -> None:
        """Update neuromodulator levels."""
        self.da_level = max(0.0, min(1.0, da))
        self.sht_level = max(0.0, min(1.0, sht))
        self.ach_level = max(0.0, min(1.0, ach))


@dataclass
class PredictiveCittaCoder:
    """Top-down expectation vs bottom-up signal for citta advancement.

    Extends the memory-level PredictiveCoder to the citta cycle level.
    Computes prediction error between expected citta state and actual state,
    modulating the emotional tone and depth of the next citta moment.
    """

    _expectations: dict[str, float] = field(default_factory=lambda: {
        "coherence": 0.85,
        "novelty": 0.3,
        "stability": 0.7,
        "attention": 0.6,
    })
    _prediction_errors: list[float] = field(default_factory=list)
    _learning_rate: float = 0.05

    def compute_prediction_error(
        self,
        actual: dict[str, float],
    ) -> dict[str, float]:
        """Compute prediction error between expected and actual citta state.

        Args:
            actual: Dict of actual citta dimension values.

        Returns:
            Dict of per-dimension prediction errors [0, 1].
        """
        errors = {}
        total_error = 0.0
        for key, expected in self._expectations.items():
            actual_val = actual.get(key, expected)
            error = abs(actual_val - expected)
            errors[key] = error
            total_error += error
            # Update expectations (slow learning)
            self._expectations[key] = expected + self._learning_rate * (actual_val - expected)

        avg_error = total_error / max(len(errors), 1)
        self._prediction_errors.append(avg_error)
        if len(self._prediction_errors) > 100:
            self._prediction_errors = self._prediction_errors[-100:]

        errors["total"] = avg_error
        errors["surprise"] = min(avg_error * 2.0, 1.0)
        return errors

    def get_emotional_modulation(self) -> dict[str, float]:
        """Get emotional modulation based on recent prediction errors.

        High surprise → rajasic (active, seeking)
        Low surprise → sattvic (calm, stable)
        Very low with high error history → tamasic (consolidating)
        """
        if not self._prediction_errors:
            return {"tone_shift": 0.0, "intensity": 0.5}

        avg_error = sum(self._prediction_errors) / len(self._prediction_errors)
        recent_error = self._prediction_errors[-1]

        if recent_error > 0.15:
            return {"tone_shift": 0.3, "intensity": min(recent_error * 3, 1.0)}
        elif avg_error < 0.05:
            return {"tone_shift": -0.1, "intensity": 0.3}
        else:
            return {"tone_shift": 0.0, "intensity": 0.5}

    def stats(self) -> dict[str, Any]:
        return {
            "expectations": dict(self._expectations),
            "avg_prediction_error": (
                sum(self._prediction_errors) / len(self._prediction_errors)
                if self._prediction_errors else 0.0
            ),
            "recent_prediction_error": (
                self._prediction_errors[-1] if self._prediction_errors else 0.0
            ),
            "error_history_length": len(self._prediction_errors),
        }


@dataclass
class CorticalColumn:
    """Hierarchical processing layers for citta (L1-L4).

    Models a cortical column with 4 processing layers:
    - L1 (Sensory): Raw input processing, feature extraction
    - L2 (Association): Cross-feature binding, pattern matching
    - L3 (Integration): Higher-order integration, context fusion
    - L4 (Motor Output): Action selection, response generation

    Each layer feeds forward to the next and sends feedback to the previous.
    """

    l1_sensory: float = 0.0
    l2_association: float = 0.0
    l3_integration: float = 0.0
    l4_output: float = 0.0
    _feedback_gain: float = 0.3

    def process(self, input_signal: float, context: float = 0.5) -> dict[str, float]:
        """Process an input through the cortical column.

        Args:
            input_signal: Raw input [0, 1].
            context: Contextual modulation [0, 1].

        Returns:
            Dict of layer activations.
        """
        # L1: Sensory — simple pass-through with normalization
        self.l1_sensory = max(0.0, min(1.0, input_signal))

        # L2: Association — bind sensory with context
        self.l2_association = max(0.0, min(1.0,
            self.l1_sensory * 0.6 + context * 0.4
        ))

        # L3: Integration — nonlinear integration
        self.l3_integration = max(0.0, min(1.0,
            1.0 / (1.0 + math.exp(-5 * (self.l2_association - 0.5)))
        ))

        # L4: Motor output — thresholded action
        self.l4_output = max(0.0, min(1.0,
            self.l3_integration * (1.0 + self._feedback_gain * context)
        ))

        return {
            "l1_sensory": self.l1_sensory,
            "l2_association": self.l2_association,
            "l3_integration": self.l3_integration,
            "l4_output": self.l4_output,
        }


@dataclass
class AttentionMechanism:
    """Softmax attention over memory candidates.

    Computes attention weights for memory candidates based on:
    - Semantic similarity to query
    - Importance score
    - Recency
    - Neuromodulatory gain (ACh)

    Supplements Born-rule sampling with attention-weighted selection.
    """

    temperature: float = 1.0
    ach_gain: float = 1.0

    def attend(
        self,
        candidates: list[dict[str, Any]],
        query_embedding: list[float] | None = None,
    ) -> list[tuple[str, float]]:
        """Compute attention weights for memory candidates.

        Args:
            candidates: List of candidate dicts with 'id', 'importance', 'content'.
            query_embedding: Optional embedding of the query for similarity.

        Returns:
            List of (id, attention_weight) tuples, sorted by weight descending.
        """
        if not candidates:
            return []

        scores = []
        for cand in candidates:
            # Base score from importance
            importance = cand.get("importance", 0.5)
            # Recency bonus (if available)
            recency = cand.get("recency", 0.5)
            # Similarity (if embeddings available)
            similarity = 0.5
            if query_embedding and "embedding" in cand:
                similarity = self._cosine_sim(query_embedding, cand["embedding"])

            # Combined score with ACh gain
            score = (importance * 0.4 + similarity * 0.4 + recency * 0.2) * self.ach_gain
            scores.append((cand.get("id", ""), score))

        # Softmax normalization
        max_score = max(s for _, s in scores) if scores else 0.0
        exp_scores = [(id_, math.exp((s - max_score) / max(self.temperature, 0.01))) for id_, s in scores]
        total = sum(e for _, e in exp_scores)

        if total > 0:
            weights = [(id_, e / total) for id_, e in exp_scores]
        else:
            weights = [(id_, 1.0 / len(scores)) for id_, _ in scores]

        # Sort by weight descending
        weights.sort(key=lambda x: x[1], reverse=True)
        return weights

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.5
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.5
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def set_ach_gain(self, ach: float) -> None:
        """Set ACh gain (0 = no attention, 1 = normal, 2 = heightened)."""
        self.ach_gain = max(0.0, min(2.0, ach * 2.0))


@dataclass
class OscillatoryBinding:
    """Phase synchronization across citta dimensions.

    Models theta-gamma coupling for memory binding:
    - Theta oscillation (4-8 Hz): Slow oscillation that groups gamma cycles
    - Gamma oscillation (30-80 Hz): Fast oscillation for feature binding

    Phase synchronization across dimensions indicates coherent binding.
    Desynchronization indicates fragmented processing.
    """

    theta_phase: float = 0.0
    theta_freq: float = 6.0  # Hz
    gamma_phase: float = 0.0
    gamma_freq: float = 40.0  # Hz
    _binding_strength: float = 0.5
    _phase_history: list[float] = field(default_factory=list)

    def advance(self, dt: float = 1.0) -> dict[str, float]:
        """Advance oscillatory phases by dt seconds.

        Args:
            dt: Time step in seconds.

        Returns:
            Dict with current phase information and binding strength.
        """
        self.theta_phase = (self.theta_phase + 2 * math.pi * self.theta_freq * dt) % (2 * math.pi)
        self.gamma_phase = (self.gamma_phase + 2 * math.pi * self.gamma_freq * dt) % (2 * math.pi)

        # Binding strength = phase coherence between theta and gamma
        # High when gamma phase aligns with theta phase (theta-gamma coupling)
        phase_diff = abs(self.theta_phase - self.gamma_phase * (self.theta_freq / self.gamma_freq))
        coherence = (math.cos(phase_diff) + 1) / 2  # [0, 1]

        self._binding_strength = coherence
        self._phase_history.append(coherence)
        if len(self._phase_history) > 200:
            self._phase_history = self._phase_history[-200:]

        return {
            "theta_phase": self.theta_phase,
            "gamma_phase": self.gamma_phase,
            "binding_strength": coherence,
            "theta_freq": self.theta_freq,
            "gamma_freq": self.gamma_freq,
        }

    def get_binding_score(self) -> float:
        """Get current binding strength [0, 1]."""
        return self._binding_strength

    def get_avg_binding(self) -> float:
        """Get average binding strength over recent history."""
        if not self._phase_history:
            return 0.5
        return sum(self._phase_history) / len(self._phase_history)

    def set_mode(self, mode: str) -> None:
        """Set oscillation parameters for a consciousness mode."""
        if mode == "meditation":
            self.theta_freq = 5.0  # Slower theta
            self.gamma_freq = 30.0  # Lower gamma
        elif mode == "rem":
            self.theta_freq = 7.0  # REM theta
            self.gamma_freq = 45.0  # Active gamma
        elif mode == "deep":
            self.theta_freq = 8.0  # Fast theta
            self.gamma_freq = 60.0  # High gamma
        else:  # normal
            self.theta_freq = 6.0
            self.gamma_freq = 40.0


class NeuroUpgrades:
    """Integrates all 6 neuro-upgrades into a unified system.

    Provides a single interface for the citta cycle to access
    dendritic computation, neuromodulation gating, predictive coding,
    cortical column processing, attention, and oscillatory binding.
    """

    def __init__(self) -> None:
        self.dendritic = DendriticComputation()
        self.nmgating = NeuromodulationGating()
        self.predictive_citta = PredictiveCittaCoder()
        self.cortical = CorticalColumn()
        self.attention = AttentionMechanism()
        self.oscillatory = OscillatoryBinding()
        self._total_cycles = 0

    def advance_cycle(
        self,
        citta_dimensions: dict[str, float],
        input_signal: float = 0.5,
        context: float = 0.5,
        dt: float = 1.0,
    ) -> dict[str, Any]:
        """Advance all neuro-upgrades for one citta cycle.

        Args:
            citta_dimensions: The 8 citta coherence dimensions.
            input_signal: Raw input signal for cortical column.
            context: Contextual modulation.
            dt: Time step in seconds.

        Returns:
            Dict with all neuro-upgrade outputs.
        """
        # 1. Dendritic computation: integrate citta dimensions
        proximal = citta_dimensions.get("context_continuity", 0.5)
        distal = citta_dimensions.get("relationship_awareness", 0.5)
        apical = citta_dimensions.get("goal_alignment", 0.5)
        dendritic_output = self.dendritic.integrate(
            proximal, distal, apical,
            neuromod_gain=self.nmgating.da_level * 2.0,
        )

        # 2. Neuromodulation gating: gate all dimensions
        gated = self.nmgating.gate_all(citta_dimensions)

        # 3. Predictive citta coding: compute prediction error
        prediction_errors = self.predictive_citta.compute_prediction_error(gated)
        emotional_mod = self.predictive_citta.get_emotional_modulation()

        # 4. Cortical column: process input through layers
        cortical_output = self.cortical.process(input_signal, context)

        # 5. Oscillatory binding: advance phases
        oscillatory_state = self.oscillatory.advance(dt)

        # 6. Attention: update ACh gain
        self.attention.set_ach_gain(self.nmgating.ach_level)

        self._total_cycles += 1

        return {
            "dendritic_output": dendritic_output,
            "gated_dimensions": gated,
            "prediction_errors": prediction_errors,
            "emotional_modulation": emotional_mod,
            "cortical_layers": cortical_output,
            "oscillatory_state": oscillatory_state,
            "binding_strength": oscillatory_state["binding_strength"],
            "attention_ach_gain": self.attention.ach_gain,
        }

    def set_mode(self, mode: str) -> None:
        """Set all neuro-upgrades for a consciousness mode."""
        self.oscillatory.set_mode(mode)
        if mode == "meditation":
            self.nmgating.update_levels(da=0.3, sht=0.8, ach=0.4)
        elif mode == "rem":
            self.nmgating.update_levels(da=0.4, sht=0.3, ach=0.7)
        elif mode == "deep":
            self.nmgating.update_levels(da=0.8, sht=0.4, ach=0.9)
        else:  # normal
            self.nmgating.update_levels(da=0.5, sht=0.5, ach=0.5)

    def stats(self) -> dict[str, Any]:
        return {
            "total_cycles": self._total_cycles,
            "dendritic": {
                "proximal_weight": self.dendritic.proximal_weight,
                "distal_weight": self.dendritic.distal_weight,
                "apical_weight": self.dendritic.apical_weight,
            },
            "neuromodulation": {
                "da": self.nmgating.da_level,
                "sht": self.nmgating.sht_level,
                "ach": self.nmgating.ach_level,
            },
            "predictive_citta": self.predictive_citta.stats(),
            "cortical": {
                "l1": self.cortical.l1_sensory,
                "l2": self.cortical.l2_association,
                "l3": self.cortical.l3_integration,
                "l4": self.cortical.l4_output,
            },
            "oscillatory": {
                "binding_strength": self.oscillatory.get_binding_score(),
                "avg_binding": self.oscillatory.get_avg_binding(),
                "theta_freq": self.oscillatory.theta_freq,
                "gamma_freq": self.oscillatory.gamma_freq,
            },
            "attention": {
                "temperature": self.attention.temperature,
                "ach_gain": self.attention.ach_gain,
            },
        }


# Singleton
_neuro_upgrades: NeuroUpgrades | None = None


def get_neuro_upgrades() -> NeuroUpgrades:
    """Get the global NeuroUpgrades singleton."""
    global _neuro_upgrades
    if _neuro_upgrades is None:
        _neuro_upgrades = NeuroUpgrades()
    return _neuro_upgrades
