# ruff: noqa: BLE001
"""
Homeostasis Metrics — Measure system balance points.

Tracks key metrics for maintaining system equilibrium:
- Memory distribution (short-term vs long-term)
- Storage usage and efficiency
- Test pass rate
- Tool dispatch latency
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class HomeostasisMetrics:
    """Tracks metrics for system homeostasis."""

    def __init__(self) -> None:
        self.metrics: dict[str, list[tuple[float, float]]] = {}
        self.set_points: dict[str, float] = {
            "memory_balance": 0.5,
            "storage_efficiency": 0.8,
            "test_pass_rate": 1.0,
            "dispatch_latency_ms": 50.0,
        }
        self.tolerances: dict[str, float] = {
            "memory_balance": 0.2,
            "storage_efficiency": 0.1,
            "test_pass_rate": 0.05,
            "dispatch_latency_ms": 20.0,
        }

    def record(self, metric: str, value: float) -> None:
        """Record a metric value."""
        self.metrics.setdefault(metric, []).append((time.time(), value))

    def get_current(self, metric: str) -> float | None:
        """Get the most recent value for a metric."""
        values = self.metrics.get(metric, [])
        return values[-1][1] if values else None

    def is_in_range(self, metric: str) -> bool:
        """Check if a metric is within its tolerance range."""
        current = self.get_current(metric)
        if current is None:
            return True
        set_point = self.set_points.get(metric, 0)
        tolerance = self.tolerances.get(metric, 0)
        return abs(current - set_point) <= tolerance

    def all_in_range(self) -> bool:
        """Check if all metrics are in range."""
        return all(self.is_in_range(m) for m in self.set_points)

    def deviations(self) -> dict[str, float]:
        """Get deviation from set point for each metric."""
        result: dict[str, float] = {}
        for metric in self.set_points:
            current = self.get_current(metric)
            if current is not None:
                result[metric] = current - self.set_points[metric]
        return result

    def summary(self) -> dict[str, Any]:
        return {
            "set_points": self.set_points,
            "all_in_range": self.all_in_range(),
            "deviations": self.deviations(),
            "tracked_metrics": list(self.metrics.keys()),
        }


_metrics: HomeostasisMetrics | None = None


def get_metrics() -> HomeostasisMetrics:
    global _metrics
    if _metrics is None:
        _metrics = HomeostasisMetrics()
    return _metrics
