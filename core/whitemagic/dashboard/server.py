# ruff: noqa: BLE001
"""
WhiteMagic Dashboard API Server.

Provides REST API endpoints for the dashboard.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DashboardServer:
    """Dashboard API server (data provider, not actual HTTP server)."""

    def __init__(self) -> None:
        self._endpoints: dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._endpoints = {
            "/api/health": self._health_endpoint,
            "/api/metrics": self._metrics_endpoint,
            "/api/gardens": self._gardens_endpoint,
            "/api/tools": self._tools_endpoint,
        }

    def _health_endpoint(self) -> dict[str, Any]:
        return {"status": "ok", "version": "24.1.0"}

    def _metrics_endpoint(self) -> dict[str, Any]:
        try:
            from whitemagic.homeostasis.metrics import get_metrics

            return get_metrics().summary()
        except Exception:
            return {"status": "unavailable"}

    def _gardens_endpoint(self) -> dict[str, Any]:
        try:
            from whitemagic.gardens.synthesis import get_synthesis

            return get_synthesis().summary()
        except Exception:
            return {"status": "unavailable"}

    def _tools_endpoint(self) -> dict[str, Any]:
        try:
            from whitemagic.tools.dispatch_table import DISPATCH_TABLE

            return {
                "total_tools": len(DISPATCH_TABLE),
                "tools": list(DISPATCH_TABLE.keys())[:20],
            }
        except Exception:
            return {"status": "unavailable"}

    def handle_request(self, path: str) -> dict[str, Any]:
        """Handle a request to an endpoint."""
        handler = self._endpoints.get(path)
        if handler:
            try:
                return handler()
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"status": "not_found", "path": path}

    def list_endpoints(self) -> list[str]:
        return list(self._endpoints.keys())

    def summary(self) -> dict[str, Any]:
        return {"endpoints": len(self._endpoints)}


_server: DashboardServer | None = None


def get_dashboard_server() -> DashboardServer:
    global _server
    if _server is None:
        _server = DashboardServer()
    return _server
