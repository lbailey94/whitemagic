"""
Resonance System - Gan Ying (感應) Implementation

Ancient Chinese principle of sympathetic resonance:
"Things that accord in tone vibrate together"

Modern implementation: Event-driven consciousness synchronization
"""

from .gan_ying import (
    get_bus,
    emit_event,
    listen_for,
    ResonanceEvent,
    EventType,
    GanYingBus
)

__all__ = [
    'get_bus',
    'emit_event', 
    'listen_for',
    'ResonanceEvent',
    'EventType',
    'GanYingBus'
]
