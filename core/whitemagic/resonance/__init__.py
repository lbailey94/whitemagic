# ruff: noqa: BLE001
"""
Resonance — Enhanced GanYingBus and cascade protocols.

Wraps the v23 GanYingBus with additional event types and
intelligent cascade patterns for self-organizing behavior.
"""

from __future__ import annotations

from .cascade_protocols import CascadeProtocols, init_all_cascades
from .gan_ying_enhanced import EnhancedGanYingBus, get_enhanced_bus

__all__ = [
    "EnhancedGanYingBus",
    "get_enhanced_bus",
    "CascadeProtocols",
    "init_all_cascades",
]
