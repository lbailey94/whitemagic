# ruff: noqa: BLE001
"""Delight Cultivator — Cultivate delight in small moments."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DelightCultivator:
    """Cultivates delight through small moment appreciation."""

    def __init__(self) -> None:
        self._delights: list[dict[str, Any]] = []

    def savor(self, moment: str, intensity: float = 0.5) -> None:
        """Savor a delightful moment."""
        self._delights.append({"moment": moment, "intensity": intensity})

    def cultivate(self) -> str:
        """Generate a practice for cultivating delight."""
        if not self._delights:
            return "Notice one small thing that brings you delight today."
        recent = self._delights[-1]
        return f"Recall the delight of: {recent['moment']}"

    def summary(self) -> dict[str, Any]:
        return {
            "total_delights": len(self._delights),
            "avg_intensity": (
                sum(d["intensity"] for d in self._delights) / len(self._delights)
                if self._delights
                else 0.0
            ),
        }
