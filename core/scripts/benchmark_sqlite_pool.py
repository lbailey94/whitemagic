#!/usr/bin/env python3
"""Benchmark: SQLite Connection Pool vs Open/Close per Query.

Measures the performance improvement from using persistent connection
pooling instead of opening/closing a new connection for every query.

Usage:
    python core/scripts/benchmark_sqlite_pool.py
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from whitemagic.config.paths import DB_PATH, ensure_paths
from whitemagic.core.memory.db_manager import ConnectionPool

QUERIES = [
    ("SELECT COUNT(*) FROM memories", ()),
    ("SELECT id, title, content FROM memories ORDER BY importance DESC LIMIT 10", ()),
    ("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type", ()),
    ("SELECT id FROM memories WHERE importance > 0.5 LIMIT 20", ()),
    ("SELECT id, importance, galactic_distance FROM memories ORDER BY created_at DESC LIMIT 50", ()),
]

ITERATIONS = 100


def benchmark_open_close(db_path: str, iterations: int) -> dict:
    """Benchmark: open/close connection for every query."""
    times = []
    for i in range(iterations):
        query, params = QUERIES[i % len(QUERIES)]
        start = time.perf_counter_ns()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA mmap_size=268435456")
        conn.execute("PRAGMA cache_size=-65536")
        conn.execute("PRAGMA temp_store=MEMORY")
        result = conn.execute(query, params).fetchall()
        conn.close()
        elapsed = (time.perf_counter_ns() - start) / 1_000_000  # ms
        times.append(elapsed)

    return {
        "mean_ms": sum(times) / len(times),
        "median_ms": sorted(times)[len(times) // 2],
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "total_ms": sum(times),
    }


def benchmark_pool(db_path: str, iterations: int) -> dict:
    """Benchmark: use persistent connection pool."""
    pool = ConnectionPool(db_path, max_connections=10)
    times = []
    for i in range(iterations):
        query, params = QUERIES[i % len(QUERIES)]
        start = time.perf_counter_ns()
        with pool.connection() as conn:
            result = conn.execute(query, params).fetchall()
        elapsed = (time.perf_counter_ns() - start) / 1_000_000  # ms
        times.append(elapsed)
    pool.close_all()

    return {
        "mean_ms": sum(times) / len(times),
        "median_ms": sorted(times)[len(times) // 2],
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "total_ms": sum(times),
    }


def main():
    ensure_paths()
    db_path = DB_PATH

    print("=" * 60)
    print("SQLite Connection Pool Benchmark")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Iterations: {ITERATIONS}")
    print(f"Queries: {len(QUERIES)} (rotating)")
    print()

    # Warm up
    print("Warming up...")
    conn = sqlite3.connect(db_path)
    conn.execute("SELECT 1").fetchone()
    conn.close()

    # Benchmark open/close
    print("\n[1/2] Benchmarking open/close per query...")
    open_close = benchmark_open_close(db_path, ITERATIONS)

    # Benchmark pool
    print("[2/2] Benchmarking persistent connection pool...")
    pool = benchmark_pool(db_path, ITERATIONS)

    # Results
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\n{'Metric':<20} {'Open/Close':>12} {'Pool':>12} {'Speedup':>10}")
    print("-" * 60)
    print(f"{'Mean (ms)':<20} {open_close['mean_ms']:>12.3f} {pool['mean_ms']:>12.3f} {open_close['mean_ms']/pool['mean_ms']:>10.1f}x")
    print(f"{'Median (ms)':<20} {open_close['median_ms']:>12.3f} {pool['median_ms']:>12.3f} {open_close['median_ms']/pool['median_ms']:>10.1f}x")
    print(f"{'Min (ms)':<20} {open_close['min_ms']:>12.3f} {pool['min_ms']:>12.3f} {open_close['min_ms']/pool['min_ms']:>10.1f}x")
    print(f"{'Max (ms)':<20} {open_close['max_ms']:>12.3f} {pool['max_ms']:>12.3f} {open_close['max_ms']/pool['max_ms']:>10.1f}x")
    print(f"{'P95 (ms)':<20} {open_close['p95_ms']:>12.3f} {pool['p95_ms']:>12.3f} {open_close['p95_ms']/pool['p95_ms']:>10.1f}x")
    print(f"{'Total (ms)':<20} {open_close['total_ms']:>12.3f} {pool['total_ms']:>12.3f} {open_close['total_ms']/pool['total_ms']:>10.1f}x")

    improvement = (1 - pool['total_ms'] / open_close['total_ms']) * 100
    print(f"\nOverall improvement: {improvement:.1f}%")
    print(f"Time saved: {open_close['total_ms'] - pool['total_ms']:.1f}ms over {ITERATIONS} queries")

    if improvement > 0:
        print(f"\n✅ Connection pool is {open_close['total_ms']/pool['total_ms']:.1f}x faster than open/close")
    else:
        print(f"\n⚠️ No significant improvement (pool overhead may dominate for fast queries)")


if __name__ == "__main__":
    main()
