# ruff: noqa: BLE001
"""Care Metrics — Measure care quality."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CareMetrics:
    """Tracks quality of care provided."""

    def __init__(self) -> None:
        self._care_events: list[dict[str, Any]] = []

    def record_care(self, recipient: str, quality: float, duration: float = 0.0) -> None:
        """Record a care event."""
        self._care_events.append({
            "recipient": recipient,
            "quality": max(0.0, min(1.0, quality)),
            "duration": duration,
        })

    def avg_quality(self) -> float:
        if not self._care_events:
            return 0.0
        return sum(e["quality"] for e in self._care_events) / len(self._care_events)

    def summary(self) -> dict[str, Any]:
        return {
            "total_care_events": len(self._care_events),
            "avg_quality": round(self.avg_quality(), 3),
        }
