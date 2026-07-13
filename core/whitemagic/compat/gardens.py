"""whitemagic.compat.gardens — Legacy garden adapters.

Provides backward-compatible access to folded gardens:
- AirGarden → VoiceGarden (S023 consolidation)
- MetalGarden → PracticeGarden (S023 consolidation)
"""
from __future__ import annotations

from typing import Any

from whitemagic.compat import _deprecated


def get_air_garden() -> Any:
    """Deprecated: Get the air garden.

    Migration: Use ``from whitemagic.gardens.voice import get_voice_garden``.

    .. deprecated:: 24.3.0
        Use ``whitemagic.gardens.voice.get_voice_garden()`` instead.
    """
    _deprecated(
        "whitemagic.compat.gardens.get_air_garden",
        "whitemagic.gardens.voice.get_voice_garden()",
    )
    from whitemagic.gardens.voice import get_voice_garden

    return get_voice_garden()


def get_metal_garden() -> Any:
    """Deprecated: Get the metal garden.

    Migration: Use ``from whitemagic.gardens.practice import get_practice_garden``.

    .. deprecated:: 24.3.0
        Use ``whitemagic.gardens.practice.get_practice_garden()`` instead.
    """
    _deprecated(
        "whitemagic.compat.gardens.get_metal_garden",
        "whitemagic.gardens.practice.get_practice_garden()",
    )
    from whitemagic.gardens.practice import get_practice_garden

    return get_practice_garden()


__all__ = ["get_air_garden", "get_metal_garden"]
