"""Resonance Subsystem (Consolidated v3.3).

This package re-exports symbols from the consolidated _consolidated.py module
and provides access to the Julia-inspired resonance engine.
"""

from ._consolidated import (
    CascadeTrigger,
    EventType,
    GanYingBus,
    ResonanceEvent,
    emit_event,
    get_bus,
    get_event_bus,
)
from .julia_resonance import (
    CausalVerificationResult,
    NeighborResult,
    ResonanceEngine,
    ResonanceResult,
    get_resonance_engine,
)

__all__ = [
    "CascadeTrigger",
    "EventType",
    "GanYingBus",
    "ResonanceEvent",
    "emit_event",
    "get_bus",
    "get_event_bus",
    "ResonanceEngine",
    "ResonanceResult",
    "CausalVerificationResult",
    "NeighborResult",
    "get_resonance_engine",
]
