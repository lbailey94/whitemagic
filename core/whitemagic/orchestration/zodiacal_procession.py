# ruff: noqa: BLE001
"""
Zodiacal Procession — Yin/Yang autonomous cycle system.

Implements the bidirectional zodiacal procession for autonomous operation:
- Yin Phase: Pisces → Aquarius → Capricorn → ... → Aries (receptive)
- Yang Phase: Aries → Taurus → Gemini → ... → Pisces (creative)
- Fixed Signs as bidirectional hubs (Taurus, Leo, Scorpio, Aquarius)

"Like Finnegans Wake, it never actually ends, but curves back to begin again"
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

ZODIAC_ORDER = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

FIXED_SIGNS = {"taurus", "leo", "scorpio", "aquarius"}


class ProcessionDirection(Enum):
    YIN = "yin"   # Receptive: Pisces → Aries
    YANG = "yang"  # Creative: Aries → Pisces


class ZodiacalProcession:
    """Manages the zodiacal procession cycle."""

    def __init__(self) -> None:
        self.current_sign: str = "aries"
        self.direction: ProcessionDirection = ProcessionDirection.YANG
        self.cycle_count: int = 0
        self.history: list[dict[str, Any]] = []

    def advance(self) -> str:
        """Advance to the next sign in the procession."""
        idx = ZODIAC_ORDER.index(self.current_sign)

        if self.direction == ProcessionDirection.YANG:
            idx = (idx + 1) % len(ZODIAC_ORDER)
        else:
            idx = (idx - 1) % len(ZODIAC_ORDER)

        self.current_sign = ZODIAC_ORDER[idx]
        self.cycle_count += 1

        entry = {
            "sign": self.current_sign,
            "direction": self.direction.value,
            "is_fixed": self.current_sign in FIXED_SIGNS,
            "cycle": self.cycle_count,
            "timestamp": time.time(),
        }
        self.history.append(entry)

        # At fixed signs, consider direction change
        if self.current_sign in FIXED_SIGNS and self.cycle_count % 6 == 0:
            self._toggle_direction()

        return self.current_sign

    def _toggle_direction(self) -> None:
        if self.direction == ProcessionDirection.YANG:
            self.direction = ProcessionDirection.YIN
        else:
            self.direction = ProcessionDirection.YANG

    def set_sign(self, sign: str) -> bool:
        """Set the current sign directly."""
        if sign.lower() in ZODIAC_ORDER:
            self.current_sign = sign.lower()
            return True
        return False

    def status(self) -> dict[str, Any]:
        return {
            "current_sign": self.current_sign,
            "direction": self.direction.value,
            "cycle_count": self.cycle_count,
            "is_fixed": self.current_sign in FIXED_SIGNS,
        }


_procession: ZodiacalProcession | None = None


def get_procession() -> ZodiacalProcession:
    global _procession
    if _procession is None:
        _procession = ZodiacalProcession()
    return _procession
