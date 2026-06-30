# ruff: noqa: BLE001
"""
Consciousness Depth Gauge — Shim re-exporting canonical implementation.

Canonical implementation: whitemagic.core.consciousness.depth_gauge
"""

from __future__ import annotations

from whitemagic.core.consciousness.depth_gauge import (
    ConsciousnessDepthGauge,
    ConsciousnessLayer as DepthLayer,
    DepthReading,
    get_depth_gauge,
)

__all__ = [
    "ConsciousnessDepthGauge",
    "DepthLayer",
    "DepthReading",
    "get_depth_gauge",
]
