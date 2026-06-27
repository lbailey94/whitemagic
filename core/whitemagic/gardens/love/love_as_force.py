# ruff: noqa: BLE001
"""Love as Force — Love as a driving force in the system."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LoveAsForce:
    """Treats love as a systemic force, not just an emotion."""

    def __init__(self) -> None:
        self._force_events: list[dict[str, Any]] = []
        self._current_force: float = 0.5

    def channel(self, direction: str, intensity: float = 0.5) -> None:
        """Channel love as a force in a direction."""
        self._force_events.append({"direction": direction, "intensity": intensity})
        self._current_force = max(0.0, min(1.0, self._current_force + intensity * 0.1))

    def current_force(self) -> float:
        """Get current love force level."""
        return self._current_force

    def summary(self) -> dict[str, Any]:
        return {
            "current_force": round(self._current_force, 3),
            "total_events": len(self._force_events),
        }
