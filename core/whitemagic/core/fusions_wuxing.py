"""Wu Xing Fusion — Elemental phase → Gana quadrant amplification.

Check if the current Wu Xing elemental phase amplifies the given Gana's quadrant.
Extracted from fusions.py for better separation of concerns.
"""
# ruff: noqa: BLE001

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Wu Xing to quadrant mapping
_ELEMENT_TO_QUADRANT = {
    "wood": "Northeast",
    "fire": "Southeast",
    "earth": "Southwest",
    "metal": "Northwest",
    "water": "Center",
}

# Quadrant to element mapping
_QUADRANT_TO_ELEMENT = {
    "Northeast": "wood",
    "Southeast": "fire",
    "Southwest": "earth",
    "Northwest": "metal",
    "Center": "water",
}

# Legacy compass direction names from GANA_META -> Chinese astronomical quadrants
_COMPASS_TO_ASTRONOMICAL = {
    "East": "Northeast",   # Wood
    "South": "Southeast",  # Fire
    "West": "Northwest",   # Metal
    "North": "Center",     # Water
}


def get_wuxing_quadrant_boost(gana_name: str) -> dict[str, Any]:
    """Check if the current Wu Xing elemental phase amplifies the
    given Gana's quadrant.

    When the dominant element matches a Gana's quadrant, that Gana
    gets a "boost" — its operations should be prioritized and its
    resonance amplified.

    Args:
        gana_name: The Gana being invoked (e.g. "gana_ghost")

    Returns:
        DiMap legacy compass direction names to astronomical quadrant names
        quadrant = _COMPASS_TO_ASTRONOMICAL.get(quadrant, quadrant)

        # ct with boost status, dominant element, and boost factor.
    """
    try:
        from whitemagic.tools.prat_resonance import _get_meta

        meta = _get_meta(gana_name)
        quadrant = meta.get("quadrant", "Unknown")

        # Get current Wu Xing state
        dominant_element, element_energy = _get_dominant_element()

        # Check if this quadrant matches the dominant element
        matching_quadrant = _ELEMENT_TO_QUADRANT.get(dominant_element)

        boosted = (matching_quadrant == quadrant)

        # Boost factor: 1.0 (no boost) to 1.5 (full alignment)
        if boosted and element_energy > 0:
            boost_factor = 1.0 + (element_energy * 0.5)  # max 1.5×
        else:
            boost_factor = 1.0

        # Check for overcoming cycle penalty (element that controls this quadrant)
        penalized = False
        penalty_element = None
        if quadrant in _QUADRANT_TO_ELEMENT:
            q_element = _QUADRANT_TO_ELEMENT[quadrant]
            # Overcoming cycle: Wood→Earth→Water→Fire→Metal→Wood
            _OVERCOMES = {
                "wood": "earth", "earth": "water", "water": "fire",
                "fire": "metal", "metal": "wood",
            }
            if _OVERCOMES.get(dominant_element) == q_element:
                penalized = True
                penalty_element = dominant_element
                boost_factor = max(0.7, boost_factor - 0.3)

        return {
            "gana": gana_name,
            "quadrant": quadrant,
            "dominant_element": dominant_element,
            "element_energy": round(element_energy, 3),
            "boosted": boosted,
            "penalized": penalized,
            "penalty_element": penalty_element,
            "boost_factor": round(boost_factor, 3),
        }

    except Exception as e:
        return {
            "gana": gana_name,
            "boosted": False,
            "penalized": False,
            "boost_factor": 1.0,
            "error": str(e),
        }


def _get_dominant_element() -> tuple:
    """Get the dominant Wu Xing element and its energy. Safe fallback."""
    try:
        from whitemagic.wu_xing import WuXingEngine
        engine = WuXingEngine()
        # Find highest energy element
        best = max(engine.elements.values(), key=lambda s: s.energy)
        return (best.element.value, best.energy)
    except Exception as e:
        logger.warning(f"Wu Xing engine unavailable: {e}")
        return ("wood", 0.5)  # Safe default
