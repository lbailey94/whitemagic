#!/usr/bin/env python3
"""Acceleration Benchmark — Python vs Zig SIMD vs Rust.

Measures latency and throughput for:
- Single cosine similarity (two vectors)
- Batch cosine (query vs corpus)
- Normalization

Outputs JSON to stdout and optionally writes to a file.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any


def _generate_vector(dim: int) -> list[float]:
    return [random.random() for _ in range(dim)]


def _generate_corpus(n: int, dim: int) -> list[list[float]]:
    return [_generate_vector(dim) for _ in range(n)]


def benchmark_py_cosine(dim: int, iterations: int = 1000) -> dict[str, float]:
    import math

    a = _generate_vector(dim)
    b = _generate_vector(dim)

    def py_cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        py_cosine(a, b)
        times.append(time.perf_counter() - start)

    return {
        "mean_ms": statistics.mean(times) * 1000,
        "p50_ms": statistics.median(times) * 1000,
        "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
    }


def benchmark_zig_cosine(dim: int, iterations: int = 1000) -> dict[str, float] | None:
    try:
        from whitemagic.core.acceleration.simd_cosine import cosine_similarity
    except ImportError:
        return None

    a = _generate_vector(dim)
    b = _generate_vector(dim)

    # Warmup
    cosine_similarity(a, b)

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        cosine_similarity(a, b)
        times.append(time.perf_counter() - start)

    return {
        "mean_ms": statistics.mean(times) * 1000,
        "p50_ms": statistics.median(times) * 1000,
        "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
    }


def benchmark_py_batch(
    dim: int, corpus_size: int, iterations: int = 100
) -> dict[str, float]:
    import math

    query = _generate_vector(dim)
    corpus = _generate_corpus(corpus_size, dim)

    def py_batch(query: list[float], corpus: list[list[float]]) -> list[float]:
        def _cos(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

        return [_cos(query, v) for v in corpus]

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        py_batch(query, corpus)
        times.append(time.perf_counter() - start)

    return {
        "mean_ms": statistics.mean(times) * 1000,
        "p50_ms": statistics.median(times) * 1000,
        "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        "throughput_vecs_per_sec": corpus_size / statistics.mean(times),
    }


def benchmark_zig_batch(
    dim: int, corpus_size: int, iterations: int = 100
) -> dict[str, float] | None:
    try:
        from whitemagic.core.acceleration.simd_cosine import batch_cosine
    except ImportError:
        return None

    query = _generate_vector(dim)
    corpus = _generate_corpus(corpus_size, dim)

    # Warmup
    batch_cosine(query, corpus)

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        batch_cosine(query, corpus)
        times.append(time.perf_counter() - start)

    return {
        "mean_ms": statistics.mean(times) * 1000,
        "p50_ms": statistics.median(times) * 1000,
        "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        "throughput_vecs_per_sec": corpus_size / statistics.mean(times),
    }


def main() -> dict[str, Any]:
    results: dict[str, Any] = {
        "version": "v22.2.0",
        "dimensions_tested": [128, 384, 768, 1536],
        "corpus_sizes_tested": [100, 1000, 5000],
        "single_cosine": {},
        "batch_cosine": {},
    }

    for dim in results["dimensions_tested"]:
        key = f"dim_{dim}"
        results["single_cosine"][key] = {
            "python": benchmark_py_cosine(dim, iterations=200),
            "zig_simd": benchmark_zig_cosine(dim, iterations=200),
        }

    for dim in [768, 1536]:
        for corpus in results["corpus_sizes_tested"]:
            key = f"dim_{dim}_corpus_{corpus}"
            results["batch_cosine"][key] = {
                "python": benchmark_py_batch(dim, corpus, iterations=20),
                "zig_simd": benchmark_zig_batch(dim, corpus, iterations=20),
            }

    # Print summary
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  WhiteMagic Acceleration Benchmark  —  v22.2.0               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    for dim in results["dimensions_tested"]:
        key = f"dim_{dim}"
        py = results["single_cosine"][key]["python"]
        zig = results["single_cosine"][key]["zig_simd"]
        print(f"Single cosine  —  dim={dim:4d}")
        print(f"  Python   mean={py['mean_ms']:.4f}ms  p95={py['p95_ms']:.4f}ms")
        if zig:
            speedup = py["mean_ms"] / zig["mean_ms"] if zig["mean_ms"] > 0 else 0
            print(
                f"  Zig SIMD mean={zig['mean_ms']:.4f}ms  p95={zig['p95_ms']:.4f}ms  ({speedup:.1f}×)"
            )
        else:
            print("  Zig SIMD — not available")
        print()

    for dim in [768, 1536]:
        for corpus in results["corpus_sizes_tested"]:
            key = f"dim_{dim}_corpus_{corpus}"
            py = results["batch_cosine"][key]["python"]
            zig = results["batch_cosine"][key]["zig_simd"]
            print(f"Batch cosine —  dim={dim:4d}  corpus={corpus:5d}")
            print(
                f"  Python   mean={py['mean_ms']:.2f}ms  throughput={py['throughput_vecs_per_sec']:,.0f} vec/s"
            )
            if zig:
                speedup = py["mean_ms"] / zig["mean_ms"] if zig["mean_ms"] > 0 else 0
                print(
                    f"  Zig SIMD mean={zig['mean_ms']:.2f}ms  throughput={zig['throughput_vecs_per_sec']:,.0f} vec/s  ({speedup:.1f}×)"
                )
            else:
                print("  Zig SIMD — not available")
            print()

    # Write JSON report
    report_dir = Path(__file__).resolve().parent.parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "benchmark_v22.json"
    report_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Full report written to: {report_path}")

    return results


if __name__ == "__main__":
    data = main()
    sys.exit(0)
