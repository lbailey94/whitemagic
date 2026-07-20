"""Runtime Health Surface — Aggregated system health metrics.

Phase 8 WI 4 of the Codebase Hardening Strategy.

Exposes a unified health surface that aggregates:
- Middleware latency (per-middleware timing)
- Backend health (SQLite, HNSW, embeddings)
- Cache isolation status (per-user, per-galaxy)
- Native process state (Rust, Julia, Elixir, Haskell, Koka, Zig)
- Degraded capabilities (what's missing or failing)
- Pending migrations (schema version mismatches)

Usage::

    from whitemagic.ops.health_surface import HealthSurface

    surface = HealthSurface()
    report = surface.collect()
    print(report["status"])  # "healthy" | "degraded" | "critical"
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass, field
from importlib.util import find_spec
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: str = "unknown"  # "healthy", "degraded", "down", "unknown"
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class HealthSurface:
    """Aggregates runtime health metrics across all subsystems.

    Collects health from:
    1. Middleware pipeline (per-middleware latency)
    2. Memory backends (SQLite integrity, HNSW, FTS5)
    3. Cache isolation (per-user/galaxy namespace keys)
    4. Native bridges (process state, circuit breaker)
    5. Degraded capabilities (missing optional deps)
    6. Pending migrations (schema version checks)
    """

    def __init__(self) -> None:
        self._last_report: dict[str, Any] = {}
        self._last_collect_time: float = 0.0

    @property
    def last_report(self) -> dict[str, Any]:
        return dict(self._last_report)

    def collect(self) -> dict[str, Any]:
        """Collect a full health report."""
        t0 = time.perf_counter()

        components: list[ComponentHealth] = []
        components.append(self._check_middleware_latency())
        components.append(self._check_memory_backends())
        components.append(self._check_cache_isolation())
        components.append(self._check_native_bridges())
        components.append(self._check_degraded_capabilities())
        components.append(self._check_pending_migrations())
        components.append(self._check_apotheosis_health())

        # Determine overall status
        statuses = [c.status for c in components]
        if "down" in statuses:
            overall = "critical"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        report = {
            "status": overall,
            "collected_at": time.time(),
            "collection_duration_ms": (time.perf_counter() - t0) * 1000,
            "components": {c.name: asdict(c) for c in components},
            "summary": {
                "total_components": len(components),
                "healthy": sum(1 for c in components if c.status == "healthy"),
                "degraded": sum(1 for c in components if c.status == "degraded"),
                "down": sum(1 for c in components if c.status == "down"),
                "unknown": sum(1 for c in components if c.status == "unknown"),
            },
        }

        self._last_report = report
        self._last_collect_time = time.time()
        return report

    def _check_middleware_latency(self) -> ComponentHealth:
        """Check middleware pipeline latency."""
        health = ComponentHealth(name="middleware_latency")

        try:
            from whitemagic.tools.dispatch_table import get_pipeline

            pipeline = get_pipeline()
            middlewares = pipeline.describe() if hasattr(pipeline, "describe") else []

            health.details["middleware_count"] = len(middlewares)
            health.details["middlewares"] = middlewares
            health.status = "healthy"
        except Exception as e:  # noqa: BLE001
            health.status = "degraded"
            health.error = str(e)

        return health

    def _check_memory_backends(self) -> ComponentHealth:
        """Check memory backend health."""
        health = ComponentHealth(name="memory_backends")

        try:
            from whitemagic.ops.migration_cli import MigrationCLI

            cli = MigrationCLI()
            galaxies = cli.inspect()

            total_memories = sum(g.memory_count for g in galaxies)
            all(g.integrity_ok for g in galaxies)
            errors = [e for g in galaxies for e in g.integrity_errors]

            health.details["galaxy_count"] = len(galaxies)
            health.details["total_memories"] = total_memories
            health.details["galaxies"] = [
                {"name": g.name, "memories": g.memory_count, "ok": g.integrity_ok}
                for g in galaxies
            ]

            if errors:
                health.status = "degraded"
                health.error = "; ".join(errors[:3])
            else:
                health.status = "healthy"
        except Exception as e:  # noqa: BLE001
            health.status = "degraded"
            health.error = str(e)

        return health

    def _check_cache_isolation(self) -> ComponentHealth:
        """Check cache namespace isolation."""
        health = ComponentHealth(name="cache_isolation")

        try:
            from whitemagic.tools.middleware import _ensure_cached

            _ensure_cached()
            health.details["cache_initialized"] = True
            health.status = "healthy"
        except Exception as e:  # noqa: BLE001
            health.status = "degraded"
            health.error = str(e)

        return health

    def _check_native_bridges(self) -> ComponentHealth:
        """Check native bridge process states."""
        health = ComponentHealth(name="native_bridges")

        bridges: dict[str, str] = {}

        # Skip polyglot bridge imports if WM_SKIP_POLYGLOT is set (prevents subprocess hangs)
        if os.environ.get("WM_SKIP_POLYGLOT"):
            health.details["bridges"] = {}
            health.details["available"] = 0
            health.details["total"] = 6
            health.status = "degraded"
            health.error = "Polyglot bridges skipped (WM_SKIP_POLYGLOT=1)"
            return health

        # Check each polyglot bridge
        bridge_specs = [
            ("rust", "whitemagic_rs"),
            ("julia", "whitemagic.core.acceleration.julia_interface"),
            ("elixir", "whitemagic.core.acceleration.elixir_interface"),
            ("haskell", "whitemagic.core.acceleration.haskell_interface"),
            ("koka", "whitemagic.core.acceleration.koka_native_bridge"),
            ("zig", "whitemagic.core.acceleration.zig_bridge"),
        ]

        available = 0
        for name, module_path in bridge_specs:
            try:
                if module_path.startswith("whitemagic_rs"):
                    if find_spec(module_path) is not None:
                        bridges[name] = "healthy"
                        available += 1
                    else:
                        bridges[name] = "unavailable"
                else:
                    __import__(module_path)
                    bridges[name] = "healthy"
                    available += 1
            except ImportError:
                bridges[name] = "unavailable"
            except Exception as e:  # noqa: BLE001
                bridges[name] = f"degraded: {e!s}"

        health.details["bridges"] = bridges
        health.details["available"] = available
        health.details["total"] = len(bridge_specs)

        if available == 0:
            health.status = "degraded"
            health.error = "No native bridges available"
        elif available < len(bridge_specs):
            health.status = "degraded"
        else:
            health.status = "healthy"

        return health

    def _check_degraded_capabilities(self) -> ComponentHealth:
        """Check for degraded capabilities (missing optional deps)."""
        health = ComponentHealth(name="degraded_capabilities")

        try:
            from whitemagic.runtime_status import get_runtime_status

            status = get_runtime_status()
            degraded_reasons = status.get("degraded_reasons", [])

            health.details["degraded_reasons"] = degraded_reasons
            health.details["mode"] = status.get("mode", "unknown")
            health.details["version"] = status.get("version", "unknown")

            if degraded_reasons:
                health.status = "degraded"
                health.error = ", ".join(degraded_reasons)
            else:
                health.status = "healthy"
        except Exception as e:  # noqa: BLE001
            health.status = "degraded"
            health.error = str(e)

        return health

    def _check_pending_migrations(self) -> ComponentHealth:
        """Check for pending schema migrations."""
        health = ComponentHealth(name="pending_migrations")

        try:
            from whitemagic.ops.migration_cli import MigrationCLI

            cli = MigrationCLI()
            galaxies = cli.inspect()

            pending: list[dict[str, str]] = []
            for g in galaxies:
                if g.schema_version and g.schema_version not in ("unknown", "current"):
                    pending.append({
                        "galaxy": g.name,
                        "current_version": g.schema_version,
                    })

            health.details["pending_count"] = len(pending)
            health.details["pending"] = pending

            if pending:
                health.status = "degraded"
            else:
                health.status = "healthy"
        except Exception as e:  # noqa: BLE001
            health.status = "unknown"
            health.error = str(e)

        return health

    def _check_apotheosis_health(self) -> ComponentHealth:
        """WI 6: Check ApotheosisEngine biological/immune health metrics."""
        health = ComponentHealth(name="apotheosis_health")

        try:
            from whitemagic.core.consciousness.apotheosis_engine import (
                get_apotheosis_engine,
            )

            engine = get_apotheosis_engine()
            result = engine.tick(available_tools=[])

            health_metrics = result.get("health", {})
            degraded_metrics = [
                m for m, v in health_metrics.items()
                if isinstance(v, dict) and v.get("status") in ("degraded", "critical")
            ]

            health.details["metrics"] = health_metrics
            health.details["degraded_metrics"] = degraded_metrics
            health.details["auto_heal_actions"] = result.get("auto_heal_actions", [])

            if degraded_metrics:
                health.status = "degraded"
                health.error = f"Degraded: {', '.join(degraded_metrics[:3])}"
            else:
                health.status = "healthy"
        except Exception as e:  # noqa: BLE001
            health.status = "unknown"
            health.error = str(e)

        return health


# Singleton
_health_surface: HealthSurface | None = None


def get_health_surface() -> HealthSurface:
    """Get the global HealthSurface singleton."""
    global _health_surface
    if _health_surface is None:
        _health_surface = HealthSurface()
    return _health_surface
