"""Prometheus Metrics Exporter for WhiteMagic.
============================================
Exposes WhiteMagic metrics via Prometheus protocol for scraping.
Runs an HTTP server on port 9090 (configurable via WM_PROMETHEUS_PORT).

Metrics exposed:
  - whitemagic_tool_calls_total{tool} - Total tool invocations
  - whitemagic_tool_errors_total{tool} - Total tool errors
  - whitemagic_tool_duration_seconds{tool} - Tool execution duration histogram
  - whitemagic_memory_count{type} - Memory count by type
  - whitemagic_cold_start_seconds - Cold start duration gauge
  - whitemagic_db_connections_active - Active DB connections
  - whitemagic_circuit_breaker_state{tool} - Circuit breaker state (0=closed, 1=open, 2=half_open)

Usage:
    from whitemagic.core.monitoring.prometheus_export import start_prometheus_server
    start_prometheus_server()  # Starts HTTP server on port 9090

    # Or configure via environment:
    # WM_PROMETHEUS_PORT=9090 WM_PROMETHEUS_ENABLED=1
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Try to import prometheus_client
HAS_PROMETHEUS = False
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    pass


class PrometheusMetrics:
    """Prometheus metrics collector for WhiteMagic."""

    def __init__(self) -> None:
        self._enabled = os.environ.get("WM_PROMETHEUS_ENABLED", "0") == "1"
        self._port = int(os.environ.get("WM_PROMETHEUS_PORT", "9090"))
        self._lock = threading.Lock()
        self._server_started = False

        # Metrics (initialized if prometheus available)
        self._tool_calls: Any = None
        self._tool_errors: Any = None
        self._tool_duration: Any = None
        self._memory_count: Any = None
        self._cold_start: Any = None
        self._db_connections: Any = None
        self._circuit_breaker_state: Any = None

        if self._enabled and HAS_PROMETHEUS:
            self._init_metrics()

    def _init_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        try:
            # Tool invocation counter
            self._tool_calls = Counter(
                "whitemagic_tool_calls_total",
                "Total tool invocations",
                ["tool"]
            )

            # Tool error counter
            self._tool_errors = Counter(
                "whitemagic_tool_errors_total",
                "Total tool errors",
                ["tool"]
            )

            # Tool duration histogram
            self._tool_duration = Histogram(
                "whitemagic_tool_duration_seconds",
                "Tool execution duration",
                ["tool"],
                buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
            )

            # Memory count gauge
            self._memory_count = Gauge(
                "whitemagic_memory_count",
                "Memory count by type",
                ["type"]
            )

            # Cold start gauge
            self._cold_start = Gauge(
                "whitemagic_cold_start_seconds",
                "Cold start duration"
            )

            # DB connections gauge
            self._db_connections = Gauge(
                "whitemagic_db_connections_active",
                "Active database connections"
            )

            # Circuit breaker state gauge
            self._circuit_breaker_state = Gauge(
                "whitemagic_circuit_breaker_state",
                "Circuit breaker state (0=closed, 1=open, 2=half_open)",
                ["tool"]
            )

            logger.info("Prometheus metrics initialized")
        except Exception as e:
            logger.warning("Prometheus metrics init failed: %s", e)
            self._enabled = False

    def start_server(self) -> bool:
        """Start Prometheus HTTP server."""
        if not self._enabled or not HAS_PROMETHEUS:
            return False

        if self._server_started:
            return True

        try:
            start_http_server(self._port)
            self._server_started = True
            logger.info("Prometheus server started on port %d", self._port)
            return True
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Failed to start Prometheus server: %s", e)
            return False

    def record_tool_call(self, tool_name: str, duration_seconds: float, status: str) -> None:
        """Record a tool invocation."""
        if not self._enabled or not HAS_PROMETHEUS:
            return

        with self._lock:
            try:
                self._tool_calls.labels(tool=tool_name).inc()
                if status == "error":
                    self._tool_errors.labels(tool=tool_name).inc()
                self._tool_duration.labels(tool=tool_name).observe(duration_seconds)
            except Exception as e:
                logger.debug(f"Prometheus metric record failed for {tool_name}: {e}")

    def set_memory_count(self, memory_type: str, count: int) -> None:
        """Set memory count gauge."""
        if not self._enabled or not HAS_PROMETHEUS:
            return

        try:
            self._memory_count.labels(type=memory_type).set(count)
        except Exception as e:
            logger.debug(f"Prometheus memory_count set failed: {e}")

    def set_cold_start(self, duration_seconds: float) -> None:
        """Set cold start gauge."""
        if not self._enabled or not HAS_PROMETHEUS:
            return

        try:
            self._cold_start.set(duration_seconds)
        except Exception as e:
            logger.debug(f"Prometheus cold_start set failed: {e}")

    def set_db_connections(self, count: int) -> None:
        """Set active DB connections gauge."""
        if not self._enabled or not HAS_PROMETHEUS:
            return

        try:
            self._db_connections.set(count)
        except Exception as e:
            logger.debug(f"Prometheus db_connections set failed: {e}")

    def set_circuit_breaker(self, tool_name: str, state: str) -> None:
        """Set circuit breaker state (closed=0, open=1, half_open=2)."""
        if not self._enabled or not HAS_PROMETHEUS:
            return

        state_map = {"closed": 0, "open": 1, "half_open": 2}
        try:
            self._circuit_breaker_state.labels(tool=tool_name).set(state_map.get(state, 0))
        except Exception as e:
            logger.debug(f"Prometheus circuit_breaker set failed: {e}")

    def status(self) -> dict[str, Any]:
        """Get Prometheus exporter status."""
        return {
            "enabled": self._enabled,
            "has_prometheus": HAS_PROMETHEUS,
            "server_started": self._server_started,
            "port": self._port,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_prom: PrometheusMetrics | None = None
_prom_lock = threading.Lock()


def get_prometheus() -> PrometheusMetrics:
    """Get the global Prometheus metrics instance."""
    global _prom
    if _prom is None:
        with _prom_lock:
            if _prom is None:
                _prom = PrometheusMetrics()
    return _prom


def start_prometheus_server() -> bool:
    """Start the Prometheus HTTP server."""
    return get_prometheus().start_server()


def record_tool_call(tool_name: str, duration_seconds: float, status: str) -> None:
    """Convenience: record a tool call metric."""
    get_prometheus().record_tool_call(tool_name, duration_seconds, status)
