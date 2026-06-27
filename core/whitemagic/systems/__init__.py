# ruff: noqa: BLE001
"""Systems — System monitoring and cross-system automation."""

from __future__ import annotations

from .monitoring.system_monitor import SystemMonitor, get_system_monitor

__all__ = ["SystemMonitor", "get_system_monitor"]
