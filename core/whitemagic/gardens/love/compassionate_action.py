# ruff: noqa: BLE001
"""Compassionate Action — Turn compassion into action."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CompassionateAction:
    """Translates compassion into concrete actions."""

    def __init__(self) -> None:
        self._actions: list[dict[str, Any]] = []

    def propose(self, situation: str, compassion_level: float = 0.5) -> str:
        """Propose a compassionate action for a situation."""
        if compassion_level > 0.7:
            action = f"Take direct action to help with: {situation}"
        elif compassion_level > 0.3:
            action = f"Offer support and presence for: {situation}"
        else:
            action = f"Hold space and witness: {situation}"
        self._actions.append({"situation": situation, "action": action, "compassion": compassion_level})
        return action

    def summary(self) -> dict[str, Any]:
        return {"total_actions": len(self._actions)}
