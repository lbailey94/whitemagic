"""Resonance Subsystem (Consolidated v3.2).

This package re-exports symbols from the consolidated _consolidated.py module.
The resonance/ sub-package was consolidated into a single file in Milestone 4.3.
"""

from ._consolidated import (
    EventType,
    GanYingBus,
    ResonanceEvent,
    emit_event,
    get_bus,
    get_event_bus,
)

__all__ = [
    "EventType",
    "GanYingBus",
    "ResonanceEvent",
    "emit_event",
    "get_bus",
    "get_event_bus",
]
