"""Metal Garden - DEPRECATED: Folded into Practice Garden (S023).

This garden has been consolidated into practice as part of the 28-fold symmetry restoration.
Metal tools enable disciplined practice and mastery.

Migration:
- `get_metal_garden()` → `get_practice_garden()`
- `metal.consult_zodiac()` → `practice.consult_zodiac()`
- `metal.zodiac.*` → `practice.zodiac.*`

Last Updated: 2026-02-21 (S023 Garden Consolidation)
"""

from __future__ import annotations

import warnings

# Redirect all metal imports to practice
from whitemagic.gardens.practice import PracticeGarden, get_practice_garden
from whitemagic.gardens.practice.zodiac import (  # noqa: F401
    ZodiacCore,
    ZodiacCouncil,
    consult_council,
    consult_core,
    get_zodiac_council,
)

# Backward compatibility - MetalGarden now returns PracticeGarden
MetalGarden = PracticeGarden


def get_metal_garden() -> PracticeGarden:
    """DEPRECATED: Use get_practice_garden() instead.

    Metal garden functionality has been folded into practice (S023).
    Metal tools enable disciplined practice.
    """
    warnings.warn(
        "metal garden folded into practice (S023). Use get_practice_garden() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_practice_garden()


__all__ = [
    "MetalGarden",
    "get_metal_garden",
    "PracticeGarden",
    "ZodiacCore",
    "ZodiacCouncil",
    "consult_council",
    "consult_core",
    "get_zodiac_council",
]
