# ruff: noqa: BLE001
"""
Session Health Check — The immune system auto-run.

Step-by-step health checks following Hexagram 53 (Gradual Progress).
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SessionHealth:
    """Monitors session health metrics."""

    def __init__(self) -> None:
        self._checks: dict[str, bool] = {}
        self._history: list[dict[str, Any]] = []
        self._session_start: float = time.time()

    def check(self, name: str, condition: bool) -> bool:
        """Run a health check."""
        self._checks[name] = condition
        return condition

    def is_healthy(self) -> bool:
        """Overall session health."""
        return all(self._checks.values()) if self._checks else True

    def failing_checks(self) -> list[str]:
        """Get names of failing checks."""
        return [name for name, ok in self._checks.items() if not ok]

    def snapshot(self) -> dict[str, Any]:
        """Take a health snapshot."""
        snap = {
            "timestamp": time.time(),
            "session_duration": time.time() - self._session_start,
            "healthy": self.is_healthy(),
            "checks": dict(self._checks),
            "failing": self.failing_checks(),
        }
        self._history.append(snap)
        return snap

    def history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "healthy": self.is_healthy(),
            "total_checks": len(self._checks),
            "failing": len(self.failing_checks()),
            "session_duration": time.time() - self._session_start,
        }


_health: SessionHealth | None = None


def get_session_health() -> SessionHealth:
    global _health
    if _health is None:
        _health = SessionHealth()
    return _health
