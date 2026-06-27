# ruff: noqa: BLE001
"""
Delta-Based Session Summary Generator — Track changes, not redundancy.

Generates session summaries that focus on what changed rather than
re-describing everything. Dramatically reduces token usage.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DeltaTracker:
    """Tracks deltas (changes) between session states."""

    def __init__(self) -> None:
        self._deltas: list[dict[str, Any]] = []
        self._baseline: dict[str, Any] = {}

    def set_baseline(self, state: dict[str, Any]) -> None:
        """Set the baseline state for delta comparison."""
        self._baseline = dict(state)

    def record_delta(self, key: str, old_value: Any, new_value: Any) -> None:
        """Record a change."""
        self._deltas.append({
            "key": key,
            "old": old_value,
            "new": new_value,
            "timestamp": time.time(),
        })

    def compare(self, current: dict[str, Any]) -> list[dict[str, Any]]:
        """Compare current state against baseline and record deltas."""
        for key, value in current.items():
            old = self._baseline.get(key)
            if old != value:
                self.record_delta(key, old, value)
        # Check for removed keys
        for key in self._baseline:
            if key not in current:
                self.record_delta(key, self._baseline[key], None)
        self._baseline = dict(current)
        return self._deltas[-10:]

    def summary(self) -> dict[str, Any]:
        """Generate a delta-based summary."""
        return {
            "total_deltas": len(self._deltas),
            "unique_keys_changed": len(set(d["key"] for d in self._deltas)),
            "recent": self._deltas[-5:],
        }


_tracker: DeltaTracker | None = None


def get_delta_tracker() -> DeltaTracker:
    global _tracker
    if _tracker is None:
        _tracker = DeltaTracker()
    return _tracker
