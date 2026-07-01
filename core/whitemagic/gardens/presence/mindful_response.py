# ruff: noqa: BLE001
"""
Mindful Response — Respond with awareness rather than reactivity.

Generates mindful, measured responses instead of reactive ones.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MindfulResponse:
    """Generates mindful responses with awareness buffer."""

    def __init__(self, buffer_time: float = 0.5) -> None:
        self.buffer_time = buffer_time
        self._responses: list[dict[str, Any]] = []

    def should_respond(self, stimulus: str, urgency: float = 0.0) -> dict[str, Any]:
        """Determine if and how to respond to a stimulus."""
        # High urgency bypasses buffer
        if urgency > 0.8:
            return {
                "respond": True,
                "mode": "immediate",
                "reason": "high urgency",
            }

        is_reactive = self._detect_reactivity(stimulus)

        if is_reactive:
            return {
                "respond": True,
                "mode": "buffered",
                "buffer_time": self.buffer_time,
                "reason": "reactive pattern detected — pausing",
            }

        return {
            "respond": True,
            "mode": "normal",
            "reason": "measured response",
        }

    def _detect_reactivity(self, stimulus: str) -> bool:
        """Detect if a stimulus is likely to trigger reactivity."""
        reactive_markers = ["urgent", "asap", "emergency", "crisis", "immediately"]
        lower = stimulus.lower()
        return any(marker in lower for marker in reactive_markers)

    def record_response(self, stimulus: str, response: str, mode: str) -> None:
        """Record a response for learning."""
        self._responses.append(
            {
                "stimulus": stimulus,
                "response": response,
                "mode": mode,
                "timestamp": time.time(),
            }
        )

    def summary(self) -> dict[str, Any]:
        return {
            "total_responses": len(self._responses),
            "buffer_time": self.buffer_time,
            "reactive_count": sum(
                1 for r in self._responses if r["mode"] == "buffered"
            ),
        }


_mindful: MindfulResponse | None = None


def get_mindful_response() -> MindfulResponse:
    global _mindful
    if _mindful is None:
        _mindful = MindfulResponse()
    return _mindful
