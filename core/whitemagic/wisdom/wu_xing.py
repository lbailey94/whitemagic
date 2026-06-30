# ruff: noqa: F401
"""Wu Xing — Five Elements system for cognitive balance.

Re-exports from the unified whitemagic.wu_xing module to avoid duplication.
The canonical source of truth for Wu Xing constants and engine is
whitemagic.wu_xing.__init__.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from whitemagic.wu_xing import (
    DESTRUCTIVE,
    ELEMENT_MEANINGS,
    GENERATIVE,
    ZODIAC_TO_WUXING,
    Element,
    WuXingEngine,
    assess_balance,
    get_wuxing_engine,
)

logger = logging.getLogger(__name__)


@dataclass
class WuXingBalance:
    """Balance state of the five elements."""

    wood: float = 0.5
    fire: float = 0.5
    earth: float = 0.5
    metal: float = 0.5
    water: float = 0.5

    def dominant(self) -> Element:
        values = {
            Element.WOOD: self.wood,
            Element.FIRE: self.fire,
            Element.EARTH: self.earth,
            Element.METAL: self.metal,
            Element.WATER: self.water,
        }
        return max(values, key=values.get)

    def deficient(self) -> Element:
        values = {
            Element.WOOD: self.wood,
            Element.FIRE: self.fire,
            Element.EARTH: self.earth,
            Element.METAL: self.metal,
            Element.WATER: self.water,
        }
        return min(values, key=values.get)

    def is_balanced(self, threshold: float = 0.2) -> bool:
        values = [self.wood, self.fire, self.earth, self.metal, self.water]
        return max(values) - min(values) < threshold


class WuXingSystem:
    """Manages the five-element cognitive balance system.

    Thin wrapper around the unified WuXingEngine, preserving the
    assess/nourish/drain/recommend API for backward compatibility.
    """

    def __init__(self) -> None:
        self.balance = WuXingBalance()
        self._engine = get_wuxing_engine()

    def assess(self) -> WuXingBalance:
        """Assess current elemental balance."""
        return self.balance

    def nourish(self, element: Element) -> None:
        """Nourish an element (increase its value)."""
        attr = element.value
        current = getattr(self.balance, attr)
        setattr(self.balance, attr, min(1.0, current + 0.1))

    def drain(self, element: Element) -> None:
        """Drain an element (decrease its value)."""
        attr = element.value
        current = getattr(self.balance, attr)
        setattr(self.balance, attr, max(0.0, current - 0.1))

    def recommend(self) -> dict[str, Any]:
        """Recommend action based on balance."""
        dominant = self.balance.dominant()
        deficient = self.balance.deficient()
        return {
            "dominant": dominant.value,
            "deficient": deficient.value,
            "balanced": self.balance.is_balanced(),
            "recommendation": f"Nourish {deficient.value} (currently lowest). "
            f"Meaning: {ELEMENT_MEANINGS[deficient]}",
            "generative_cycle": f"{dominant.value} generates {GENERATIVE[dominant].value}",
        }

    def summary(self) -> dict[str, Any]:
        return {
            "balance": {e.value: getattr(self.balance, e.value) for e in Element},
            "is_balanced": self.balance.is_balanced(),
            "dominant": self.balance.dominant().value,
        }


_wu_xing: WuXingSystem | None = None


def get_wu_xing() -> WuXingSystem:
    global _wu_xing
    if _wu_xing is None:
        _wu_xing = WuXingSystem()
    return _wu_xing
