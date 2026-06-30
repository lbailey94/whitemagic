"""Karma Ledger as Causal Ledger (Objective T).

Transforms the Karma Ledger into a causal inference data source.
When an improvement is applied, all downstream effects (including
unintended) get recorded with timestamps.

Causal utility = sum(intended effects) - sum(unintended side-effects),
weighted by confidence.

Feeds into C (counterfactual estimation) as the primary data source.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EffectType(Enum):
    """Type of effect recorded in the causal ledger."""

    INTENDED = "intended"
    UNINTENDED = "unintended"
    SIDE_EFFECT = "side_effect"


@dataclass
class CausalEffect:
    """A single causal effect recorded in the ledger."""

    effect_id: str
    improvement_id: str
    effect_type: EffectType
    effect_metric: str  # What changed (e.g., "recall_quality")
    effect_magnitude: float  # How much it changed (signed)
    effect_timestamp: float = field(default_factory=time.time)
    effect_confidence: float = (
        0.5  # How confident we are this was caused by the improvement
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class CausalLedger:
    """Tracks causal effects of improvements for inference.

    Records intended and unintended effects, computes causal utility,
    and provides data for difference-in-differences analysis.
    """

    def __init__(self) -> None:
        self._effects: list[CausalEffect] = []
        self._by_improvement: dict[str, list[CausalEffect]] = {}

    def record_effect(
        self,
        improvement_id: str,
        effect_type: EffectType,
        effect_metric: str,
        effect_magnitude: float,
        effect_confidence: float = 0.5,
        timestamp: float | None = None,
    ) -> CausalEffect:
        """Record a causal effect.

        Args:
            improvement_id: Which improvement caused this effect.
            effect_type: Intended, unintended, or side_effect.
            effect_metric: What metric changed.
            effect_magnitude: How much it changed (signed).
            effect_confidence: Confidence this was caused by the improvement.
            timestamp: When the effect was observed.

        Returns:
            The recorded CausalEffect.
        """
        ts = timestamp or time.time()
        effect_id = f"effect_{len(self._effects)}_{improvement_id}"
        effect = CausalEffect(
            effect_id=effect_id,
            improvement_id=improvement_id,
            effect_type=effect_type,
            effect_metric=effect_metric,
            effect_magnitude=effect_magnitude,
            effect_timestamp=ts,
            effect_confidence=effect_confidence,
        )
        self._effects.append(effect)
        self._by_improvement.setdefault(improvement_id, []).append(effect)
        return effect

    def get_effects(self, improvement_id: str) -> list[CausalEffect]:
        """Get all effects for an improvement."""
        return self._by_improvement.get(improvement_id, [])

    def get_causal_utility(self, improvement_id: str) -> float:
        """Compute causal utility of an improvement.

        causal_utility = Σ(intended_magnitude * confidence)
                       - Σ(unintended_magnitude * confidence)
                       - Σ(side_effect_magnitude * confidence)

        Args:
            improvement_id: The improvement to evaluate.

        Returns:
            Causal utility score (higher is better).
        """
        effects = self.get_effects(improvement_id)
        utility = 0.0
        for e in effects:
            if e.effect_type == EffectType.INTENDED:
                utility += e.effect_magnitude * e.effect_confidence
            elif e.effect_type == EffectType.UNINTENDED:
                utility -= abs(e.effect_magnitude) * e.effect_confidence
            elif e.effect_type == EffectType.SIDE_EFFECT:
                utility -= (
                    abs(e.effect_magnitude) * e.effect_confidence * 0.5
                )  # Side effects weighted less
        return utility

    def get_all_utilities(self) -> dict[str, float]:
        """Get causal utility for all improvements."""
        return {
            imp_id: self.get_causal_utility(imp_id) for imp_id in self._by_improvement
        }

    def get_metric_history(
        self,
        metric: str,
        improvement_id: str | None = None,
    ) -> list[tuple[float, float]]:
        """Get temporal history of a metric for DiD analysis.

        Args:
            metric: The metric to track.
            improvement_id: Optional filter by improvement.

        Returns:
            List of (timestamp, magnitude) tuples sorted by time.
        """
        effects = (
            self._effects
            if improvement_id is None
            else self.get_effects(improvement_id)
        )
        history = [
            (e.effect_timestamp, e.effect_magnitude)
            for e in effects
            if e.effect_metric == metric
        ]
        return sorted(history, key=lambda x: x[0])

    def difference_in_differences(
        self,
        improvement_id: str,
        metric: str,
    ) -> dict[str, Any]:
        """Compute difference-in-differences for an improvement on a metric.

        Compares pre-improvement and post-improvement trajectories.

        Args:
            improvement_id: The improvement to analyze.
            metric: The metric to compare.

        Returns:
            Dict with pre_mean, post_mean, diff, and confidence.
        """
        effects = self.get_effects(improvement_id)
        metric_effects = [e for e in effects if e.effect_metric == metric]

        if not metric_effects:
            return {"error": "no_data", "metric": metric}

        # Split by before/after improvement (using first effect timestamp as boundary)
        if len(metric_effects) < 2:
            return {
                "pre_mean": 0.0,
                "post_mean": metric_effects[0].effect_magnitude,
                "diff": metric_effects[0].effect_magnitude,
                "n_pre": 0,
                "n_post": 1,
            }

        # Use median timestamp as split point
        timestamps = sorted(e.effect_timestamp for e in metric_effects)
        split = timestamps[len(timestamps) // 2]

        pre = [e.effect_magnitude for e in metric_effects if e.effect_timestamp < split]
        post = [
            e.effect_magnitude for e in metric_effects if e.effect_timestamp >= split
        ]

        pre_mean = sum(pre) / len(pre) if pre else 0.0
        post_mean = sum(post) / len(post) if post else 0.0

        return {
            "pre_mean": pre_mean,
            "post_mean": post_mean,
            "diff": post_mean - pre_mean,
            "n_pre": len(pre),
            "n_post": len(post),
        }

    def get_stats(self) -> dict[str, Any]:
        type_counts = {t.value: 0 for t in EffectType}
        for e in self._effects:
            type_counts[e.effect_type.value] += 1
        return {
            "total_effects": len(self._effects),
            "total_improvements": len(self._by_improvement),
            "effect_types": type_counts,
        }
