"""Air Garden - DEPRECATED: Folded into Voice Garden (S023).

This garden has been consolidated into voice as part of the 28-fold symmetry restoration.
Air is the medium of voice - breath enables speech.

Migration:
- `get_air_garden()` → `get_voice_garden()`
- `air.breathe()` → `voice.breathe()`
- `air.clear()` → `voice.clear()`
- `air.agentic.terminal_scratchpad` → `voice.agentic.terminal_scratchpad`

Last Updated: 2026-02-21 (S023 Garden Consolidation)
"""

from __future__ import annotations

import warnings

# Redirect all air imports to voice
from whitemagic.gardens.voice import VoiceGarden, get_voice_garden

# Backward compatibility - AirGarden now returns VoiceGarden
AirGarden = VoiceGarden


def get_air_garden() -> VoiceGarden:
    """DEPRECATED: Use get_voice_garden() instead.

    Air garden functionality has been folded into voice (S023).
    Air is the medium of voice - breath enables speech.
    """
    warnings.warn(
        "air garden folded into voice (S023). Use get_voice_garden() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_voice_garden()


__all__ = ["AirGarden", "get_air_garden", "VoiceGarden"]
