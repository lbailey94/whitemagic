#!/usr/bin/env python3
"""
WhiteMagic Benchmark Gauntlet — Comprehensive performance measurement.

Runs all core subsystem benchmarks and produces a rich formatted report
showing latency, throughput, and relative performance vs. baselines.

Usage:
    python scripts/benchmark_gauntlet.py            # Full gauntlet
    python scripts/benchmark_gauntlet.py --quick    # Fast probes only
    python scripts/benchmark_gauntlet.py --json     # JSON output
    python scripts/benchmark_gauntlet.py --suite memory  # Specific suite
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_STATE_ROOT", "/tmp/wm_gauntlet")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BenchResult:
    name: str
    value: float           # primary measurement
    unit: str              # "ms", "µs", "ops/s", "MB/s"
    baseline: Optional[float] = None  # expected value for this unit
    notes: str = ""
    status: str = "ok"     # ok | warn | fail | skip
    error: str = ""

    @property
    def delta_pct(self) -> Optional[float]:
        if self.baseline is None:
            return None
        return ((self.value - self.baseline) / self.baseline) * 100

    @property
    def rating(self) -> str:
        if self.status in ("skip", "fail"):
            return {"skip": "⏭️", "fail": "❌"}.get(self.status, "❓")
        d = self.delta_pct
        if d is None:
            return "📊"
        if "ops" in self.unit or "/s" in self.unit:
            # Higher is better
            if d >= 10: return "🚀"
            if d >= -10: return "✅"
            if d >= -25: return "⚠️"
            return "❌"
        else:
            # Lower is better (latency)
            if d <= -10: return "🚀"
            if d <= 10: return "✅"
            if d <= 30: return "⚠️"
            return "❌"


@dataclass
class BenchSuite:
    name: str
    results: list[BenchResult] = field(default_factory=list)
    duration_s: float = 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Timing helpers
# ──────────────────────────────────────────────────────────────────────────────

def timeit(fn: Callable, n: int = 10, warmup: int = 2) -> float:
    """Return median time in ms across n runs."""
    gc.disable()
    try:
        for _ in range(warmup):
            fn()
        times = []
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        return times[len(times) // 2]  # median
    finally:
        gc.enable()


def safe_bench(name: str, fn: Callable, unit: str = "ms",
               baseline: Optional[float] = None, n: int = 10,
               warmup: int = 2, notes: str = "") -> BenchResult:
    """Run a benchmark safely, catching all errors."""
    try:
        ms = timeit(fn, n=n, warmup=warmup)
        value = ms if unit in ("ms", "µs") else ms
        if unit == "µs":
            value = ms * 1000
        return BenchResult(name=name, value=round(value, 3), unit=unit,
                           baseline=baseline, notes=notes)
    except ImportError as exc:
        return BenchResult(name=name, value=0, unit=unit, status="skip",
                           baseline=baseline, error=f"Not available: {exc}")
    except Exception as exc:
        return BenchResult(name=name, value=0, unit=unit, status="fail",
                           baseline=baseline, error=str(exc)[:120])


# ──────────────────────────────────────────────────────────────────────────────
# Benchmark suites
# ──────────────────────────────────────────────────────────────────────────────

def bench_tool_dispatch(quick: bool = False) -> BenchSuite:
    suite = BenchSuite("Tool Dispatch")
    t0 = time.monotonic()

    # Tool registry load
    def load_registry():
        from importlib import import_module
        import_module("whitemagic.tools.tool_surface")

    suite.results.append(safe_bench(
        "Registry import", load_registry, "ms", baseline=50.0,
        n=3, warmup=1, notes="one-time startup cost"
    ))

    # Tool dispatch call
    try:
        from whitemagic.tools.unified_api import call_tool
        suite.results.append(safe_bench(
            "call_tool('health_report')", lambda: call_tool("health_report"),
            "ms", baseline=5.0, n=5 if not quick else 2, warmup=1,
        ))
        suite.results.append(safe_bench(
            "call_tool('gnosis')", lambda: call_tool("gnosis"),
            "ms", baseline=10.0, n=5 if not quick else 2, warmup=1,
        ))
    except ImportError as exc:
        suite.results.append(BenchResult("call_tool", 0, "ms", status="skip", error=str(exc)))

    suite.duration_s = time.monotonic() - t0
    return suite


def bench_memory(quick: bool = False) -> BenchSuite:
    suite = BenchSuite("Memory System")
    t0 = time.monotonic()

    try:
        from whitemagic.tools.unified_api import call_tool

        # Memory create
        _state = {"i": 0}
        def create_mem():
            _state["i"] += 1
            return call_tool("create_memory", content=f"Gauntlet test memory #{_state['i']}",
                             tags=["gauntlet", "test"], importance=0.5)

        suite.results.append(safe_bench(
            "create_memory()", create_mem, "ms", baseline=5.0,
            n=5 if not quick else 2, warmup=1,
            notes="SQLite write + associations"
        ))

        # Memory search
        suite.results.append(safe_bench(
            "search_memories() (text)", lambda: call_tool(
                "search_memories", query="test", limit=5),
            "ms", baseline=10.0, n=10 if not quick else 3, warmup=2,
            notes="text-based fuzzy search"
        ))

        suite.results.append(safe_bench(
            "fast_read_memory()", lambda: call_tool("fast_read_memory"),
            "ms", baseline=2.0, n=10 if not quick else 3, warmup=2,
            notes="recent memories (no search)"
        ))

    except ImportError as exc:
        suite.results.append(BenchResult("memory ops", 0, "ms", status="skip", error=str(exc)))

    suite.duration_s = time.monotonic() - t0
    return suite


def bench_mcp(quick: bool = False) -> BenchSuite:
    suite = BenchSuite("MCP Layer")
    t0 = time.monotonic()

    try:
        from whitemagic.runtime_status import get_runtime_status
        suite.results.append(safe_bench(
            "get_runtime_status()", get_runtime_status, "µs",
            baseline=500.0, n=20 if not quick else 5, warmup=3,
            notes="runtime readiness probe"
        ))
    except ImportError as exc:
        suite.results.append(BenchResult("runtime_status", 0, "µs", status="skip", error=str(exc)))

    try:
        from whitemagic.tools.manifest import get_manifest
        suite.results.append(safe_bench(
            "tools manifest()", get_manifest, "ms",
            baseline=5.0, n=5, warmup=1,
            notes="full tool manifest generation"
        ))
    except ImportError as exc:
        suite.results.append(BenchResult("manifest", 0, "ms", status="skip", error=str(exc)))

    suite.duration_s = time.monotonic() - t0
    return suite


def bench_rust_bridge(quick: bool = False) -> BenchSuite:
    suite = BenchSuite("Rust Bridge")
    t0 = time.monotonic()

    try:
        import whitemagic_rust as rs  # type: ignore[import]

        # SIMD similarity (if available)
        if hasattr(rs, "rust_cosine_similarity"):
            import random
            vec_a = [random.random() for _ in range(384)]
            vec_b = [random.random() for _ in range(384)]
            suite.results.append(safe_bench(
                "rust_cosine_similarity (384-dim)", lambda: rs.rust_cosine_similarity(vec_a, vec_b),
                "µs", baseline=20.0, n=100 if not quick else 20, warmup=5,
                notes="SIMD-hinted Rust implementation"
            ))

        if hasattr(rs, "euclidean_distance"):
            import random
            vec_a = [random.random() for _ in range(384)]
            vec_b = [random.random() for _ in range(384)]
            suite.results.append(safe_bench(
                "euclidean_distance (384-dim)", lambda: rs.euclidean_distance(vec_a, vec_b),
                "µs", baseline=15.0, n=100 if not quick else 20, warmup=5,
                notes="SIMD-hinted Rust implementation"
            ))

        # Hash function
        if hasattr(rs, "compute_sha256"):
            text = "The quick brown fox jumps over the lazy dog" * 10
            suite.results.append(safe_bench(
                "compute_sha256 (440 chars)", lambda: rs.compute_sha256(text),
                "µs", baseline=5.0, n=100 if not quick else 20, warmup=5,
                notes="Rust native SHA256"
            ))

        if not suite.results:
            suite.results.append(BenchResult(
                "whitemagic_rust", 0, "ms", status="skip",
                error="Module loaded but no benchmark functions found"
            ))

    except ImportError:
        suite.results.append(BenchResult(
            "Rust bridge", 0, "ms", status="skip",
            error="whitemagic_rs not compiled — run: cd whitemagic-rust && maturin develop"
        ))

    suite.duration_s = time.monotonic() - t0
    return suite


def bench_config(quick: bool = False) -> BenchSuite:
    suite = BenchSuite("Config & Paths")
    t0 = time.monotonic()

    try:
        from whitemagic.config.paths import get_paths
        suite.results.append(safe_bench(
            "get_paths()", get_paths, "µs", baseline=100.0,
            n=50 if not quick else 10, warmup=5,
            notes="config path resolution"
        ))
    except ImportError as exc:
        suite.results.append(BenchResult("get_paths", 0, "µs", status="skip", error=str(exc)))

    try:
        from whitemagic.config import get_config
        suite.results.append(safe_bench(
            "get_config()", get_config, "µs", baseline=200.0,
            n=20 if not quick else 5, warmup=2,
            notes="config load (may be cached)"
        ))
    except ImportError as exc:
        suite.results.append(BenchResult("get_config", 0, "µs", status="skip", error=str(exc)))

    suite.duration_s = time.monotonic() - t0
    return suite


# ──────────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────────

def fmt_value(r: BenchResult) -> str:
    if r.status in ("skip", "fail"):
        return f"[dim]{r.error[:60]}[/dim]"
    d = r.delta_pct
    if d is not None:
        sign = "+" if d > 0 else ""
        pct_color = "red" if (d > 10 and "ms" in r.unit) or (d < -10 and "ops" in r.unit) else "green"
        return f"[bold]{r.value:,.1f} {r.unit}[/bold]  [dim {pct_color}]({sign}{d:.0f}%)[/dim {pct_color}]"
    return f"[bold]{r.value:,.1f} {r.unit}[/bold]"


def render_report(suites: list[BenchSuite], total_s: float) -> Table:
    table = Table(box=box.ROUNDED, expand=True,
                  title="[bold]WhiteMagic Benchmark Gauntlet[/bold]",
                  header_style="bold cyan", show_header=True)
    table.add_column("Suite / Benchmark", style="white", no_wrap=True)
    table.add_column("Rating", justify="center", width=5)
    table.add_column("Result", justify="right")
    table.add_column("Baseline", justify="right", style="dim")
    table.add_column("Notes", style="dim", no_wrap=False)

    for suite in suites:
        table.add_row(f"[bold cyan]━ {suite.name}[/bold cyan]", "", "", "", "")
        for r in suite.results:
            baseline_str = f"{r.baseline:,.1f} {r.unit}" if r.baseline else "—"
            table.add_row(
                f"  {r.name}", r.rating, fmt_value(r), baseline_str, r.notes
            )

    table.add_section()
    table.add_row(f"[bold]Total time[/bold]", "", f"[bold]{total_s:.2f}s[/bold]", "", "")
    return table


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

ALL_SUITES: dict[str, Callable] = {
    "dispatch": bench_tool_dispatch,
    "memory":   bench_memory,
    "mcp":      bench_mcp,
    "rust":     bench_rust_bridge,
    "config":   bench_config,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="WhiteMagic Benchmark Gauntlet")
    parser.add_argument("--quick", action="store_true", help="Fewer iterations, faster run")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--suite", choices=list(ALL_SUITES), help="Run only one suite")
    args = parser.parse_args()

    suites_to_run = {args.suite: ALL_SUITES[args.suite]} if args.suite else ALL_SUITES

    if HAS_RICH and not args.json:
        console = Console()
        console.print(Panel.fit(
            "[bold magenta]WhiteMagic Benchmark Gauntlet[/bold magenta]\n"
            "[dim]Measuring core subsystem performance[/dim]" +
            (" [yellow](quick mode)[/yellow]" if args.quick else ""),
            border_style="magenta",
        ))

    results: list[BenchSuite] = []
    t_total = time.monotonic()

    for key, fn in suites_to_run.items():
        if HAS_RICH and not args.json:
            Console().print(f"  [cyan]▸[/cyan] Running [bold]{fn.__doc__ or key}[/bold]...")
        suite = fn(quick=args.quick)
        results.append(suite)

    elapsed = time.monotonic() - t_total

    if args.json:
        report = {
            "duration_s": round(elapsed, 3),
            "suites": [
                {"name": s.name, "duration_s": round(s.duration_s, 3),
                 "benchmarks": [
                     {"name": r.name, "value": r.value, "unit": r.unit,
                      "baseline": r.baseline, "status": r.status,
                      "delta_pct": round(r.delta_pct, 1) if r.delta_pct is not None else None,
                      "error": r.error}
                     for r in s.results
                 ]}
                for s in results
            ]
        }
        print(json.dumps(report, indent=2))
        return 0

    if HAS_RICH:
        console = Console()
        console.print()
        console.print(render_report(results, elapsed))
    else:
        print(f"\nBenchmark Gauntlet ({elapsed:.2f}s)")
        print("─" * 60)
        for s in results:
            print(f"\n{s.name}")
            for r in s.results:
                print(f"  {r.icon} {r.name:<40} {r.value:>10.2f} {r.unit}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
