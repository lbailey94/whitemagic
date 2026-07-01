#!/usr/bin/env python3
"""Benchmark suite for inference acceleration components.

Measures:
  1. Ternary GEMV: Python scalar vs Rust AVX2 (if available)
  2. HLL cardinality estimation: accuracy vs memory
  3. Count-Min Sketch: frequency estimation accuracy
  4. Routing metrics: overhead per decision
  5. Memory analytics: throughput (ops/sec)

Usage:
    python scripts/bench_inference.py
    python scripts/bench_inference.py --size 1024 --iterations 1000
"""

from __future__ import annotations

import argparse
import random
import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from whitemagic.core.memory.probabilistic import (
    CountMinSketch,
    HyperLogLog,
    MemoryAnalytics,
)
from whitemagic.inference.complexity import ComplexityClassifier
from whitemagic.inference.routing_metrics import RoutingMetrics


def benchmark_ternary_gemv_python(m: int, k: int, iterations: int) -> dict:
    """Benchmark pure Python ternary GEMV."""
    weights = [random.choice([-1, 0, 1]) for _ in range(m * k)]
    activations = [random.uniform(-1, 1) for _ in range(k)]

    start = time.perf_counter()
    for _ in range(iterations):
        result = []
        for i in range(m):
            row = weights[i * k : (i + 1) * k]
            dot = sum(w * a for w, a in zip(row, activations))
            result.append(dot)
    elapsed = time.perf_counter() - start

    return {
        "backend": "python_scalar",
        "m": m,
        "k": k,
        "iterations": iterations,
        "total_time_s": round(elapsed, 4),
        "ops_per_sec": round(iterations / elapsed, 0),
        "avg_latency_us": round(elapsed / iterations * 1e6, 1),
    }


def benchmark_ternary_gemv_rust(m: int, k: int, iterations: int) -> dict | None:
    """Benchmark Rust ternary GEMV via PyO3 (if available)."""
    try:
        import whitemagic_rust

        rust_inference = whitemagic_rust.inference
    except (ImportError, AttributeError):
        return None

    weights = [random.choice([-1, 0, 1]) for _ in range(m * k)]
    activations = [random.uniform(-1, 1) for _ in range(k)]
    packed = rust_inference.py_pack_ternary_matrix(weights, m, k)

    # Warmup
    rust_inference.py_ternary_gemv(packed, activations, m, k)

    start = time.perf_counter()
    for _ in range(iterations):
        rust_inference.py_ternary_gemv(packed, activations, m, k)
    elapsed = time.perf_counter() - start

    backend = rust_inference.py_ternary_backend()

    return {
        "backend": f"rust_{backend}",
        "m": m,
        "k": k,
        "iterations": iterations,
        "total_time_s": round(elapsed, 4),
        "ops_per_sec": round(iterations / elapsed, 0),
        "avg_latency_us": round(elapsed / iterations * 1e6, 1),
    }


def benchmark_hll(n: int, precision: int = 14) -> dict:
    """Benchmark HyperLogLog cardinality estimation."""
    hll = HyperLogLog(precision=precision)
    items = [f"item_{i}" for i in range(n)]

    start = time.perf_counter()
    for item in items:
        hll.add(item)
    elapsed = time.perf_counter() - start

    estimate = hll.estimate()
    error_pct = abs(estimate - n) / n * 100 if n > 0 else 0

    return {
        "structure": "HyperLogLog",
        "n_items": n,
        "precision": precision,
        "estimate": round(estimate, 0),
        "error_pct": round(error_pct, 2),
        "memory_bytes": hll.memory_bytes(),
        "ingest_time_s": round(elapsed, 4),
        "ingest_ops_per_sec": round(n / elapsed, 0),
    }


def benchmark_cms(n: int, width: int = 4096, depth: int = 5) -> dict:
    """Benchmark Count-Min Sketch frequency estimation."""
    cms = CountMinSketch(width=width, depth=depth)
    # Create a skewed distribution: 10 hot keys, 90 cold keys
    hot_keys = [f"hot_{i}" for i in range(10)]
    cold_keys = [f"cold_{i}" for i in range(90)]
    start = time.perf_counter()
    for _ in range(n):
        # 80% requests to hot keys, 20% to cold
        if random.random() < 0.8:
            key = random.choice(hot_keys)
        else:
            key = random.choice(cold_keys)
        cms.add(key)
    elapsed = time.perf_counter() - start

    hot_estimates = {k: cms.estimate(k) for k in hot_keys}
    total_estimated = sum(hot_estimates.values())
    total_actual = int(n * 0.8)  # Approximate

    return {
        "structure": "CountMinSketch",
        "n_increments": n,
        "width": width,
        "depth": depth,
        "memory_bytes": cms.memory_bytes(),
        "ingest_time_s": round(elapsed, 4),
        "ingest_ops_per_sec": round(n / elapsed, 0),
        "hot_key_estimates": hot_estimates,
        "total_hot_estimated": total_estimated,
        "total_hot_actual_approx": total_actual,
    }


def benchmark_routing(n: int = 10000) -> dict:
    """Benchmark routing metrics overhead."""
    metrics = RoutingMetrics()
    classifier = ComplexityClassifier()

    start = time.perf_counter()
    for i in range(n):
        # Simulate routing a request
        prompt = f"test prompt {i} with some complexity"
        tier = classifier.classify(prompt).tier
        metrics.record_routing(
            tier, latency_ms=1.0, confidence=0.9, success=True, reason="bench"
        )
    elapsed = time.perf_counter() - start

    summary = metrics.summary()

    return {
        "n_decisions": n,
        "total_time_s": round(elapsed, 4),
        "decisions_per_sec": round(n / elapsed, 0),
        "avg_overhead_us": round(elapsed / n * 1e6, 1),
        "total_routed": summary["total_routed"],
        "tier_distribution": {
            tier: stats["total_requests"]
            for tier, stats in summary.get("tiers", {}).items()
        },
    }


def benchmark_memory_analytics(n: int = 50000) -> dict:
    """Benchmark MemoryAnalytics throughput."""
    analytics = MemoryAnalytics(hll_precision=14, cms_width=4096, cms_depth=5)

    start = time.perf_counter()
    for i in range(n):
        tags = [f"tag_{i % 20}"]
        source = "bench" if i % 2 == 0 else "test"
        analytics.observe_memory(f"mem_{i}", tags=tags, source=source)
    elapsed = time.perf_counter() - start

    summary = analytics.summary()
    distinct_est = analytics.estimate_distinct_count()

    return {
        "n_observations": n,
        "total_time_s": round(elapsed, 4),
        "ops_per_sec": round(n / elapsed, 0),
        "memory_bytes": summary["memory_bytes"],
        "distinct_estimate": round(distinct_est, 0),
        "error_pct": round(abs(distinct_est - n) / n * 100, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inference acceleration benchmarks")
    parser.add_argument(
        "--size", type=int, default=256, help="Matrix dimension (m=k=size)"
    )
    parser.add_argument("--iterations", type=int, default=1000, help="GEMV iterations")
    parser.add_argument("--hll-n", type=int, default=10000, help="HLL item count")
    parser.add_argument("--cms-n", type=int, default=50000, help="CMS increment count")
    parser.add_argument(
        "--routing-n", type=int, default=10000, help="Routing decisions"
    )
    parser.add_argument(
        "--analytics-n", type=int, default=50000, help="Analytics observations"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("WhiteMagic Inference Acceleration Benchmarks")
    print("=" * 70)

    # 1. Ternary GEMV
    print(f"\n1. Ternary GEMV ({args.size}x{args.size}, {args.iterations} iterations)")
    print("-" * 50)
    py_result = benchmark_ternary_gemv_python(args.size, args.size, args.iterations)
    print(
        f"  Python scalar: {py_result['ops_per_sec']:>10,} ops/sec  "
        f"({py_result['avg_latency_us']:.1f} µs/op)"
    )

    rust_result = benchmark_ternary_gemv_rust(args.size, args.size, args.iterations)
    if rust_result:
        print(
            f"  Rust AVX2:     {rust_result['ops_per_sec']:>10,} ops/sec  "
            f"({rust_result['avg_latency_us']:.1f} µs/op)"
        )
        speedup = rust_result["ops_per_sec"] / py_result["ops_per_sec"]
        print(f"  Speedup:       {speedup:>10.1f}x")
    else:
        print("  Rust AVX2:     [not available — build with maturin develop]")

    # 2. HLL
    print(f"\n2. HyperLogLog ({args.hll_n} items, p=14)")
    print("-" * 50)
    hll_result = benchmark_hll(args.hll_n)
    print(
        f"  Estimate:      {hll_result['estimate']:>10,} (error: {hll_result['error_pct']:.2f}%)"
    )
    print(f"  Memory:        {hll_result['memory_bytes']:>10,} bytes")
    print(f"  Throughput:    {hll_result['ingest_ops_per_sec']:>10,} ops/sec")

    # 3. CMS
    print(f"\n3. Count-Min Sketch ({args.cms_n} increments)")
    print("-" * 50)
    cms_result = benchmark_cms(args.cms_n)
    print(f"  Memory:        {cms_result['memory_bytes']:>10,} bytes")
    print(f"  Throughput:    {cms_result['ingest_ops_per_sec']:>10,} ops/sec")
    print(
        f"  Hot key sample: {dict(list(cms_result['hot_key_estimates'].items())[:3])}"
    )

    # 4. Routing
    print(f"\n4. Routing Metrics ({args.routing_n} decisions)")
    print("-" * 50)
    routing_result = benchmark_routing(args.routing_n)
    print(f"  Throughput:    {routing_result['decisions_per_sec']:>10,} decisions/sec")
    print(f"  Overhead:      {routing_result['avg_overhead_us']:>10.1f} µs/decision")
    print(f"  Tier distribution: {routing_result['tier_distribution']}")

    # 5. Memory Analytics
    print(f"\n5. Memory Analytics ({args.analytics_n} observations)")
    print("-" * 50)
    analytics_result = benchmark_memory_analytics(args.analytics_n)
    print(f"  Throughput:    {analytics_result['ops_per_sec']:>10,} ops/sec")
    print(f"  Memory:        {analytics_result['memory_bytes']:>10,} bytes")
    print(
        f"  Distinct est:  {analytics_result['distinct_estimate']:>10,} "
        f"(error: {analytics_result['error_pct']:.2f}%)"
    )

    print("\n" + "=" * 70)
    print("Benchmarks complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
