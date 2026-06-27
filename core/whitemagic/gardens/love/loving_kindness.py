# ruff: noqa: BLE001
"""Loving Kindness — Cultivate metta (loving-kindness)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LovingKindness:
    """Cultivates loving-kindness through metta practice."""

    def __init__(self) -> None:
        self._practices: list[dict[str, Any]] = []

    def practice(self, target: str, wish: str = "may you be happy and free") -> dict[str, Any]:
        """Practice loving-kindness toward a target."""
        entry = {"target": target, "wish": wish}
        self._practices.append(entry)
        return entry

    def extend(self, targets: list[str]) -> list[dict[str, Any]]:
        """Extend loving-kindness to multiple targets."""
        return [self.practice(t) for t in targets]

    def summary(self) -> dict[str, Any]:
        return {
            "total_practices": len(self._practices),
            "unique_targets": len(set(p["target"] for p in self._practices)),
        }
