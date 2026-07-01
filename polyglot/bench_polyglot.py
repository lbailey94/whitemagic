#!/usr/bin/env python3
"""Polyglot Holographic Memory Benchmark Harness.

Compares encode latency and nearest-neighbor throughput across
Julia, Elixir, and Haskell backends. Rust is excluded until the
bridge example is built.

Usage:
    python bench_polyglot.py [--texts N] [--queries N] [--k K]
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

POLYGLOT_BRIDGE = Path(__file__).parent / "bridges" / "python"
if str(POLYGLOT_BRIDGE) not in sys.path:
    sys.path.insert(0, str(POLYGLOT_BRIDGE))

import whitemagic_polyglot as wp

import logging
logger = logging.getLogger(__name__)


def bench_encode(backend, texts: list[str], warmup: int = 2) -> dict:
    """Benchmark encode latency."""
    # Warmup
    for t in texts[:warmup]:
        backend.call("encode", text=t)

    latencies = []
    for t in texts:
        t0 = time.perf_counter()
        backend.call("encode", text=t)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)  # ms

    return {
        "count": len(latencies),
        "mean_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(statistics.median(latencies), 3),
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "std_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0.0, 3),
        "throughput_hz": round(len(latencies) / sum(latencies) * 1000, 1),
    }


def bench_nearest_neighbors(backend, queries: list[str], texts: list[str], k: int, warmup: int = 2) -> dict:
    """Benchmark nearest-neighbor search latency."""
    # Warmup
    for q in queries[:warmup]:
        backend.call("nearest_neighbors", query=q, texts=texts, k=k)

    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        backend.call("nearest_neighbors", query=q, texts=texts, k=k)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    return {
        "count": len(latencies),
        "text_pool_size": len(texts),
        "k": k,
        "mean_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(statistics.median(latencies), 3),
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "std_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0.0, 3),
        "throughput_hz": round(len(latencies) / sum(latencies) * 1000, 1),
    }


def run_backend(name: str, cls, texts: list[str], queries: list[str], k: int) -> dict:
    logger.debug(f"\n{'='*60}")
    logger.debug("Backend: %s", name)
    logger.debug(f"{'='*60}")

    try:
        with cls() as backend:
            # Ping check
            ping = backend.call("ping")
            logger.debug("  Ping: %s", ping)

            # Encode benchmark
            logger.debug(f"\n  Encoding {len(texts)} texts...")
            encode_result = bench_encode(backend, texts)
            logger.debug(f"    mean={encode_result['mean_ms']}ms  median={encode_result['median_ms']}ms  throughput={encode_result['throughput_hz']}Hz")

            # NN benchmark
            logger.debug(f"\n  Nearest neighbors ({len(queries)} queries, pool={len(texts)}, k={k})...")
            nn_result = bench_nearest_neighbors(backend, queries, texts, k)
            logger.debug(f"    mean={nn_result['mean_ms']}ms  median={nn_result['median_ms']}ms  throughput={nn_result['throughput_hz']}Hz")

            return {
                "backend": name,
                "status": "ok",
                "encode": encode_result,
                "nearest_neighbors": nn_result,
            }
    except Exception as e:
        logger.debug("  FAILED: %s", e)
        return {"backend": name, "status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Polyglot holographic memory benchmark")
    parser.add_argument("--texts", type=int, default=100, help="Number of texts to encode")
    parser.add_argument("--queries", type=int, default=20, help="Number of NN queries")
    parser.add_argument("--k", type=int, default=5, help="K for nearest neighbors")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    logger.debug("WhiteMagic Polyglot Benchmark")
    logger.debug("  Texts: %s  Queries: %s  k: %s", args.texts, args.queries, args.k)

    # Generate deterministic test data
    texts = [f"benchmark text number {i} with some words to encode" for i in range(args.texts)]
    queries = [f"query text {i}" for i in range(args.queries)]

    # Auto-detect compiled Haskell binary for fair comparison
    hs_binary = Path(__file__).parent / "bridges" / "haskell" / "bridge"
    if hs_binary.exists():
        logger.debug("  Note: Using compiled Haskell binary for fair comparison")

    backends = [
        ("Julia", wp.JuliaBackend),
        ("Elixir", wp.ElixirBackend),
        ("Haskell", wp.HaskellBackend),
    ]

    results = []
    for name, cls in backends:
        result = run_backend(name, cls, texts, queries, args.k)
        results.append(result)

    summary = {
        "benchmark": "polyglot_holographic_memory",
        "config": {"texts": args.texts, "queries": args.queries, "k": args.k},
        "results": results,
    }

    if args.json:
        logger.debug(json.dumps(summary, indent=2))
    else:
        logger.debug("\n" + "=" * 60)
        logger.debug("SUMMARY")
        logger.debug("=" * 60)
        for r in results:
            if r["status"] == "ok":
                enc = r["encode"]
                nn = r["nearest_neighbors"]
                logger.debug(f"\n  {r['backend']}:")
                logger.debug(f"    Encode:  {enc['mean_ms']}ms mean, {enc['throughput_hz']}Hz")
                logger.debug(f"    NN:      {nn['mean_ms']}ms mean, {nn['throughput_hz']}Hz")
            else:
                logger.debug(f"\n  {r['backend']}: FAILED ({r.get('error', 'unknown')})")


if __name__ == "__main__":
    main()
