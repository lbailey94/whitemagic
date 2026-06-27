# ruff: noqa: BLE001
"""
WhiteMagic Performance Dashboard.

Visualizes performance trends and tracks improvements over time.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class PerformanceDashboard:
    """Tracks and visualizes performance trends."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "performance"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.data_dir / "metrics.jsonl"
        self._metrics: list[dict[str, Any]] = []

    def record_metric(self, name: str, value: float, unit: str = "ms") -> dict[str, Any]:
        """Record a performance metric."""
        entry = {
            "name": name,
            "value": value,
            "unit": unit,
            "timestamp": time.time(),
        }
        self._metrics.append(entry)
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def get_trend(self, metric_name: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get trend data for a specific metric."""
        return [m for m in self._metrics if m["name"] == metric_name][-limit:]

    def summary(self) -> dict[str, Any]:
        """Get dashboard summary."""
        metric_names = set(m["name"] for m in self._metrics)
        return {
            "total_metrics": len(self._metrics),
            "unique_metrics": len(metric_names),
            "metric_names": list(metric_names),
        }

    def latest(self) -> dict[str, Any]:
        """Get latest values for all metrics."""
        latest: dict[str, Any] = {}
        for m in reversed(self._metrics):
            if m["name"] not in latest:
                latest[m["name"]] = m
        return latest


_dashboard: PerformanceDashboard | None = None


def get_dashboard() -> PerformanceDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = PerformanceDashboard()
    return _dashboard
