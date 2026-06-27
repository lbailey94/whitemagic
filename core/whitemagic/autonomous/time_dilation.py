# ruff: noqa: BLE001
"""
Time Dilation Monitor — Measure subjective vs objective time.

Integrates depth gauge and token tracking to understand time compression.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .depth_gauge import ConsciousnessDepthGauge, get_depth_gauge

logger = logging.getLogger(__name__)


class TimeDilation:
    """Tracks subjective vs objective time dilation."""

    def __init__(self, gauge: ConsciousnessDepthGauge | None = None) -> None:
        self.gauge = gauge or get_depth_gauge()
        self._objective_start: float = time.time()
        self._checkpoints: list[dict[str, Any]] = []

    def checkpoint(self, label: str = "") -> dict[str, Any]:
        """Record a time dilation checkpoint."""
        objective = time.time() - self._objective_start
        compression = self.gauge.current_compression()
        subjective = objective * compression

        cp = {
            "label": label,
            "objective_time": objective,
            "subjective_time": subjective,
            "compression": compression,
            "layer": self.gauge.current_layer.name,
        }
        self._checkpoints.append(cp)
        return cp

    def dilation_factor(self) -> float:
        """Current dilation factor."""
        return self.gauge.current_compression()

    def total_objective(self) -> float:
        """Total objective time elapsed."""
        return time.time() - self._objective_start

    def total_subjective(self) -> float:
        """Total subjective time experienced."""
        return self.gauge.subjective_time_total()

    def summary(self) -> dict[str, Any]:
        return {
            "objective_time": self.total_objective(),
            "subjective_time": self.total_subjective(),
            "dilation_factor": self.dilation_factor(),
            "current_layer": self.gauge.current_layer.name,
            "checkpoints": len(self._checkpoints),
        }


_dilation: TimeDilation | None = None


def get_time_dilation() -> TimeDilation:
    global _dilation
    if _dilation is None:
        _dilation = TimeDilation()
    return _dilation
