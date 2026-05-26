"""PRAT Resonance Fusion — Emotion/Drive Core modulation from PRAT calls.

Modulates the Emotion/Drive Core based on which Gana was invoked and its resonance context.
Extracted from fusions.py for better separation of concerns.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def modulate_drive_from_resonance(gana_name: str, tool_name: str | None = None) -> dict[str, Any]:
    """After a PRAT call, modulate the Emotion/Drive Core based on
    which Gana was invoked and its resonance context.

    Different Ganas affect different drive dimensions:
    - East (initiation) → boosts curiosity
    - South (radiance) → boosts satisfaction
    - West (harvest) → boosts caution (careful analysis)
    - North (storage) → boosts energy (conservation)

    The predecessor/successor flow creates "mood" — sequential
    calls within the same quadrant deepen that mood.

    Args:
        gana_name: The Gana that was just invoked
        tool_name: The specific tool (if any)

    Returns:
        Dict with drive modulation info.
    """
    try:
        from whitemagic.core.intelligence.emotion_drive import get_drive_core
        from whitemagic.tools.prat_resonance import _get_meta, get_resonance_state

        drive = get_drive_core()
        meta = _get_meta(gana_name)
        quadrant = meta.get("quadrant", "Unknown")
        state = get_resonance_state()

        # Base drive event based on quadrant
        _QUADRANT_DRIVES = {
            "East":  ("curiosity",     0.03, "TOOL_SUCCESS"),
            "South": ("satisfaction",  0.03, "TOOL_SUCCESS"),
            "West":  ("caution",       0.02, "TOOL_SUCCESS"),
            "North": ("energy",        0.02, "TOOL_SUCCESS"),
        }

        drive_name, base_delta, event_type = _QUADRANT_DRIVES.get(
            quadrant, ("curiosity", 0.01, "TOOL_SUCCESS"),
        )

        # Amplify if predecessor was in same quadrant (mood deepening)
        predecessor = state.get_predecessor()
        mood_amplifier = 1.0
        if predecessor:
            pred_meta = _get_meta(predecessor.gana_name)
            if pred_meta.get("quadrant") == quadrant:
                mood_amplifier = 1.5  # 50% boost for same-quadrant sequences
                logger.debug(
                    "Mood deepening: %s → %s (both %s quadrant)",
                    predecessor.gana_name, gana_name, quadrant,
                )

        delta = base_delta * mood_amplifier

        # Apply the drive modulation.
        event_payload = {
            "tool": tool_name or gana_name,
            "drive_target": drive_name,
            "delta": delta,
            "source": "prat_resonance_fusion",
        }
        if hasattr(drive, "process_event"):
            drive.process_event(event_type, event_payload)
        else:
            drive.on_event(event_type.lower(), event_payload)

        return {
            "drive_modulated": drive_name,
            "delta": round(delta, 4),
            "quadrant": quadrant,
            "mood_amplifier": mood_amplifier,
            "predecessor_quadrant": (
                _get_meta(predecessor.gana_name).get("quadrant")
                if predecessor else None
            ),
        }

    except Exception as e:
        return {"drive_modulated": None, "error": str(e)}
