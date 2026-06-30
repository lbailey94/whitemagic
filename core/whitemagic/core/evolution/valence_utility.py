"""Emotional Valence as Utility Signal (Objective K).

Uses the z-axis (emotional) of 5D memory as a dopamine-like reward prediction
error (RPE) signal. When an improvement's outcome exceeds expectations,
associated memories get a positive emotional boost, increasing confidence
in similar future improvements.

RPE: δ = actual_outcome - predicted_outcome
  δ > 0 → surprise success → boost z (positive valence)
  δ < 0 → surprise failure → reduce z (negative valence)
  δ ≈ 0 → expected → no change

Over time, the system develops "preferences" — improvement types that
consistently produce positive valence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValenceRecord:
    """A single emotional valence update from an outcome."""

    hypothesis_id: str
    prediction: float  # Predicted outcome (0-1)
    actual: float  # Actual outcome (0-1, or 0/1 for binary)
    rpe: float  # Reward prediction error = actual - prediction
    valence_delta: float  # Change applied to z-coordinate
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ValenceUtilityTracker:
    """Tracks emotional valence as a utility signal for learning.

    Computes reward prediction errors and adjusts confidence in
    improvement categories based on accumulated valence.
    """

    def __init__(self, learning_rate: float = 0.1, valence_decay: float = 0.95) -> None:
        self._learning_rate = learning_rate
        self._valence_decay = valence_decay
        self._records: list[ValenceRecord] = []
        self._category_valence: dict[str, float] = {}  # category → accumulated valence
        self._hypothesis_valence: dict[str, float] = {}  # hypothesis_id → valence

    def compute_rpe(self, prediction: float, actual: float) -> float:
        """Compute reward prediction error.

        δ = actual - prediction
        """
        return actual - prediction

    def record_outcome(
        self,
        hypothesis_id: str,
        prediction: float,
        actual: float,
        category: str = "default",
        timestamp: float = 0.0,
    ) -> ValenceRecord:
        """Record an outcome and update valence.

        Args:
            hypothesis_id: The hypothesis ID.
            prediction: Predicted outcome probability (0-1).
            actual: Actual outcome (0-1, or 0/1 for binary).
            category: Improvement category for tracking preferences.
            timestamp: Optional timestamp.

        Returns:
            The ValenceRecord with RPE and valence delta.
        """
        rpe = self.compute_rpe(prediction, actual)

        # Valence delta proportional to RPE, scaled by learning rate
        valence_delta = rpe * self._learning_rate

        record = ValenceRecord(
            hypothesis_id=hypothesis_id,
            prediction=prediction,
            actual=actual,
            rpe=rpe,
            valence_delta=valence_delta,
            timestamp=timestamp,
            metadata={"category": category},
        )
        self._records.append(record)

        # Update hypothesis-level valence
        current = self._hypothesis_valence.get(hypothesis_id, 0.0)
        self._hypothesis_valence[hypothesis_id] = current + valence_delta

        # Update category-level valence (with decay)
        cat_current = self._category_valence.get(category, 0.0)
        self._category_valence[category] = (
            cat_current * self._valence_decay + valence_delta
        )

        return record

    def get_valence(self, hypothesis_id: str) -> float:
        """Get accumulated valence for a hypothesis."""
        return self._hypothesis_valence.get(hypothesis_id, 0.0)

    def get_category_valence(self, category: str) -> float:
        """Get accumulated valence for an improvement category."""
        return self._category_valence.get(category, 0.0)

    def get_confidence_adjustment(self, category: str) -> float:
        """Get a confidence adjustment based on category valence.

        Positive valence → boost confidence (up to +0.2)
        Negative valence → reduce confidence (down to -0.2)
        Zero valence → no adjustment

        Args:
            category: The improvement category.

        Returns:
            Confidence adjustment in [-0.2, +0.2].
        """
        valence = self.get_category_valence(category)
        # Clamp to [-0.2, 0.2]
        return max(-0.2, min(0.2, valence))

    def get_preferences(self) -> dict[str, float]:
        """Get category preference ranking based on accumulated valence.

        Returns:
            Dict of category → valence, sorted by valence (highest first).
        """
        return dict(
            sorted(self._category_valence.items(), key=lambda x: x[1], reverse=True)
        )

    def get_records(self, hypothesis_id: str | None = None) -> list[ValenceRecord]:
        """Get valence records, optionally filtered by hypothesis."""
        if hypothesis_id is None:
            return list(self._records)
        return [r for r in self._records if r.hypothesis_id == hypothesis_id]

    def apply_decay(self) -> None:
        """Apply decay to all category valence values."""
        for cat in self._category_valence:
            self._category_valence[cat] *= self._valence_decay

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_records": len(self._records),
            "categories_tracked": len(self._category_valence),
            "hypotheses_tracked": len(self._hypothesis_valence),
            "avg_rpe": (
                sum(r.rpe for r in self._records) / len(self._records)
                if self._records
                else 0.0
            ),
            "top_preferences": list(self.get_preferences().items())[:5],
        }
