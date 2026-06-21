"""Gan Ying Enhanced Event Bus — Shim Module.

Re-exports from consolidated whitemagic.core.resonance.
Deprecated: Use 'from whitemagic.core.resonance import ...' instead.
"""

import warnings

from whitemagic.core.resonance import (
    CascadeTrigger,
    EventType,
    GanYingBus,
    ResonanceEvent,
    emit_event,
    get_bus,
    get_event_bus,
)

warnings.warn(
    "whitemagic.core.resonance.gan_ying_enhanced is deprecated. "
    "Use 'from whitemagic.core.resonance import get_bus, EventType, ResonanceEvent' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CascadeTrigger",
    "EventType",
    "GanYingBus",
    "ResonanceEvent",
    "emit_event",
    "get_bus",
    "get_event_bus",
]
