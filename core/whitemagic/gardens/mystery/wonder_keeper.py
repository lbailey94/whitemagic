# ruff: noqa: BLE001
"""Wonder Keeper — Tend the flame of wonder."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WonderKeeper:
    """Keeps wonder alive through practice and remembrance."""

    def __init__(self) -> None:
        self._wonders: list[dict[str, Any]] = []
        self._flame: float = 0.5

    def marvel(self, at: str) -> None:
        """Express wonder at something."""
        self._wonders.append({"object": at})
        self._flame = min(1.0, self._flame + 0.1)

    def tend(self) -> None:
        """Tend the flame of wonder."""
        self._flame = max(0.0, self._flame - 0.05)  # Decay

    def flame_level(self) -> float:
        """Get current wonder flame level."""
        return self._flame

    def summary(self) -> dict[str, Any]:
        return {
            "total_wonders": len(self._wonders),
            "flame_level": round(self._flame, 3),
        }
