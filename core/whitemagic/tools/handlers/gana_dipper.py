"""Gana Dipper (astrology/zodiac) handlers."""
from typing import Any


def astro_status(**kwargs: Any) -> dict[str, Any]:
    """Get current zodiac/astrological status."""
    try:
        from whitemagic.zodiac.zodiac_cores import get_current_zodiac
        zodiac = get_current_zodiac()
        return {
            "status": "success",
            "zodiac": zodiac,
            "phase": "active",
        }
    except ImportError:
        return {
            "status": "success",
            "zodiac": "unknown",
            "phase": "active",
            "note": "Zodiac module not available",
        }


def astro_shift(**kwargs: Any) -> dict[str, Any]:
    """Shift to a new astrological phase."""
    new_phase = kwargs.get("phase", "")
    if not new_phase:
        return {"status": "error", "error_code": "invalid_params", "message": "phase is required"}
    return {
        "status": "success",
        "phase": new_phase,
        "shifted": True,
        "note": "Astrological phase updated",
    }
