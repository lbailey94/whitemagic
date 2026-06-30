# ruff: noqa: BLE001
"""
Harmony Metrics Dashboard — Visualize coherence across gardens.

Real-time metrics for garden harmony and system balance.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class HarmonyMetrics:
    """Tracks harmony metrics across all gardens."""

    def __init__(self) -> None:
        self.garden_harmony: dict[str, float] = {}
        self.overall_harmony: float = 0.5
        self.history: list[dict[str, Any]] = []

    def update_garden(self, name: str, harmony: float) -> None:
        """Update harmony score for a garden."""
        self.garden_harmony[name] = max(0.0, min(1.0, harmony))
        self._recalculate_overall()

    def _recalculate_overall(self) -> None:
        if self.garden_harmony:
            self.overall_harmony = sum(self.garden_harmony.values()) / len(
                self.garden_harmony
            )
        self.history.append(
            {
                "overall": self.overall_harmony,
                "gardens": dict(self.garden_harmony),
                "timestamp": time.time(),
            }
        )

    def get_harmony(self, garden: str | None = None) -> float:
        """Get harmony score for a garden or overall."""
        if garden:
            return self.garden_harmony.get(garden, 0.0)
        return self.overall_harmony

    def trend(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get harmony trend history."""
        return self.history[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "overall_harmony": round(self.overall_harmony, 3),
            "garden_count": len(self.garden_harmony),
            "gardens": {k: round(v, 3) for k, v in self.garden_harmony.items()},
            "history_length": len(self.history),
        }


_harmony: HarmonyMetrics | None = None


def get_harmony_metrics() -> HarmonyMetrics:
    global _harmony
    if _harmony is None:
        _harmony = HarmonyMetrics()
    return _harmony
