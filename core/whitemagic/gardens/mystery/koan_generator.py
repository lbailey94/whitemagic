# ruff: noqa: BLE001
"""Koan Generator — Generate koans for contemplation."""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

KOAN_TEMPLATES = [
    "What is the sound of one hand {action}?",
    "When you {action}, what {action}s?",
    "Before {action}, what is there?",
    "Show me your original face before you were born.",
    "The {thing} does not {action}, yet {action} happens.",
    "What is this?",
]


class KoanGenerator:
    """Generates koans for contemplation."""

    def __init__(self) -> None:
        self._koans: list[str] = []

    def generate(self) -> str:
        """Generate a koan."""
        actions = ["clapping", "thinking", "arising", "ceasing"]
        things = ["mind", "mirror", "moon", "river"]
        template = random.choice(KOAN_TEMPLATES)
        koan = template.format(
            action=random.choice(actions),
            thing=random.choice(things),
        )
        self._koans.append(koan)
        return koan

    def history(self) -> list[str]:
        return list(self._koans)

    def summary(self) -> dict[str, Any]:
        return {"total_generated": len(self._koans)}
