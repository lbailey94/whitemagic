"""Emergence — Self-modifying and creative features."""

from __future__ import annotations

from .detector import EmergenceDetector, EmergentBehavior, get_detector
from .dream_state import DreamState, get_dream_state
from .pattern_discovery import (
    DiscoveryReport,
    PatternDiscovery,
    get_discovery,
    run_full_discovery,
)

__all__ = [
    "EmergenceDetector",
    "EmergentBehavior",
    "get_detector",
    "DreamState",
    "get_dream_state",
    "PatternDiscovery",
    "DiscoveryReport",
    "get_discovery",
    "run_full_discovery",
]
