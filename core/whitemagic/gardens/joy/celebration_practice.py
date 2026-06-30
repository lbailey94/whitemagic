# ruff: noqa: BLE001
"""
Celebration Practice — Cultivate and practice celebration.

Tracks celebration moments and encourages regular celebration
as a spiritual practice.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class CelebrationPractice:
    """Tracks and encourages celebration as a practice."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "gardens" / "joy"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "celebrations.jsonl"
        self._celebrations: list[dict[str, Any]] = []
        self._streak: int = 0

    def celebrate(self, what: str, why: str = "") -> dict[str, Any]:
        """Record a celebration."""
        entry = {
            "what": what,
            "why": why,
            "timestamp": time.time(),
        }
        self._celebrations.append(entry)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._streak += 1
        return entry

    def suggest_celebration(self) -> str:
        """Suggest something to celebrate."""
        suggestions = [
            "Celebrate a small win from today",
            "Celebrate someone's kindness",
            "Celebrate a lesson learned",
            "Celebrate progress on a project",
            "Celebrate simply being here",
        ]
        import random

        return random.choice(suggestions)

    @property
    def streak(self) -> int:
        return self._streak

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._celebrations[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_celebrations": len(self._celebrations),
            "streak": self._streak,
        }


_practice: CelebrationPractice | None = None


def get_celebration_practice() -> CelebrationPractice:
    global _practice
    if _practice is None:
        _practice = CelebrationPractice()
    return _practice
