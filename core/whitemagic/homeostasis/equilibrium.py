# ruff: noqa: BLE001
"""
Homeostasis Equilibrium — Find and maintain optimal balance.

The system is in equilibrium when all metrics are within their
tolerance ranges and the rate of change is minimal.
"""

from __future__ import annotations

import logging
from typing import Any

from .metrics import HomeostasisMetrics, get_metrics

logger = logging.getLogger(__name__)


class EquilibriumDetector:
    """Detects and maintains system equilibrium."""

    def __init__(self, metrics: HomeostasisMetrics | None = None) -> None:
        self.metrics = metrics or get_metrics()
        self.equilibrium_history: list[bool] = []

    def is_at_equilibrium(self) -> bool:
        """Check if system is at equilibrium."""
        in_range = self.metrics.all_in_range()
        self.equilibrium_history.append(in_range)
        return in_range

    def stability_score(self, window: int = 10) -> float:
        """Calculate stability score over recent history."""
        recent = self.equilibrium_history[-window:]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    def find_balance_point(self, metric: str, samples: int = 20) -> float | None:
        """Find the natural balance point for a metric."""
        values = self.metrics.metrics.get(metric, [])
        if len(values) < 2:
            return None
        recent_values = [v[1] for v in values[-samples:]]
        return sum(recent_values) / len(recent_values)

    def summary(self) -> dict[str, Any]:
        return {
            "at_equilibrium": self.is_at_equilibrium(),
            "stability_score": self.stability_score(),
            "history_length": len(self.equilibrium_history),
        }


_equilibrium: EquilibriumDetector | None = None


def get_equilibrium() -> EquilibriumDetector:
    global _equilibrium
    if _equilibrium is None:
        _equilibrium = EquilibriumDetector()
    return _equilibrium
