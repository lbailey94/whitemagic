"""Fusion Event Bridge — Event emission utility for fusions.

Emit fusion events to the Gan Ying bus.
Extracted from fusions.py for better separation of concerns.
"""
# ruff: noqa: BLE001

import logging
from typing import Any

logger = logging.getLogger(__name__)


def emit_fusion_event(event_name: str, data: dict[str, Any]) -> None:
    """Emit a fusion event to the Gan Ying bus."""
    try:
        from whitemagic.core.resonance.gan_ying_enhanced import (
            EventType,
            ResonanceEvent,
            get_bus,
        )

        bus = get_bus()
        event = ResonanceEvent(
            source="fusion",
            event_type=EventType.NOVEL_PATTERN,
            data={"fusion_event": event_name, **data},
        )
        bus.emit(event)
        logger.debug(f"Fusion event emitted: {event_name}")
    except Exception as e:
        logger.warning(f"Failed to emit fusion event {event_name}: {e}")
