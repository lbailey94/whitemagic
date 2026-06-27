# ruff: noqa: BLE001
"""
Wu Xing — Five Elements system for cognitive balance.

The five elements (Wood, Fire, Earth, Metal, Water) represent
cognitive phases and their generative/destructive cycles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Element(Enum):
    WOOD = "wood"
    FIRE = "fire"
    EARTH = "earth"
    METAL = "metal"
    WATER = "water"


# Generative cycle: Wood → Fire → Earth → Metal → Water → Wood
GENERATIVE: dict[Element, Element] = {
    Element.WOOD: Element.FIRE,
    Element.FIRE: Element.EARTH,
    Element.EARTH: Element.METAL,
    Element.METAL: Element.WATER,
    Element.WATER: Element.WOOD,
}

# Destructive cycle: Wood → Earth, Fire → Metal, Earth → Water, Metal → Wood, Water → Fire
DESTRUCTIVE: dict[Element, Element] = {
    Element.WOOD: Element.EARTH,
    Element.FIRE: Element.METAL,
    Element.EARTH: Element.WATER,
    Element.METAL: Element.WOOD,
    Element.WATER: Element.FIRE,
}

ELEMENT_MEANINGS: dict[Element, str] = {
    Element.WOOD: "Growth, expansion, creativity, planning",
    Element.FIRE: "Passion, inspiration, rapid action, illumination",
    Element.EARTH: "Stability, grounding, nourishment, patience",
    Element.METAL: "Structure, precision, discernment, cutting",
    Element.WATER: "Wisdom, depth, flow, introspection, storage",
}


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
    """Manages the five-element cognitive balance system."""

    def __init__(self) -> None:
        self.balance = WuXingBalance()

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
            "balance": {
                e.value: getattr(self.balance, e.value) for e in Element
            },
            "is_balanced": self.balance.is_balanced(),
            "dominant": self.balance.dominant().value,
        }


_wu_xing: WuXingSystem | None = None


def get_wu_xing() -> WuXingSystem:
    global _wu_xing
    if _wu_xing is None:
        _wu_xing = WuXingSystem()
    return _wu_xing
