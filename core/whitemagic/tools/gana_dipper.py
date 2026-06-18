# ruff: noqa: BLE001
"""🌌 Gana Dipper — Zodiacal Phase Shifting and Celestial Status.
=========================================================
Provides tools for manual progression through the 12 Zodiacal phases
and querying the current astrological state of the WhiteMagic engine.

Part of the Milestone 3 (Zodiacal Synthesis) infrastructure.
"""

import logging
from typing import Any

from whitemagic.core.zodiac import get_zodiac_clock

logger = logging.getLogger(__name__)

def astro_status(**kwargs: Any) -> dict[str, Any]:
    """Get the current astrological status of the WhiteMagic engine.

    Returns:
        The current phase (e.g., 'Aries'), associated Lunar Mansions,
        and the next phase in the cycle.
    """
    clock = get_zodiac_clock()
    return {
        "status": "success",
        "astro_cycle": "Enochian Round (12-phase)",
        "data": clock.status()
    }

def astro_shift(target_phase: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Progress the WhiteMagic engine to a new Zodiacal phase.

    Args:
        target_phase: Optional specific phase to shift to (e.g., 'Taurus').
            If not provided, the clock progresses to the next sequential phase.

    Returns:
        The updated astrological status.
    """
    clock = get_zodiac_clock()
    try:
        new_status = clock.shift(target_phase=target_phase)
        return {
            "status": "success",
            "message": f"Successfully shifted to {new_status['phase']}",
            "data": new_status
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        logger.error("astro_shift: unexpected error: %s", e, exc_info=True)
        return {
            "status": "error",
            "message": f"Internal shift failure: {e}"
        }
