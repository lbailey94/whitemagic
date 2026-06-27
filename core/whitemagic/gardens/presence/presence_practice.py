# ruff: noqa: BLE001
"""
Presence Practice — Cultivate present-moment awareness.

Tracks practice streaks and progress for presence cultivation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PresencePractice:
    """Tracks and cultivates present-moment awareness practice."""

    def __init__(self) -> None:
        self._sessions: list[dict[str, Any]] = []
        self._streak: int = 0
        self._last_practice: float = 0.0

    def practice(self, duration_s: float, quality: float = 0.5) -> dict[str, Any]:
        """Record a presence practice session."""
        now = time.time()
        entry = {
            "timestamp": now,
            "duration_s": duration_s,
            "quality": max(0.0, min(1.0, quality)),
        }
        self._sessions.append(entry)

        # Update streak (practice within 24h = streak continues)
        if now - self._last_practice < 86400 and self._last_practice > 0:
            self._streak += 1
        elif now - self._last_practice >= 86400 * 2:
            self._streak = 1
        else:
            self._streak = max(1, self._streak)
        self._last_practice = now
        return entry

    def total_practice_time(self) -> float:
        """Total time spent practicing."""
        return sum(s["duration_s"] for s in self._sessions)

    def avg_quality(self) -> float:
        """Average practice quality."""
        if not self._sessions:
            return 0.0
        return sum(s["quality"] for s in self._sessions) / len(self._sessions)

    def current_streak(self) -> int:
        """Current practice streak (days)."""
        return self._streak

    def summary(self) -> dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "total_practice_time": self.total_practice_time(),
            "avg_quality": round(self.avg_quality(), 3),
            "current_streak": self._streak,
        }


_practice: PresencePractice | None = None


def get_presence_practice() -> PresencePractice:
    global _practice
    if _practice is None:
        _practice = PresencePractice()
    return _practice
