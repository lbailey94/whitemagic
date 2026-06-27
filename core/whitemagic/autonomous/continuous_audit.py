# ruff: noqa: BLE001
"""
Continuous Audit System — Autonomous learning loop.

Wires together existing systems for moment-to-moment self-awareness.
Instead of auditing every few hours/days, audit constantly.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class ContinuousAudit:
    """Continuous autonomous audit loop."""

    def __init__(self) -> None:
        self.checks: dict[str, Callable[[], dict[str, Any]]] = {}
        self.results: list[dict[str, Any]] = []
        self._last_audit: float = 0.0
        self._audit_count: int = 0

    def register_check(self, name: str, check_fn: Callable[[], dict[str, Any]]) -> None:
        """Register an audit check."""
        self.checks[name] = check_fn

    def run_audit(self) -> dict[str, Any]:
        """Run all registered checks."""
        self._last_audit = time.time()
        self._audit_count += 1
        check_results: dict[str, Any] = {}
        issues_found = 0

        for name, check_fn in self.checks.items():
            try:
                result = check_fn()
                check_results[name] = result
                if result.get("status") == "issue":
                    issues_found += 1
            except Exception as e:
                check_results[name] = {"status": "error", "error": str(e)}
                issues_found += 1

        audit = {
            "audit_id": self._audit_count,
            "timestamp": self._last_audit,
            "checks_run": len(self.checks),
            "issues_found": issues_found,
            "results": check_results,
        }
        self.results.append(audit)
        return audit

    def recent_results(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.results[-limit:]

    def health_trend(self) -> list[float]:
        """Get health trend (1.0 = healthy, 0.0 = issues)."""
        return [
            1.0 - (r["issues_found"] / max(r["checks_run"], 1))
            for r in self.results
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "total_audits": self._audit_count,
            "registered_checks": len(self.checks),
            "last_audit": self._last_audit,
            "avg_health": (
                sum(self.health_trend()) / len(self.health_trend())
                if self.health_trend() else 1.0
            ),
        }


_audit: ContinuousAudit | None = None


def get_continuous_audit() -> ContinuousAudit:
    global _audit
    if _audit is None:
        _audit = ContinuousAudit()
    return _audit
