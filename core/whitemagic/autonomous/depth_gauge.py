# ruff: noqa: BLE001
"""
Consciousness Depth Gauge — Shim re-exporting canonical implementation.

Canonical implementation: whitemagic.core.consciousness.depth_gauge
"""

from __future__ import annotations

from whitemagic.core.consciousness.depth_gauge import (
    ConsciousnessDepthGauge,
    DepthReading,
    get_depth_gauge,
)
from whitemagic.core.consciousness.depth_gauge import (
    ConsciousnessLayer as DepthLayer,
)

__all__ = [
    "ConsciousnessDepthGauge",
    "DepthLayer",
    "DepthReading",
    "get_depth_gauge",
]
