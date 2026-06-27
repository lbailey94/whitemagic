# ruff: noqa: BLE001
"""
Homeostasis Feedback — Corrective actions to restore balance.

Implements feedback loops that detect deviations from set points
and apply corrective actions based on biological negative feedback.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .metrics import HomeostasisMetrics, get_metrics

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """Negative feedback loop for system homeostasis."""

    def __init__(self, metrics: HomeostasisMetrics | None = None) -> None:
        self.metrics = metrics or get_metrics()
        self.actions: dict[str, Callable[[float], None]] = {}
        self.correction_history: list[dict[str, Any]] = []

    def register_action(self, metric: str, action: Callable[[float], None]) -> None:
        """Register a corrective action for a metric."""
        self.actions[metric] = action

    def check_and_correct(self) -> list[dict[str, Any]]:
        """Check all metrics and apply corrections where needed."""
        corrections: list[dict[str, Any]] = []
        for metric, action in self.actions.items():
            if not self.metrics.is_in_range(metric):
                current = self.metrics.get_current(metric)
                if current is not None:
                    deviation = current - self.metrics.set_points.get(metric, 0)
                    try:
                        action(deviation)
                        correction = {
                            "metric": metric,
                            "deviation": deviation,
                            "action": "applied",
                        }
                        corrections.append(correction)
                        self.correction_history.append(correction)
                    except Exception as e:
                        logger.debug("Correction failed for %s: %s", metric, e)
        return corrections

    def summary(self) -> dict[str, Any]:
        return {
            "registered_actions": len(self.actions),
            "total_corrections": len(self.correction_history),
        }


_feedback: FeedbackLoop | None = None


def get_feedback() -> FeedbackLoop:
    global _feedback
    if _feedback is None:
        _feedback = FeedbackLoop()
    return _feedback
