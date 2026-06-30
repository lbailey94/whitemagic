#!/usr/bin/env python3
"""WhiteMagic Comprehensive Benchmark Suite — v22.2.0

Unifies acceleration, memory, and dispatch benchmarks into a single
report with cross-sectional insights.

Usage:
    source .venv/bin/activate && python core/scripts/benchmark_suite.py

Outputs:
    - Terminal summary with speedups and percentiles
    - JSON report to core/reports/benchmark_suite_v22.2.0.json
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _fmt_ms(v: float) -> str:
    return f"{v:.3f}ms"


def _fmt_speedup(py: float, acc: float | None) -> str:
    if acc is None or acc <= 0:
        return "N/A"
    return f"{py / acc:.1f}×"


def _summary(name: str, values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    return {
        "n": n,
        "min_ms": s[0] * 1000,
        "max_ms": s[-1] * 1000,
        "mean_ms": statistics.mean(s) * 1000,
        "p50_ms": s[int(n * 0.50)] * 1000,
        "p95_ms": s[int(n * 0.95)] * 1000,
        "p99_ms": s[int(n * 0.99)] * 1000,
        "stddev_ms": (statistics.stdev(s) * 1000 if n > 1 else 0.0),
    }


# ---------------------------------------------------------------------------
# 1. Cosine Similarity Benchmarks (Python vs Zig SIMD vs Rust)
# ---------------------------------------------------------------------------
def _generate_vector(dim: int) -> list[float]:
    return [random.random() for _ in range(dim)]


def benchmark_cosine(dim: int = 768, iterations: int = 500) -> dict[str, Any]:
    """Benchmark single cosine similarity across backends."""
    a = _generate_vector(dim)
    b = _generate_vector(dim)

    # Python scalar
    def py_cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    py_times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        py_cosine(a, b)
        py_times.append(time.perf_counter() - t0)

    # Zig SIMD
    zig_times: list[float] = []
    zig_available = False
    try:
        from whitemagic.core.acceleration.simd_cosine import cosine_similarity

        cosine_similarity(a, b)  # warmup
        for _ in range(iterations):
            t0 = time.perf_counter()
            cosine_similarity(a, b)
            zig_times.append(time.perf_counter() - t0)
        zig_available = True
    except ImportError:
        pass

    # Rust SIMD
    rust_times: list[float] = []
    rust_available = False
    try:
        from whitemagic.rust.optimization import simd_cosine_batch

        simd_cosine_batch([a], b)  # warmup
        for _ in range(iterations):
            t0 = time.perf_counter()
            simd_cosine_batch([a], b)
            rust_times.append(time.perf_counter() - t0)
        rust_available = True
    except ImportError:
        pass

    result: dict[str, Any] = {
        "dimension": dim,
        "iterations": iterations,
        "python": _summary("python", py_times),
    }
    if zig_available:
        result["zig_simd"] = _summary("zig", zig_times)
        result["zig_speedup"] = statistics.mean(py_times) / statistics.mean(zig_times)
    if rust_available:
        result["rust_simd"] = _summary("rust", rust_times)
        result["rust_speedup"] = statistics.mean(py_times) / statistics.mean(rust_times)
    return result


# ---------------------------------------------------------------------------
# 2. Batch Cosine Benchmark
# ---------------------------------------------------------------------------
def benchmark_batch_cosine(
    dim: int = 768, corpus_size: int = 1000, iterations: int = 50
) -> dict[str, Any]:
    """Benchmark batch cosine (query vs corpus)."""
    query = _generate_vector(dim)
    corpus = [_generate_vector(dim) for _ in range(corpus_size)]

    # Python batch
    def py_batch(query: list[float], corpus: list[list[float]]) -> list[float]:
        def _cos(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

        return [_cos(query, v) for v in corpus]

    py_times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        py_batch(query, corpus)
        py_times.append(time.perf_counter() - t0)

    # Zig batch
    zig_times: list[float] = []
    zig_available = False
    try:
        from whitemagic.core.acceleration.simd_cosine import batch_cosine

        batch_cosine(query, corpus)  # warmup
        for _ in range(iterations):
            t0 = time.perf_counter()
            batch_cosine(query, corpus)
            zig_times.append(time.perf_counter() - t0)
        zig_available = True
    except ImportError:
        pass

    result: dict[str, Any] = {
        "dimension": dim,
        "corpus_size": corpus_size,
        "iterations": iterations,
        "python": _summary("python", py_times),
    }
    if zig_available:
        result["zig_simd"] = _summary("zig", zig_times)
        result["zig_speedup"] = statistics.mean(py_times) / statistics.mean(zig_times)
    return result


# ---------------------------------------------------------------------------
# 3. Property-Based 5D Math Tests
# ---------------------------------------------------------------------------
def benchmark_5d_properties(iterations: int = 10_000) -> dict[str, Any]:
    """Property-based tests on holographic coordinate math."""
    errors: list[str] = []

    # Property 1: cosine(a, a) == 1.0
    prop1_pass = 0
    prop1_fail = 0
    for _ in range(iterations):
        v = _generate_vector(128)
        dot = sum(x * x for x in v)
        norm = math.sqrt(dot)
        cos_aa = dot / (norm * norm) if norm > 0 else 0.0
        if abs(cos_aa - 1.0) < 1e-6:
            prop1_pass += 1
        else:
            prop1_fail += 1
            if len(errors) < 3:
                errors.append(f"cosine(a,a) = {cos_aa:.6f} (expected 1.0)")

    # Property 2: cosine(a, b) == cosine(b, a)
    prop2_pass = 0
    prop2_fail = 0
    for _ in range(iterations):
        a = _generate_vector(128)
        b = _generate_vector(128)
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        cos_ab = dot / (na * nb) if na > 0 and nb > 0 else 0.0
        cos_ba = dot / (nb * na) if nb > 0 and na > 0 else 0.0
        if abs(cos_ab - cos_ba) < 1e-10:
            prop2_pass += 1
        else:
            prop2_fail += 1

    # Property 3: cosine angular distance respects the triangle inequality.
    # We measure d(a,b) = arccos(clamp(cos(a,b))) on three sampled vectors
    # and assert d(a,c) <= d(a,b) + d(b,c) (with a small numerical tolerance).
    def _angular_distance(u: list[float], v: list[float]) -> float:
        dot = sum(x * y for x, y in zip(u, v))
        nu = math.sqrt(sum(x * x for x in u))
        nv = math.sqrt(sum(x * x for x in v))
        if nu == 0 or nv == 0:
            return 0.0
        cos = max(-1.0, min(1.0, dot / (nu * nv)))
        return math.acos(cos)

    prop3_pass = 0
    prop3_fail = 0
    for _ in range(iterations):
        a = _generate_vector(64)
        b = _generate_vector(64)
        c = _generate_vector(64)
        d_ab = _angular_distance(a, b)
        d_bc = _angular_distance(b, c)
        d_ac = _angular_distance(a, c)
        if d_ac <= d_ab + d_bc + 1e-9:
            prop3_pass += 1
        else:
            prop3_fail += 1
            if len(errors) < 3:
                errors.append(
                    f"triangle violated: d_ac={d_ac:.6f} > d_ab+d_bc={d_ab + d_bc:.6f}"
                )

    return {
        "iterations": iterations,
        "cosine_idempotent": {
            "pass": prop1_pass,
            "fail": prop1_fail,
            "rate": prop1_pass / iterations,
        },
        "cosine_symmetric": {
            "pass": prop2_pass,
            "fail": prop2_fail,
            "rate": prop2_pass / iterations,
        },
        "triangle_inequality": {
            "pass": prop3_pass,
            "fail": prop3_fail,
            "rate": prop3_pass / iterations,
        },
        "errors": errors,
        "all_pass": prop1_fail == 0 and prop2_fail == 0 and prop3_fail == 0,
    }


# ---------------------------------------------------------------------------
# 4. Dispatch Pipeline Benchmark
# ---------------------------------------------------------------------------
def benchmark_dispatch(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark tool dispatch latency for read-only tools.

    Note: ``call_tool`` takes keyword arguments (``call_tool(name, **kwargs)``),
    not a positional dict. We also count successes vs errors so a "fast"
    benchmark that's just failing loudly cannot masquerade as low latency.
    """
    try:
        from whitemagic.tools.unified_api import call_tool
    except ImportError:
        return {"error": "unified_api not available"}

    def _bench(name: str, **kwargs: Any) -> tuple[list[float], int, int]:
        times: list[float] = []
        ok_count = 0
        err_count = 0
        last_error: str | None = None
        # Warmup
        try:
            call_tool(name, **kwargs)
        except Exception:  # noqa: BLE001 - benchmark, root cause logged below
            pass
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                resp = call_tool(name, **kwargs)
                times.append(time.perf_counter() - t0)
                # Treat envelope-error as failure for benchmark accounting
                if isinstance(resp, dict) and resp.get("status") == "success":
                    ok_count += 1
                else:
                    err_count += 1
                    if last_error is None and isinstance(resp, dict):
                        last_error = str(
                            resp.get("error_code") or resp.get("error") or ""
                        )
            except Exception as e:  # noqa: BLE001 - capture for transparency
                times.append(time.perf_counter() - t0)
                err_count += 1
                if last_error is None:
                    last_error = f"{type(e).__name__}: {e}"
        return times, ok_count, err_count

    gnosis_times, gnosis_ok, gnosis_err = _bench("gnosis", action="status")
    health_times, health_ok, health_err = _bench("health_report")

    return {
        "iterations": iterations,
        "gnosis_status": {
            **_summary("gnosis", gnosis_times),
            "ok": gnosis_ok,
            "err": gnosis_err,
        },
        "health_report": {
            **_summary("health", health_times),
            "ok": health_ok,
            "err": health_err,
        },
    }


# ---------------------------------------------------------------------------
# 5. PRAT Compression Benchmark Scaffolding
# ---------------------------------------------------------------------------
def benchmark_prat_compression() -> dict[str, Any]:
    """Measure PRAT layer overhead: tools described vs tokens saved.

    This is scaffolding for the full benchmark Opus 4.7 recommended.
    Full implementation requires a fixed task gold set.
    """
    try:
        from whitemagic.tools.prat_mappings import (
            GANA_TO_TOOLS,  # type: ignore[import-not-found]
        )
        from whitemagic.tools.tool_surface import get_surface_counts

        counts = get_surface_counts()
        total_tools = counts.get("callable_tools", 0)
        gana_count = len(GANA_TO_TOOLS)
        avg_tools_per_gana = (
            sum(len(t) for t in GANA_TO_TOOLS.values()) / gana_count
            if gana_count > 0
            else 0
        )

        # Estimate token savings (heuristic: ~50 tokens/tool description)
        tokens_flat = total_tools * 50
        tokens_prat = gana_count * 80 + avg_tools_per_gana * gana_count * 20
        estimated_savings = tokens_flat - tokens_prat

        return {
            "status": "scaffold",
            "total_tools": total_tools,
            "gana_count": gana_count,
            "avg_tools_per_gana": round(avg_tools_per_gana, 1),
            "estimated_tokens_flat": tokens_flat,
            "estimated_tokens_prat": int(tokens_prat),
            "estimated_token_savings": int(estimated_savings),
            "estimated_savings_pct": round(estimated_savings / tokens_flat * 100, 1)
            if tokens_flat > 0
            else 0,
            "note": "Full benchmark requires gold task set (see Opus 4.7 review)",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 65)
    print(" WhiteMagic Comprehensive Benchmark Suite — v22.2.0")
    print("=" * 65)

    from whitemagic.utils.progress_bar import ProgressBar

    results: dict[str, Any] = {
        "version": "v22.2.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    phases = [
        (
            "Cosine Similarity",
            "[1/5] Cosine Similarity (dim=768, n=500)...",
            lambda: benchmark_cosine(dim=768, iterations=500),
        ),
        (
            "Batch Cosine",
            "[2/5] Batch Cosine (dim=768, corpus=1000, n=50)...",
            lambda: benchmark_batch_cosine(dim=768, corpus_size=1000, iterations=50),
        ),
        (
            "5D Properties",
            "[3/5] Property-Based 5D Math (n=10,000)...",
            lambda: benchmark_5d_properties(iterations=10_000),
        ),
        (
            "Dispatch",
            "[4/5] Dispatch Pipeline (n=8, per-tool)...",
            lambda: benchmark_dispatch(iterations=8),
        ),
        (
            "PRAT Scaffold",
            "[5/5] PRAT Compression Scaffold...",
            lambda: benchmark_prat_compression(),
        ),
    ]

    bar = ProgressBar(total=len(phases), label="Suite")
    bar.start()

    for i, (label, header, fn) in enumerate(phases):
        bar.set_label(label)
        print(f"\n{header}")
        results_key = [
            "cosine",
            "batch_cosine",
            "5d_properties",
            "dispatch",
            "prat_compression",
        ][i]
        results[results_key] = fn()
        bar.advance()

    bar.finish()

    # Write report
    report_dir = REPO_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "benchmark_suite_v22.2.0.json"
    report_path.write_text(json.dumps(results, indent=2) + "\n")

    print("\n" + "=" * 65)
    print(f" Report: {report_path}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
