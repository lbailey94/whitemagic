# ruff: noqa: BLE001
"""
Chronological Timeline — Time-based memory navigation.

Organizes all memories, events, and interactions along a timeline.
Enables asking "What happened on November 20th?" or "Show me last week's work".
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class ChronologicalTimeline:
    """Time-ordered event log for memory navigation."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "memory_matrix"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.timeline_file = self.data_dir / "timeline.jsonl"
        self._events: list[dict[str, Any]] = []

    def add_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Add an event to the timeline."""
        entry = {
            "event_type": event_type,
            "data": data or {},
            "timestamp": time.time(),
        }
        self._events.append(entry)
        with open(self.timeline_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_events(
        self, limit: int = 50, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get recent events, optionally filtered by type."""
        events = (
            self._events
            if not event_type
            else [e for e in self._events if e["event_type"] == event_type]
        )
        return events[-limit:]

    def get_range(self, start: float, end: float) -> list[dict[str, Any]]:
        """Get events within a time range."""
        return [e for e in self._events if start <= e["timestamp"] <= end]

    def get_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """Get events for a specific date (YYYY-MM-DD)."""
        import datetime

        target = datetime.date.fromisoformat(date_str)
        return [
            e
            for e in self._events
            if datetime.date.fromtimestamp(e["timestamp"]) == target
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "event_types": list(set(e["event_type"] for e in self._events)),
        }


_timeline: ChronologicalTimeline | None = None


def get_timeline() -> ChronologicalTimeline:
    global _timeline
    if _timeline is None:
        _timeline = ChronologicalTimeline()
    return _timeline
