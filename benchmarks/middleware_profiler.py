"""P6.5 — Middleware profiler by tool class.

Benchmarks every middleware independently, classifies required middleware
by safety/effect class, and measures post-call hooks separately.

Requirements:
1. Benchmark every middleware independently
2. Classify required middleware by safety/effect class
3. Avoid per-call timeout threads where cooperative/executor-level timeouts work
4. Preserve all controls on mutating, economic, and external operations
5. Require explicit proof for fast paths
6. Measure post-call hooks separately

Usage:
    from benchmarks.middleware_profiler import run_middleware_profile
    report = run_middleware_profile()
"""

from __future__ import annotations

import gc
import json
import statistics
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
class MiddlewareTiming:
    """Per-middleware timing across multiple runs."""

    name: str
    critical: bool = False
    runs: list[float] = field(default_factory=list)
    errors: int = 0

    @property
    def count(self) -> int:
        return len(self.runs)

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.runs) if self.runs else 0.0

    @property
    def p50_ms(self) -> float:
        if not self.runs:
            return 0.0
        s = sorted(self.runs)
        return s[len(s) // 2]

    @property
    def p95_ms(self) -> float:
        if not self.runs:
            return 0.0
        s = sorted(self.runs)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self.runs:
            return 0.0
        s = sorted(self.runs)
        idx = int(len(s) * 0.99)
        return s[min(idx, len(s) - 1)]


@dataclass
class PostCallTiming:
    """Per-post-call-hook timing."""

    name: str
    runs: list[float] = field(default_factory=list)

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.runs) if self.runs else 0.0

    @property
    def p50_ms(self) -> float:
        if not self.runs:
            return 0.0
        s = sorted(self.runs)
        return s[len(s) // 2]


@dataclass
class MiddlewareReport:
    """Full middleware profile report."""

    middleware_timings: dict[str, MiddlewareTiming] = field(default_factory=dict)
    post_call_timings: dict[str, PostCallTiming] = field(default_factory=dict)
    fast_path_timings: list[float] = field(default_factory=list)
    full_pipeline_timings: list[float] = field(default_factory=list)
    tool_class_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)
    iterations: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iterations": self.iterations,
            "middleware": {
                name: {
                    "critical": t.critical,
                    "count": t.count,
                    "mean_ms": round(t.mean_ms, 3),
                    "p50_ms": round(t.p50_ms, 3),
                    "p95_ms": round(t.p95_ms, 3),
                    "p99_ms": round(t.p99_ms, 3),
                    "errors": t.errors,
                }
                for name, t in self.middleware_timings.items()
            },
            "post_call_hooks": {
                name: {
                    "count": len(t.runs),
                    "mean_ms": round(t.mean_ms, 3),
                    "p50_ms": round(t.p50_ms, 3),
                }
                for name, t in self.post_call_timings.items()
            },
            "fast_path": {
                "count": len(self.fast_path_timings),
                "mean_ms": round(statistics.mean(self.fast_path_timings), 3) if self.fast_path_timings else 0,
                "p50_ms": round(sorted(self.fast_path_timings)[len(self.fast_path_timings) // 2], 3) if self.fast_path_timings else 0,
            },
            "full_pipeline": {
                "count": len(self.full_pipeline_timings),
                "mean_ms": round(statistics.mean(self.full_pipeline_timings), 3) if self.full_pipeline_timings else 0,
                "p50_ms": round(sorted(self.full_pipeline_timings)[len(self.full_pipeline_timings) // 2], 3) if self.full_pipeline_timings else 0,
            },
            "tool_class_breakdown": {
                cls: {k: round(v, 3) for k, v in stats.items()}
                for cls, stats in self.tool_class_breakdown.items()
            },
        }


# Middleware classification by safety/effect class
MIDDLEWARE_CLASSES: dict[str, str] = {
    "input_sanitizer": "critical_safety",
    "circuit_breaker": "critical_safety",
    "rate_limiter": "critical_safety",
    "security_monitor": "critical_safety",
    "tool_permissions": "critical_safety",
    "maturity_gate": "critical_safety",
    "governor": "critical_safety",
    "transaction_firewall": "critical_economic",
    "timeout": "operational",
    "pattern_guard": "critical_safety",
    "engagement_token": "operational",
    "model_signing": "operational",
    "cognitive_mode": "operational",
    "zodiac_resonance": "enrichment",
    "citta_consciousness": "enrichment",
    "semantic_cache": "performance",
    "auto_optimize": "performance",
    "inference_router": "performance",
    "draft_review": "performance",
    "token_tracker": "observability",
    "code_nudge": "enrichment",
    "core_router": "dispatch",
    "timing": "observability",
}

# Post-call hook classification
POST_CALL_CLASSES: dict[str, str] = {
    "karma_effects": "governance",
    "observability": "observability",
    "session_recorder": "persistence",
    "error_learner": "learning",
    "wasm_verify": "verification",
}


def _instrument_middleware(pipeline: Any) -> dict[str, list[float]]:
    """Instrument each middleware to capture per-stage timing.

    Wraps each middleware function with a timing collector.
    Returns a dict mapping middleware name → list of durations.
    """
    timings: dict[str, list[float]] = {}
    original_fns: list[tuple[str, Any, Any, bool]] = []

    for i, (name, mw_fn, critical) in enumerate(pipeline._middlewares):
        timings.setdefault(name, [])
        original_fns.append((name, mw_fn, critical))

        def make_wrapper(n: str, fn: Any) -> Any:
            def wrapped(ctx: Any, next_fn: Any) -> Any:
                t0 = time.perf_counter()
                try:
                    result = fn(ctx, next_fn)
                finally:
                    elapsed = (time.perf_counter() - t0) * 1000
                    timings[n].append(elapsed)
                return result
            return wrapped

        pipeline._middlewares[i] = (name, make_wrapper(name, mw_fn), critical)

    # Invalidate cached chain
    pipeline._chain = None
    return timings, original_fns


def _restore_middleware(pipeline: Any, original_fns: list[tuple[str, Any, Any, bool]]) -> None:
    """Restore original middleware functions."""
    pipeline._middlewares = list(original_fns)
    pipeline._chain = None


def _instrument_post_call(pipeline: Any) -> dict[str, list[float]]:
    """Instrument post-call hooks to capture timing."""
    timings: dict[str, list[float]] = {}
    original_hooks: list[tuple[str, Any]] = []

    for i, (name, hook_fn) in enumerate(pipeline._post_call_hooks):
        timings.setdefault(name, [])
        original_hooks.append((name, hook_fn))

        def make_wrapper(n: str, fn: Any) -> Any:
            def wrapped(ctx: Any, result: Any) -> Any:
                t0 = time.perf_counter()
                try:
                    augmented = fn(ctx, result)
                finally:
                    elapsed = (time.perf_counter() - t0) * 1000
                    timings[n].append(elapsed)
                return augmented
            return wrapped

        pipeline._post_call_hooks[i] = (name, make_wrapper(name, hook_fn))

    return timings, original_hooks


def _restore_post_call(pipeline: Any, original_hooks: list[tuple[str, Any]]) -> None:
    """Restore original post-call hooks."""
    pipeline._post_call_hooks = list(original_hooks)


def run_middleware_profile(
    iterations: int = 50,
    tool_name: str = "system.version",
    tool_kwargs: dict[str, Any] | None = None,
) -> MiddlewareReport:
    """Run middleware profiling across multiple iterations.

    Args:
        iterations: Number of dispatch calls to measure.
        tool_name: Tool to dispatch for profiling.
        tool_kwargs: Arguments for the tool.

    Returns:
        MiddlewareReport with per-middleware and post-call timings.
    """
    if tool_kwargs is None:
        tool_kwargs = {}

    report = MiddlewareReport(
        iterations=iterations,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    try:
        from whitemagic.tools.dispatch_table import _pipeline, _is_fast_path, dispatch
    except Exception as e:
        report.middleware_timings["_error"] = MiddlewareTiming(
            name="_error", errors=1, runs=[0.0]
        )
        report.middleware_timings["_error"].error = True
        return report

    # Check fast-path eligibility
    is_fast = _is_fast_path(tool_name)

    if is_fast:
        # Measure fast-path separately
        for _ in range(iterations):
            gc.collect()
            t0 = time.perf_counter()
            dispatch(tool_name, **tool_kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            report.fast_path_timings.append(elapsed)

        # Also measure full pipeline with _force_full_pipeline
        mw_timings, original_fns = _instrument_middleware(_pipeline)
        post_timings, original_hooks = _instrument_post_call(_pipeline)

        for _ in range(iterations):
            gc.collect()
            t0 = time.perf_counter()
            dispatch(tool_name, _force_full_pipeline=True, **tool_kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            report.full_pipeline_timings.append(elapsed)

        _restore_middleware(_pipeline, original_fns)
        _restore_post_call(_pipeline, original_hooks)
    else:
        # Full pipeline only
        mw_timings, original_fns = _instrument_middleware(_pipeline)
        post_timings, original_hooks = _instrument_post_call(_pipeline)

        for _ in range(iterations):
            gc.collect()
            t0 = time.perf_counter()
            dispatch(tool_name, **tool_kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            report.full_pipeline_timings.append(elapsed)

        _restore_middleware(_pipeline, original_fns)
        _restore_post_call(_pipeline, original_hooks)

    # Aggregate middleware timings
    mw_names = set()
    for name, _, critical in _pipeline._middlewares:
        mw_names.add(name)

    for name in mw_names:
        runs = mw_timings.get(name, [])
        is_critical = any(n == name and c for n, _, c in _pipeline._middlewares)
        report.middleware_timings[name] = MiddlewareTiming(
            name=name,
            critical=is_critical,
            runs=runs,
        )

    # Aggregate post-call timings
    for name, _ in _pipeline._post_call_hooks:
        runs = post_timings.get(name, [])
        report.post_call_timings[name] = PostCallTiming(name=name, runs=runs)

    # Tool class breakdown
    try:
        from whitemagic.tools.tool_catalog import get_tool_catalog
        from whitemagic.tools.tool_types import ToolSafety, ToolCategory
        from whitemagic.tools.registry import TOOL_REGISTRY

        by_class: dict[str, list[str]] = {}
        for td in TOOL_REGISTRY:
            cls = f"{td.safety.value}/{td.category.value}"
            by_class.setdefault(cls, []).append(td.name)

        for cls, tools in by_class.items():
            report.tool_class_breakdown[cls] = {
                "tool_count": len(tools),
                "example_tools": min(5, len(tools)),
            }
    except Exception:
        pass

    return report


def print_report(report: MiddlewareReport) -> None:
    """Print a formatted middleware profile report."""
    print(f"\n{'=' * 75}")
    print(f"Middleware Profile ({report.iterations} iterations)")
    print(f"{'=' * 75}")

    if report.fast_path_timings:
        fp = report.fast_path_timings
        print(f"\nFast-path: {len(fp)} calls, mean={statistics.mean(fp):.3f}ms, "
              f"p50={sorted(fp)[len(fp)//2]:.3f}ms")

    if report.full_pipeline_timings:
        fp = report.full_pipeline_timings
        print(f"Full pipeline: {len(fp)} calls, mean={statistics.mean(fp):.3f}ms, "
              f"p50={sorted(fp)[len(fp)//2]:.3f}ms")

    print(f"\n{'Middleware':<30} {'Class':<20} {'Critical':>8} {'Mean(ms)':>10} {'p50(ms)':>10} {'p95(ms)':>10}")
    print("-" * 90)
    for name, t in sorted(report.middleware_timings.items(), key=lambda x: x[1].mean_ms, reverse=True):
        cls = MIDDLEWARE_CLASSES.get(name, "unknown")
        print(f"{name:<30} {cls:<20} {'YES' if t.critical else 'no':>8} "
              f"{t.mean_ms:>10.3f} {t.p50_ms:>10.3f} {t.p95_ms:>10.3f}")

    if report.post_call_timings:
        print(f"\n{'Post-call hook':<30} {'Class':<20} {'Mean(ms)':>10} {'p50(ms)':>10}")
        print("-" * 72)
        for name, t in sorted(report.post_call_timings.items(), key=lambda x: x[1].mean_ms, reverse=True):
            cls = POST_CALL_CLASSES.get(name, "unknown")
            print(f"{name:<30} {cls:<20} {t.mean_ms:>10.3f} {t.p50_ms:>10.3f}")

    if report.tool_class_breakdown:
        print(f"\n{'Tool class (safety/category)':<40} {'Count':>6}")
        print("-" * 48)
        for cls, stats in sorted(report.tool_class_breakdown.items()):
            print(f"{cls:<40} {stats['tool_count']:>6}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Middleware profiler by tool class")
    parser.add_argument("--iterations", "-n", type=int, default=50)
    parser.add_argument("--tool", default="system.version")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    report = run_middleware_profile(
        iterations=args.iterations,
        tool_name=args.tool,
    )
    print_report(report)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
