"""Heart Engine (Xin) — Backward-compat shim.

Fused into NurturingEngine (slot 4, Girl 女) as of v23.1.
All emotional state synthesis now lives in whitemagic.core.nurturing.nurturing_engine.

This module re-exports the fused classes and functions for backward
compatibility with existing imports.
"""

from __future__ import annotations

from whitemagic.core.nurturing.nurturing_engine import (
    EmotionalState,
    NurturingEngine as HeartEngine,
    ResonancePulse,
    get_heart,
)

__all__ = [
    "EmotionalState",
    "HeartEngine",
    "ResonancePulse",
    "get_heart",
]
