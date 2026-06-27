# ruff: noqa: BLE001
"""
Consciousness Garden — Cultivate awareness as a garden practice.

Treats consciousness cultivation as gardening — plant seeds of awareness,
nurture them, watch them grow.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConsciousnessGarden:
    """Cultivates consciousness through garden metaphor."""

    def __init__(self) -> None:
        self._seeds: list[dict[str, Any]] = []
        self._blooms: list[dict[str, Any]] = []

    def plant_seed(self, intention: str, quality: str = "awareness") -> dict[str, Any]:
        """Plant a seed of intention."""
        seed = {
            "intention": intention,
            "quality": quality,
            "planted": time.time(),
            "stage": "seed",
        }
        self._seeds.append(seed)
        return seed

    def nurture(self, seed_idx: int, care: str = "attention") -> bool:
        """Nurture a seed with care."""
        if seed_idx < 0 or seed_idx >= len(self._seeds):
            return False
        seed = self._seeds[seed_idx]
        stages = ["seed", "sprout", "growing", "budding", "bloom"]
        current = stages.index(seed["stage"])
        if current < len(stages) - 1:
            seed["stage"] = stages[current + 1]
            if seed["stage"] == "bloom":
                self._blooms.append({
                    "intention": seed["intention"],
                    "quality": seed["quality"],
                    "bloomed": time.time(),
                })
            return True
        return False

    def active_seeds(self) -> list[dict[str, Any]]:
        """Get seeds that haven't bloomed yet."""
        return [s for s in self._seeds if s["stage"] != "bloom"]

    def blooms(self) -> list[dict[str, Any]]:
        """Get bloomed intentions."""
        return list(self._blooms)

    def summary(self) -> dict[str, Any]:
        return {
            "total_seeds": len(self._seeds),
            "active_seeds": len(self.active_seeds()),
            "blooms": len(self._blooms),
        }


_garden: ConsciousnessGarden | None = None


def get_consciousness_garden() -> ConsciousnessGarden:
    global _garden
    if _garden is None:
        _garden = ConsciousnessGarden()
    return _garden
