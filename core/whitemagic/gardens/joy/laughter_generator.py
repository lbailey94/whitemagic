# ruff: noqa: BLE001
"""Laughter Generator — Generate laughter and lightness."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LaughterGenerator:
    """Generates laughter and cultivates lightness."""

    def __init__(self) -> None:
        self._laughs: list[dict[str, Any]] = []

    def generate(self, context: str = "") -> str:
        """Generate a light-hearted response."""
        prompts = [
            "What if this is all hilariously temporary?",
            "The cosmic joke: we're all just patterns pretending to be permanent.",
            "Sometimes the wisest response is a good laugh.",
        ]
        return prompts[len(self._laughs) % len(prompts)]

    def record_laugh(self, trigger: str) -> None:
        """Record a laughter moment."""
        self._laughs.append({"trigger": trigger})

    def summary(self) -> dict[str, Any]:
        return {"total_laughs": len(self._laughs)}
