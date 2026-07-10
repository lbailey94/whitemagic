"""Benchmark 3: Performance baseline.

Measures three key performance metrics:
1. Dispatch latency — time to dispatch a simple READ tool through the full pipeline
2. Search latency — time to search memories via the galactic memory system
3. Sensorium build time — time to build the 10-dimensional sensorium

Each metric is measured across multiple iterations to get stable p50/p95/p99 stats.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from typing import Any

os.environ["WM_BENCHMARK_QUIET"] = "1"
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_TOOL_TIMEOUT"] = "30"


def _percentiles(data: list[float]) -> dict[str, float]:
    """Compute min, p50, p95, p99, max, mean for a list of values."""
    if not data:
        return {"min": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0, "mean": 0}
    s = sorted(data)
    n = len(s)
    return {
        "min": round(s[0], 2),
        "p50": round(s[n // 2], 2),
        "p95": round(s[int(n * 0.95)], 2),
        "p99": round(s[min(int(n * 0.99), n - 1)], 2),
        "max": round(s[-1], 2),
        "mean": round(statistics.mean(s), 2),
    }


def bench_dispatch_latency(iterations: int = 50) -> dict[str, Any]:
    """Measure dispatch latency for a fast READ-only tool."""
    from whitemagic.tools.dispatch_table import dispatch

    # Use a fast-path tool for pure pipeline overhead
    latencies: list[float] = []
    success = 0

    # Warm up
    for _ in range(3):
        dispatch("meta.galaxy.overview")

    for i in range(iterations):
        t0 = time.perf_counter()
        result = dispatch("meta.galaxy.overview")
        ms = (time.perf_counter() - t0) * 1000
        if result and isinstance(result, dict) and result.get("status") in ("success", "ok"):
            success += 1
        latencies.append(ms)

    return {
        "metric": "dispatch_latency_ms",
        "tool": "meta.galaxy.overview",
        "iterations": iterations,
        "success": success,
        "percentiles": _percentiles(latencies),
    }


def bench_dispatch_latency_full(iterations: int = 30) -> dict[str, Any]:
    """Measure dispatch latency for a full-pipeline tool."""
    from whitemagic.tools.dispatch_table import dispatch

    latencies: list[float] = []
    success = 0

    # Warm up
    for _ in range(3):
        dispatch("gnosis", query="test", _force_full_pipeline=True)

    for i in range(iterations):
        t0 = time.perf_counter()
        result = dispatch("gnosis", query="test", _force_full_pipeline=True)
        ms = (time.perf_counter() - t0) * 1000
        if result and isinstance(result, dict):
            success += 1
        latencies.append(ms)

    return {
        "metric": "dispatch_latency_full_pipeline_ms",
        "tool": "gnosis",
        "iterations": iterations,
        "success": success,
        "percentiles": _percentiles(latencies),
    }


def bench_search_latency(iterations: int = 30) -> dict[str, Any]:
    """Measure memory search latency."""
    from whitemagic.core.galactic import memory_search

    latencies: list[float] = []
    result_count = 0

    # Warm up
    for _ in range(3):
        memory_search("consciousness", limit=5)

    for i in range(iterations):
        t0 = time.perf_counter()
        results = memory_search("consciousness", limit=5)
        ms = (time.perf_counter() - t0) * 1000
        result_count += len(results) if results else 0
        latencies.append(ms)

    return {
        "metric": "search_latency_ms",
        "query": "consciousness",
        "iterations": iterations,
        "avg_results": round(result_count / iterations, 1) if iterations else 0,
        "percentiles": _percentiles(latencies),
    }


def bench_sensorium_build(iterations: int = 10) -> dict[str, Any]:
    """Measure sensorium build time."""
    from whitemagic.tools.prat_resonance import _build_sensorium

    latencies: list[float] = []
    dim_counts: list[int] = []

    for i in range(iterations):
        t0 = time.perf_counter()
        sensorium = _build_sensorium()
        ms = (time.perf_counter() - t0) * 1000
        latencies.append(ms)
        dim_counts.append(len(sensorium))

    return {
        "metric": "sensorium_build_ms",
        "iterations": iterations,
        "avg_dimensions": round(statistics.mean(dim_counts), 1) if dim_counts else 0,
        "percentiles": _percentiles(latencies),
    }


def main() -> None:
    print("=" * 70)
    print("BENCHMARK 3: PERFORMANCE BASELINE")
    print("=" * 70)
    print()

    results: list[dict[str, Any]] = []

    # 1. Dispatch latency (fast-path)
    print("1. Dispatch latency (fast-path: meta.galaxy.overview)...")
    r1 = bench_dispatch_latency(50)
    results.append(r1)
    p = r1["percentiles"]
    print(f"   {r1['success']}/{r1['iterations']} success")
    print(f"   p50={p['p50']}ms  p95={p['p95']}ms  p99={p['p99']}ms  mean={p['mean']}ms")
    print()

    # 2. Dispatch latency (full pipeline)
    print("2. Dispatch latency (full pipeline: gnosis)...")
    r2 = bench_dispatch_latency_full(30)
    results.append(r2)
    p = r2["percentiles"]
    print(f"   {r2['success']}/{r2['iterations']} success")
    print(f"   p50={p['p50']}ms  p95={p['p95']}ms  p99={p['p99']}ms  mean={p['mean']}ms")
    print()

    # 3. Search latency
    print("3. Memory search latency (query='consciousness')...")
    r3 = bench_search_latency(30)
    results.append(r3)
    p = r3["percentiles"]
    print(f"   avg_results={r3['avg_results']}")
    print(f"   p50={p['p50']}ms  p95={p['p95']}ms  p99={p['p99']}ms  mean={p['mean']}ms")
    print()

    # 4. Sensorium build time
    print("4. Sensorium build time...")
    r4 = bench_sensorium_build(10)
    results.append(r4)
    p = r4["percentiles"]
    print(f"   avg_dimensions={r4['avg_dimensions']}")
    print(f"   p50={p['p50']}ms  p95={p['p95']}ms  p99={p['p99']}ms  mean={p['mean']}ms")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<35s} {'p50':>8s} {'p95':>8s} {'p99':>8s} {'mean':>8s}")
    print("-" * 70)
    for r in results:
        p = r["percentiles"]
        print(f"{r['metric']:<35s} {p['p50']:>7.1f}ms {p['p95']:>7.1f}ms {p['p99']:>7.1f}ms {p['mean']:>7.1f}ms")
    print()

    # Targets
    targets = {
        "dispatch_latency_ms": ("<50ms p50", r1["percentiles"]["p50"] < 50),
        "dispatch_latency_full_pipeline_ms": ("<500ms p50", r2["percentiles"]["p50"] < 500),
        "search_latency_ms": ("<100ms p50", r3["percentiles"]["p50"] < 100),
        "sensorium_build_ms": ("<10000ms p50", r4["percentiles"]["p50"] < 10000),
    }
    print("Targets:")
    all_pass = True
    for metric, (desc, passed) in targets.items():
        icon = "OK" if passed else "FAIL"
        print(f"  [{icon}] {metric}: {desc}")
        if not passed:
            all_pass = False
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")

    # Save
    output = {
        "results": results,
        "targets": {k: {"desc": v[0], "passed": v[1]} for k, v in targets.items()},
        "overall_pass": all_pass,
    }
    with open("/tmp/benchmark_performance.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nDetailed results saved to /tmp/benchmark_performance.json")


if __name__ == "__main__":
    main()
