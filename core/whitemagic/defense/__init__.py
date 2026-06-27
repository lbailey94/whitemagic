# ruff: noqa: BLE001
"""
WhiteMagic Defense System — Autoimmune Architecture.

The body's immune system, applied to code:
- Recognize threats (anti-patterns)
- Remember solutions (pattern library)
- Auto-heal when safe (high confidence fixes)
- Learn from failures (adaptive immunity)
"""

from __future__ import annotations

from .autoimmune import AutoimmuneDefense, get_autoimmune
from .granular_awareness import GranularAwareness, get_granular_awareness
from .homeostatic_monitor import HomeostaticMonitor, get_monitor
from .multi_agent import MultiAgentCoordinator, get_coordinator

__all__ = [
    "HomeostaticMonitor",
    "get_monitor",
    "GranularAwareness",
    "get_granular_awareness",
    "MultiAgentCoordinator",
    "get_coordinator",
    "AutoimmuneDefense",
    "get_autoimmune",
]
