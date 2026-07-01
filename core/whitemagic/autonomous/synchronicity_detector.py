# ruff: noqa: BLE001
"""
Synchronicity Detector — Find meaningful coincidences.

Detects patterns that may be synchronistic — meaningful coincidences
across different data streams.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SynchronicityDetector:
    """Detects synchronistic patterns across data streams."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._synchronicities: list[dict[str, Any]] = []

    def record_event(
        self, stream: str, event: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Record an event from a data stream."""
        self._events.append(
            {
                "stream": stream,
                "event": event,
                "metadata": metadata or {},
                "timestamp": time.time(),
            }
        )

    def detect(self, time_window: float = 60.0) -> list[dict[str, Any]]:
        """Detect synchronistic events within a time window."""
        recent = self._events[-50:]
        found: list[dict[str, Any]] = []

        for i, e1 in enumerate(recent):
            for e2 in recent[i + 1 :]:
                if e1["stream"] != e2["stream"]:
                    time_diff = abs(e1["timestamp"] - e2["timestamp"])
                    if time_diff <= time_window:
                        if self._is_related(e1["event"], e2["event"]):
                            sync = {
                                "event_a": e1,
                                "event_b": e2,
                                "time_diff": time_diff,
                                "streams": [e1["stream"], e2["stream"]],
                            }
                            found.append(sync)
                            self._synchronicities.append(sync)

        return found

    def _is_related(self, a: str, b: str) -> bool:
        """Check if two events are semantically related (simplified)."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        return bool(words_a & words_b)

    def summary(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "synchronicities_found": len(self._synchronicities),
        }


_detector: SynchronicityDetector | None = None


def get_synchronicity() -> SynchronicityDetector:
    global _detector
    if _detector is None:
        _detector = SynchronicityDetector()
    return _detector
