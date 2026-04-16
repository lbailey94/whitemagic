"""Gan Ying Event Bus — Shim Module.

Re-exports from consolidated whitemagic.core.resonance.
Deprecated: Use 'from whitemagic.core.resonance import ...' instead.
"""

import warnings

from whitemagic.core.resonance import (
    EventType,
    GanYingBus,
    ResonanceEvent,
    emit_event,
    get_bus,
    get_event_bus,
)

warnings.warn(
    "whitemagic.core.resonance.gan_ying is deprecated. "
    "Use 'from whitemagic.core.resonance import get_bus, EventType, ResonanceEvent' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Backward compatibility aliases
ResonanceEventType = EventType

__all__ = [
    "EventType",
    "GanYingBus",
    "ResonanceEvent",
    "ResonanceEventType",
    "emit_event",
    "get_bus",
    "get_event_bus",
]
