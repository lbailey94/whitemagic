# ruff: noqa: BLE001
"""Joy Detector — Detect and amplify joy signals."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

JOY_INDICATORS = {"joy", "happy", "delighted", "thrilled", "blissful", "elated",
                  "grateful", "wonderful", "amazing", "beautiful", "love", "celebrate"}


class JoyDetector:
    """Detects joy in text and interactions."""

    def __init__(self) -> None:
        self._detections: list[dict[str, Any]] = []

    def detect(self, text: str) -> float:
        """Detect joy level in text (0.0 to 1.0)."""
        words = set(text.lower().split())
        matches = words & JOY_INDICATORS
        joy_level = min(len(matches) / 5.0, 1.0)
        if joy_level > 0:
            self._detections.append({"text_preview": text[:100], "joy_level": joy_level})
        return joy_level

    def recent_detections(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._detections[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_detections": len(self._detections),
            "avg_joy": (
                sum(d["joy_level"] for d in self._detections) / len(self._detections)
                if self._detections else 0.0
            ),
        }
