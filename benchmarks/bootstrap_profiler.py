"""P6.4 — Cold bootstrap profiler.

Profiles the cold-start path in this order:
1. Registry synthesis/materialization
2. Schema conversion
3. Dispatch import graph
4. Post-call initialization
5. Stable-surface listing
6. Fast-path verification

Provisional targets (to be adjusted after representative profiling):
- Base import under 100 ms
- Registry materialization under 250 ms
- First safe introspection tool under 500 ms
- Warm safe introspection under 10 ms

Usage:
    from benchmarks.bootstrap_profiler import run_bootstrap_profile
    report = run_bootstrap_profile()
"""

from __future__ import annotations

import gc
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class StageProfile:
    """Timing for a single bootstrap stage."""

    name: str
    duration_ms: float = 0.0
    target_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def within_target(self) -> bool:
        if self.target_ms is None:
            return True
        return self.duration_ms <= self.target_ms


@dataclass
class BootstrapReport:
    """Full cold bootstrap profile."""

    stages: list[StageProfile] = field(default_factory=list)
    total_ms: float = 0.0
    base_import_ms: float = 0.0
    registry_materialization_ms: float = 0.0
    first_tool_ms: float = 0.0
    warm_tool_ms: float = 0.0
    python_version: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "python_version": self.python_version,
            "total_ms": round(self.total_ms, 2),
            "base_import_ms": round(self.base_import_ms, 2),
            "registry_materialization_ms": round(self.registry_materialization_ms, 2),
            "first_tool_ms": round(self.first_tool_ms, 2),
            "warm_tool_ms": round(self.warm_tool_ms, 2),
            "targets": {
                "base_import": 100,
                "registry_materialization": 250,
                "first_safe_introspection": 500,
                "warm_safe_introspection": 10,
            },
            "stages": [
                {
                    "name": s.name,
                    "duration_ms": round(s.duration_ms, 2),
                    "target_ms": s.target_ms,
                    "within_target": s.within_target,
                    "error": s.error,
                    "details": s.details,
                }
                for s in self.stages
            ],
        }


def _timed_import(module_path: str) -> tuple[float, Any | None, str | None]:
    """Import a module and return (duration_ms, module, error)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        mod = __import__(module_path, fromlist=["__name__"])
        elapsed = (time.perf_counter() - t0) * 1000
        return elapsed, mod, None
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return elapsed, None, str(e)


def _profile_base_import() -> StageProfile:
    """Stage 0: Base import of whitemagic package."""
    elapsed, mod, err = _timed_import("whitemagic")
    version = getattr(mod, "__version__", "unknown") if mod else "error"
    return StageProfile(
        name="base_import",
        duration_ms=elapsed,
        target_ms=100,
        details={"version": version},
        error=err,
    )


def _profile_registry_materialization() -> StageProfile:
    """Stage 1: Registry synthesis/materialization."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(
            name="registry_materialization",
            duration_ms=elapsed,
            target_ms=250,
            details={"tool_count": len(DISPATCH_TABLE)},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="registry_materialization", duration_ms=elapsed, target_ms=250, error=str(e))


def _profile_schema_conversion() -> StageProfile:
    """Stage 2: Schema conversion (SQLite schema init)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.core.memory.sqlite_schema import SchemaManager
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(
            name="schema_conversion",
            duration_ms=elapsed,
            details={"schema_manager": "loaded"},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="schema_conversion", duration_ms=elapsed, error=str(e))


def _profile_dispatch_import() -> StageProfile:
    """Stage 3: Dispatch import graph (middleware pipeline build)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.tools.dispatch_table import _build_pipeline
        pipeline = _build_pipeline()
        elapsed = (time.perf_counter() - t0) * 1000
        middleware_count = len(pipeline._middleware) if hasattr(pipeline, "_middleware") else 0
        return StageProfile(
            name="dispatch_import",
            duration_ms=elapsed,
            details={"middleware_count": middleware_count},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="dispatch_import", duration_ms=elapsed, error=str(e))


def _profile_post_call_init() -> StageProfile:
    """Stage 4: Post-call initialization (lazy init simulation)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.run_mcp_lean import _ensure_init
        _ensure_init()
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(
            name="post_call_init",
            duration_ms=elapsed,
            details={"initialized": True},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="post_call_init", duration_ms=elapsed, error=str(e))


def _profile_stable_surface_listing() -> StageProfile:
    """Stage 5: Stable-surface listing (tool catalog)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.tools.tool_catalog import get_tool_catalog
        catalog = get_tool_catalog()
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(
            name="stable_surface_listing",
            duration_ms=elapsed,
            details={"catalog_entries": len(catalog) if isinstance(catalog, (list, dict)) else "n/a"},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="stable_surface_listing", duration_ms=elapsed, error=str(e))


def _profile_fast_path_verification() -> StageProfile:
    """Stage 6: Fast-path verification (dispatch a read-only tool)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.tools.dispatch_core import dispatch
        result = dispatch("system.version", {})
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(
            name="fast_path_verification",
            duration_ms=elapsed,
            target_ms=500,
            details={"dispatched": "system.version", "result_type": type(result).__name__},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="fast_path_verification", duration_ms=elapsed, target_ms=500, error=str(e))


def _profile_warm_fast_path() -> StageProfile:
    """Stage 7: Warm fast-path (second dispatch of same tool)."""
    gc.collect()
    t0 = time.perf_counter()
    try:
        from whitemagic.tools.dispatch_core import dispatch
        result = dispatch("system.version", {})
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(
            name="warm_fast_path",
            duration_ms=elapsed,
            target_ms=10,
            details={"dispatched": "system.version", "result_type": type(result).__name__},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return StageProfile(name="warm_fast_path", duration_ms=elapsed, target_ms=10, error=str(e))


def run_bootstrap_profile() -> BootstrapReport:
    """Run full cold bootstrap profile.

    Profiles each stage in order, measuring duration against provisional targets.
    """
    report = BootstrapReport(
        python_version=sys.version.split()[0],
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    t_total = time.perf_counter()

    # Stage 0: Base import
    stage = _profile_base_import()
    report.stages.append(stage)
    report.base_import_ms = stage.duration_ms

    # Stage 1: Registry materialization
    stage = _profile_registry_materialization()
    report.stages.append(stage)
    report.registry_materialization_ms = stage.duration_ms

    # Stage 2: Schema conversion
    stage = _profile_schema_conversion()
    report.stages.append(stage)

    # Stage 3: Dispatch import graph
    stage = _profile_dispatch_import()
    report.stages.append(stage)

    # Stage 4: Post-call initialization
    stage = _profile_post_call_init()
    report.stages.append(stage)

    # Stage 5: Stable-surface listing
    stage = _profile_stable_surface_listing()
    report.stages.append(stage)

    # Stage 6: Fast-path verification (cold)
    stage = _profile_fast_path_verification()
    report.stages.append(stage)
    report.first_tool_ms = stage.duration_ms

    # Stage 7: Warm fast-path
    stage = _profile_warm_fast_path()
    report.stages.append(stage)
    report.warm_tool_ms = stage.duration_ms

    report.total_ms = (time.perf_counter() - t_total) * 1000

    return report


def print_report(report: BootstrapReport) -> None:
    """Print a formatted bootstrap profile report."""
    print(f"\n{'=' * 70}")
    print(f"Cold Bootstrap Profile ({report.python_version})")
    print(f"{'=' * 70}")
    print(f"\nTotal: {report.total_ms:.1f}ms")
    print(f"\n{'Stage':<30} {'Duration':>10} {'Target':>10} {'Status':>8}")
    print("-" * 62)
    for s in report.stages:
        status = "PASS" if s.within_target else "OVER"
        target_str = f"{s.target_ms}ms" if s.target_ms else "n/a"
        error_str = f" ERROR: {s.error}" if s.error else ""
        print(f"{s.name:<30} {s.duration_ms:>9.1f}ms {target_str:>10} {status:>8}{error_str}")

    print(f"\nKey metrics:")
    print(f"  Base import:              {report.base_import_ms:.1f}ms (target: 100ms)")
    print(f"  Registry materialization: {report.registry_materialization_ms:.1f}ms (target: 250ms)")
    print(f"  First safe introspection: {report.first_tool_ms:.1f}ms (target: 500ms)")
    print(f"  Warm safe introspection:  {report.warm_tool_ms:.1f}ms (target: 10ms)")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Cold bootstrap profiler")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    args = parser.parse_args()

    report = run_bootstrap_profile()
    print_report(report)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
