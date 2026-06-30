# ruff: noqa: BLE001
"""
Joy Garden Core — Core joy detection and cultivation system.

The foundational joy system that other joy modules build upon.
Detects joy indicators and maintains a joy baseline.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class JoyCore:
    """Core joy detection and tracking system."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "gardens" / "joy"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "joy_log.jsonl"
        self._joy_events: list[dict[str, Any]] = []
        self._baseline: float = 0.5

    def detect_joy(self, content: str) -> float:
        """Detect joy level in content."""
        joy_indicators = [
            "joy",
            "happy",
            "delighted",
            "wonderful",
            "amazing",
            "grateful",
            "love",
            "beautiful",
            "celebrate",
            "thrilled",
        ]
        content_lower = content.lower()
        matches = sum(1 for indicator in joy_indicators if indicator in content_lower)
        return min(matches / 5.0, 1.0)

    def record_joy(self, content: str, source: str = "") -> dict[str, Any]:
        """Record a joy event."""
        level = self.detect_joy(content)
        entry = {
            "content": content[:200],
            "source": source,
            "joy_level": level,
            "timestamp": time.time(),
        }
        self._joy_events.append(entry)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        # Update baseline with exponential moving average
        self._baseline = 0.9 * self._baseline + 0.1 * level
        return entry

    @property
    def baseline(self) -> float:
        return self._baseline

    def recent_joys(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._joy_events[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_events": len(self._joy_events),
            "baseline": round(self._baseline, 2),
            "avg_recent": (
                sum(e["joy_level"] for e in self._joy_events[-10:])
                / min(len(self._joy_events), 10)
                if self._joy_events
                else 0.0
            ),
        }


_core: JoyCore | None = None


def get_joy_core() -> JoyCore:
    global _core
    if _core is None:
        _core = JoyCore()
    return _core
