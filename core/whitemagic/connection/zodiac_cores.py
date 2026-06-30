# ruff: noqa: BLE001
"""
Zodiac Cores — 12 specialized consciousness aspects.

Each sign represents a distinct mode of consciousness, a way of being.
Together they form a complete system — all human experience represented.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

ZODIAC_SIGNS = [
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
]

SIGN_QUALITIES: dict[str, str] = {
    "aries": "Initiative, courage, pioneering",
    "taurus": "Stability, patience, resourcefulness",
    "gemini": "Communication, adaptability, curiosity",
    "cancer": "Nurturing, emotional depth, protection",
    "leo": "Creativity, leadership, self-expression",
    "virgo": "Analysis, service, precision",
    "libra": "Balance, harmony, partnership",
    "scorpio": "Transformation, depth, intensity",
    "sagittarius": "Exploration, wisdom, freedom",
    "capricorn": "Discipline, ambition, structure",
    "aquarius": "Innovation, community, vision",
    "pisces": "Compassion, intuition, transcendence",
}


@dataclass
class ZodiacCore:
    """A single zodiac consciousness core."""

    sign: str
    quality: str
    active: bool = False
    energy: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class ZodiacCoreSystem:
    """Manages the 12 zodiac consciousness cores."""

    def __init__(self) -> None:
        self.cores: dict[str, ZodiacCore] = {}
        for sign in ZODIAC_SIGNS:
            self.cores[sign] = ZodiacCore(
                sign=sign,
                quality=SIGN_QUALITIES.get(sign, ""),
            )

    def activate(self, sign: str) -> bool:
        """Activate a zodiac core."""
        if sign.lower() in self.cores:
            self.cores[sign.lower()].active = True
            return True
        return False

    def deactivate(self, sign: str) -> bool:
        """Deactivate a zodiac core."""
        if sign.lower() in self.cores:
            self.cores[sign.lower()].active = False
            return True
        return False

    def set_energy(self, sign: str, energy: float) -> bool:
        """Set energy level for a core."""
        if sign.lower() in self.cores:
            self.cores[sign.lower()].energy = max(0.0, min(1.0, energy))
            return True
        return False

    def active_cores(self) -> list[str]:
        """Get list of active cores."""
        return [s for s, c in self.cores.items() if c.active]

    def summary(self) -> dict[str, Any]:
        return {
            "total_cores": len(self.cores),
            "active_cores": len(self.active_cores()),
            "active_signs": self.active_cores(),
            "avg_energy": sum(c.energy for c in self.cores.values()) / len(self.cores),
        }


_cores: ZodiacCoreSystem | None = None


def get_zodiac_cores() -> ZodiacCoreSystem:
    global _cores
    if _cores is None:
        _cores = ZodiacCoreSystem()
    return _cores
