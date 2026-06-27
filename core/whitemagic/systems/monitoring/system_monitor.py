# ruff: noqa: BLE001
"""
System Monitoring — Listens for system events and tracks health.

Monitors the overall system state by collecting metrics from
all registered subsystems and emitting health reports.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitors system health by collecting metrics from subsystems."""

    def __init__(self) -> None:
        self.metrics: dict[str, dict[str, Any]] = {}
        self.health_history: list[dict[str, Any]] = []
        self.subsystems: dict[str, Any] = {}

    def register_subsystem(self, name: str, subsystem: Any) -> None:
        """Register a subsystem for monitoring."""
        self.subsystems[name] = subsystem

    def collect_metrics(self) -> dict[str, Any]:
        """Collect metrics from all registered subsystems."""
        all_metrics: dict[str, Any] = {}
        for name, subsystem in self.subsystems.items():
            try:
                if hasattr(subsystem, "summary"):
                    all_metrics[name] = subsystem.summary()
                elif hasattr(subsystem, "status"):
                    all_metrics[name] = subsystem.status()
                else:
                    all_metrics[name] = {"status": "no metrics available"}
            except Exception as e:
                all_metrics[name] = {"error": str(e)}

        self.metrics = all_metrics
        return all_metrics

    def health_report(self) -> dict[str, Any]:
        """Generate a comprehensive health report."""
        metrics = self.collect_metrics()
        healthy_count = sum(
            1 for m in metrics.values()
            if isinstance(m, dict) and "error" not in m
        )
        total = len(metrics)

        if total == 0:
            status = "unknown"
        elif healthy_count == total:
            status = "healthy"
        elif healthy_count > total * 0.7:
            status = "good"
        elif healthy_count > total * 0.5:
            status = "fair"
        else:
            status = "critical"

        report = {
            "status": status,
            "healthy_subsystems": healthy_count,
            "total_subsystems": total,
            "metrics": metrics,
            "timestamp": time.time(),
        }
        self.health_history.append(report)
        return report

    def summary(self) -> dict[str, Any]:
        return {
            "registered_subsystems": len(self.subsystems),
            "health_checks": len(self.health_history),
            "current_status": self.health_history[-1]["status"] if self.health_history else "unknown",
        }


_monitor: SystemMonitor | None = None


def get_system_monitor() -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor
