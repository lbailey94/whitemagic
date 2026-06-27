# ruff: noqa: BLE001
"""
I Ching System — Book of Changes oracle.

Provides hexagram casting and interpretation for decision support.
64 hexagrams built from 8 trigrams (Ba Gua).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

TRIGRAMS: dict[str, list[int]] = {
    "qian": [1, 1, 1],   # Heaven
    "kun": [0, 0, 0],     # Earth
    "zhen": [1, 0, 0],    # Thunder
    "kan": [0, 1, 0],     # Water
    "gen": [0, 0, 1],     # Mountain
    "xun": [0, 1, 1],     # Wind
    "li": [1, 0, 1],      # Fire
    "dui": [1, 1, 0],     # Lake
}

TRIGRAM_NAMES: dict[str, str] = {
    "qian": "Heaven (Qian)",
    "kun": "Earth (Kun)",
    "zhen": "Thunder (Zhen)",
    "kan": "Water (Kan)",
    "gen": "Mountain (Gen)",
    "xun": "Wind (Xun)",
    "li": "Fire (Li)",
    "dui": "Lake (Dui)",
}


@dataclass
class Hexagram:
    """A cast hexagram."""
    number: int
    lines: list[int]
    lower_trigram: str
    upper_trigram: str
    name: str
    judgment: str


# Simplified hexagram names (full 64 would be too large for this module)
HEXAGRAM_NAMES: dict[int, str] = {
    1: "Qian (The Creative)",
    2: "Kun (The Receptive)",
    3: "Zhun (Difficulty at Beginning)",
    4: "Meng (Youthful Folly)",
    5: "Xu (Waiting)",
    6: "Song (Conflict)",
    7: "Shi (The Army)",
    8: "Bi (Holding Together)",
    11: "Tai (Peace)",
    12: "Pi (Standstill)",
    63: "Jiji (After Completion)",
    64: "Weiji (Before Completion)",
}


class IChingSystem:
    """I Ching oracle system."""

    def cast(self) -> Hexagram:
        """Cast a hexagram using coin method."""
        lines: list[int] = []
        for _ in range(6):
            # Coin method: 3 coins, heads=3, tails=2
            coins = [random.choice([2, 3]) for _ in range(3)]
            total = sum(coins)
            # 6=old yin, 7=young yang, 8=young yin, 9=old yang
            lines.append(1 if total in (7, 9) else 0)

        lower = lines[:3]
        upper = lines[3:]

        lower_trigram = self._match_trigram(lower)
        upper_trigram = self._match_trigram(upper)

        # Calculate hexagram number (simplified)
        binary = "".join(str(line) for line in lines)
        number = int(binary, 2) % 64 + 1

        name = HEXAGRAM_NAMES.get(number, f"Hexagram {number}")

        return Hexagram(
            number=number,
            lines=lines,
            lower_trigram=lower_trigram,
            upper_trigram=upper_trigram,
            name=name,
            judgment=f"Consult the wisdom of {name}",
        )

    @staticmethod
    def _match_trigram(lines: list[int]) -> str:
        for name, pattern in TRIGRAMS.items():
            if lines == pattern:
                return name
        return "kun"

    def interpret(self, hexagram: Hexagram) -> dict[str, Any]:
        """Interpret a cast hexagram."""
        return {
            "number": hexagram.number,
            "name": hexagram.name,
            "lower": TRIGRAM_NAMES.get(hexagram.lower_trigram, "Unknown"),
            "upper": TRIGRAM_NAMES.get(hexagram.upper_trigram, "Unknown"),
            "judgment": hexagram.judgment,
            "lines": hexagram.lines,
        }

    def consult(self, question: str) -> dict[str, Any]:
        """Cast and interpret for a specific question."""
        hexagram = self.cast()
        interpretation = self.interpret(hexagram)
        interpretation["question"] = question
        return interpretation


_i_ching: IChingSystem | None = None


def get_i_ching() -> IChingSystem:
    global _i_ching
    if _i_ching is None:
        _i_ching = IChingSystem()
    return _i_ching
