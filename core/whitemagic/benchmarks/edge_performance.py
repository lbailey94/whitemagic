# ruff: noqa: BLE001
"""
Edge AI Performance Benchmarks.

Measures real-world performance of edge AI components:
- Inference latency
- Token savings
- Cache efficiency
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EdgePerformanceBenchmark:
    """Benchmark edge AI performance."""

    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

    def benchmark_inference(self, n: int = 100) -> dict[str, Any]:
        """Benchmark local inference latency."""
        from whitemagic.agentic.cpu_inference import CPUInferenceEngine
        engine = CPUInferenceEngine()

        start = time.monotonic()
        for _ in range(n):
            engine.infer("test query")
        elapsed = time.monotonic() - start

        result = {
            "test": "inference_latency",
            "iterations": n,
            "total_time_s": elapsed,
            "avg_latency_ms": (elapsed / n) * 1000,
        }
        self.results.append(result)
        return result

    def benchmark_cache(self, n: int = 100) -> dict[str, Any]:
        """Benchmark query cache efficiency."""
        from whitemagic.agentic.token_optimizer import QueryCache
        cache = QueryCache()

        # First pass: populate cache
        start = time.monotonic()
        for i in range(n):
            cache.set(f"query_{i}", f"result_{i}", 100)
        populate_time = time.monotonic() - start

        # Second pass: read from cache
        start = time.monotonic()
        for i in range(n):
            cache.get(f"query_{i}")
        read_time = time.monotonic() - start

        result = {
            "test": "cache_efficiency",
            "iterations": n,
            "populate_time_s": populate_time,
            "read_time_s": read_time,
            "avg_write_ms": (populate_time / n) * 1000,
            "avg_read_ms": (read_time / n) * 1000,
        }
        self.results.append(result)
        return result

    def run_all(self) -> list[dict[str, Any]]:
        """Run all benchmarks."""
        self.benchmark_inference(50)
        self.benchmark_cache(50)
        return self.results

    def summary(self) -> dict[str, Any]:
        return {"total_benchmarks": len(self.results)}


def run_edge_benchmark() -> list[dict[str, Any]]:
    """Convenience function to run edge benchmarks."""
    bench = EdgePerformanceBenchmark()
    return bench.run_all()
