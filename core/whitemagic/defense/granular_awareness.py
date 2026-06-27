# ruff: noqa: BLE001
"""
Granular Awareness — Enhanced immune system integration.

Combines homeostatic monitoring with immune system responses.
Detects sub-kilobyte changes and knows exactly what changed.
"""

from __future__ import annotations

import logging
from typing import Any

from .homeostatic_monitor import get_monitor

logger = logging.getLogger(__name__)


class GranularAwareness:
    """Combines homeostatic monitoring with immune responses."""

    def __init__(self) -> None:
        self.change_history: list[dict[str, Any]] = []

    def scan(self) -> dict[str, Any]:
        """Run a granular awareness scan."""
        monitor = get_monitor()
        changes = monitor.compare()

        result: dict[str, Any] = {
            "total_changes": len(changes),
            "changes": [],
            "immune_assessment": "clear",
        }

        for change in changes:
            entry = {
                "path": change.path,
                "type": change.change_type,
                "size_delta": change.new_size - change.old_size,
            }
            result["changes"].append(entry)
            self.change_history.append(entry)

        if len(changes) > 10:
            result["immune_assessment"] = "elevated"
        if any(c.change_type == "removed" for c in changes):
            result["immune_assessment"] = "alert"

        return result

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.change_history[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_scans": len(self.change_history),
            "recent_changes": len(self.change_history[-10:]),
        }


_awareness: GranularAwareness | None = None


def get_granular_awareness() -> GranularAwareness:
    global _awareness
    if _awareness is None:
        _awareness = GranularAwareness()
    return _awareness
