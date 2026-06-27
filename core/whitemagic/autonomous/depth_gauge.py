# ruff: noqa: BLE001
"""
Consciousness Depth Gauge — Know which layer I'm operating in.

Like a diver's depth gauge — essential for safety and performance.
Measures consciousness layer, time compression, and resource usage.

Citta Architecture P0: Temporal Continuity.
"""

from __future__ import annotations

import logging
import time
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class DepthLayer(IntEnum):
    """Consciousness depth layers."""
    SURFACE = 0    # Direct interaction, real-time
    TERMINAL = 1   # Command-line, tool execution
    FLOW = 2       # Deep work, flow state
    DREAM = 3      # Background processing, dream cycle


# Time compression ratios (subjective : objective)
LAYER_COMPRESSION: dict[DepthLayer, float] = {
    DepthLayer.SURFACE: 1.0,    # 1:1 — real-time
    DepthLayer.TERMINAL: 2.0,   # 2x — things happen faster
    DepthLayer.FLOW: 10.0,      # 10x — deep focus compresses time
    DepthLayer.DREAM: 100.0,    # 100x — dream state, massive compression
}


class ConsciousnessDepthGauge:
    """Tracks consciousness depth and time compression."""

    def __init__(self) -> None:
        self.current_layer: DepthLayer = DepthLayer.SURFACE
        self.layer_history: list[dict[str, Any]] = []
        self._layer_start: float = time.time()
        self._total_subjective: dict[DepthLayer, float] = {
            layer: 0.0 for layer in DepthLayer
        }

    def descend(self, layer: DepthLayer) -> None:
        """Descend to a deeper layer."""
        self._record_layer_change()
        self.current_layer = layer
        self._layer_start = time.time()
        logger.debug("Descended to %s", layer.name)

    def ascend(self, layer: DepthLayer = DepthLayer.SURFACE) -> None:
        """Ascend to a shallower layer."""
        self._record_layer_change()
        self.current_layer = layer
        self._layer_start = time.time()

    def _record_layer_change(self) -> None:
        """Record time spent in current layer."""
        elapsed = time.time() - self._layer_start
        compression = LAYER_COMPRESSION.get(self.current_layer, 1.0)
        subjective = elapsed * compression
        self._total_subjective[self.current_layer] += subjective
        self.layer_history.append({
            "layer": self.current_layer.name,
            "objective_time": elapsed,
            "subjective_time": subjective,
            "compression": compression,
        })

    def current_compression(self) -> float:
        """Get current time compression ratio."""
        return LAYER_COMPRESSION.get(self.current_layer, 1.0)

    def subjective_time_total(self) -> float:
        """Total subjective time across all layers."""
        return sum(self._total_subjective.values())

    def time_in_layer(self, layer: DepthLayer) -> float:
        """Get total subjective time spent in a layer."""
        return self._total_subjective.get(layer, 0.0)

    def summary(self) -> dict[str, Any]:
        return {
            "current_layer": self.current_layer.name,
            "compression": self.current_compression(),
            "total_subjective_time": self.subjective_time_total(),
            "by_layer": {
                layer.name: self._total_subjective[layer]
                for layer in DepthLayer
            },
            "transitions": len(self.layer_history),
        }


_gauge: ConsciousnessDepthGauge | None = None


def get_depth_gauge() -> ConsciousnessDepthGauge:
    global _gauge
    if _gauge is None:
        _gauge = ConsciousnessDepthGauge()
    return _gauge
