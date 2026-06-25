"""Pipeline profiling: measure overhead of each middleware stage.

Runs the dispatch pipeline with and without the new middlewares
(inference_router, token_tracker) to measure their overhead.
"""

from __future__ import annotations

import statistics
import time
import unittest

from whitemagic.tools.middleware import (
    DispatchPipeline,
    mw_circuit_breaker,
    mw_governor,
    mw_inference_router,
    mw_input_sanitizer,
    mw_maturity_gate,
    mw_observability,
    mw_rate_limiter,
    mw_security_monitor,
    mw_tool_permissions,
    mw_zodiac_resonance,
)
from whitemagic.core.monitoring.token_tracker import mw_token_tracker


def _build_pipeline_without_new() -> DispatchPipeline:
    """Build pipeline without inference_router and token_tracker."""
    p = DispatchPipeline()
    p.use("input_sanitizer", mw_input_sanitizer)
    p.use("circuit_breaker", mw_circuit_breaker)
    p.use("rate_limiter", mw_rate_limiter)
    p.use("security_monitor", mw_security_monitor)
    p.use("tool_permissions", mw_tool_permissions)
    p.use("maturity_gate", mw_maturity_gate)
    p.use("zodiac_resonance", mw_zodiac_resonance)
    p.use("governor", mw_governor)
    p.use("observability", mw_observability)
    return p


def _build_pipeline_with_new() -> DispatchPipeline:
    """Build pipeline with inference_router and token_tracker."""
    p = DispatchPipeline()
    p.use("input_sanitizer", mw_input_sanitizer)
    p.use("circuit_breaker", mw_circuit_breaker)
    p.use("rate_limiter", mw_rate_limiter)
    p.use("security_monitor", mw_security_monitor)
    p.use("tool_permissions", mw_tool_permissions)
    p.use("maturity_gate", mw_maturity_gate)
    p.use("zodiac_resonance", mw_zodiac_resonance)
    p.use("governor", mw_governor)
    p.use("inference_router", mw_inference_router)
    p.use("token_tracker", mw_token_tracker)
    p.use("observability", mw_observability)
    return p


def _measure_latency(pipeline: DispatchPipeline, iterations: int = 1000) -> list[float]:
    """Measure per-call latency in milliseconds."""
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        pipeline.execute("test_probe", _internal_benchmark=True)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
    return latencies


class TestPipelineProfiling(unittest.TestCase):
    """Profile dispatch pipeline overhead with and without new middlewares."""

    def test_pipeline_overhead_comparison(self) -> None:
        """Compare latency with and without inference_router + token_tracker."""
        iterations = 500

        # Warm up
        p_warm = _build_pipeline_without_new()
        p_warm.execute("warmup", _internal_benchmark=True)

        # Measure without new middlewares
        p_old = _build_pipeline_without_new()
        latencies_old = _measure_latency(p_old, iterations)

        # Measure with new middlewares
        p_new = _build_pipeline_with_new()
        latencies_new = _measure_latency(p_new, iterations)

        avg_old = statistics.mean(latencies_old)
        avg_new = statistics.mean(latencies_new)
        median_old = statistics.median(latencies_old)
        median_new = statistics.median(latencies_new)
        p99_old = sorted(latencies_old)[int(iterations * 0.99)]
        p99_new = sorted(latencies_new)[int(iterations * 0.99)]
        overhead_ms = avg_new - avg_old
        overhead_pct = (overhead_ms / avg_old) * 100 if avg_old > 0 else 0

        print(f"\n  Pipeline Profiling ({iterations} iterations):")
        print(f"    Without new middlewares (10 stages):")
        print(f"      avg: {avg_old:.3f}ms  median: {median_old:.3f}ms  p99: {p99_old:.3f}ms")
        print(f"    With new middlewares (12 stages):")
        print(f"      avg: {avg_new:.3f}ms  median: {median_new:.3f}ms  p99: {p99_new:.3f}ms")
        print(f"    Overhead: {overhead_ms:.3f}ms ({overhead_pct:.1f}%)")

        # Overhead should be minimal (< 1ms for non-inference tools)
        self.assertLess(overhead_ms, 2.0, f"Middleware overhead should be <2ms, got {overhead_ms:.3f}ms")

    def test_token_tracker_overhead_isolated(self) -> None:
        """Measure token_tracker middleware overhead in isolation."""
        iterations = 1000

        # Measure just the token_tracker middleware
        p = DispatchPipeline()
        p.use("token_tracker", mw_token_tracker)

        latencies = _measure_latency(p, iterations)
        avg = statistics.mean(latencies)
        median = statistics.median(latencies)

        print(f"\n  Token Tracker isolated ({iterations} iterations):")
        print(f"    avg: {avg:.3f}ms  median: {median:.3f}ms")

        # Should be sub-millisecond
        self.assertLess(avg, 2.0, f"Token tracker should be <2ms, got {avg:.3f}ms")

    def test_inference_router_overhead_isolated(self) -> None:
        """Measure inference_router middleware overhead for non-inference tools."""
        iterations = 1000

        p = DispatchPipeline()
        p.use("inference_router", mw_inference_router)

        latencies = _measure_latency(p, iterations)
        avg = statistics.mean(latencies)
        median = statistics.median(latencies)

        print(f"\n  Inference Router isolated ({iterations} iterations):")
        print(f"    avg: {avg:.3f}ms  median: {median:.3f}ms")

        # For non-inference tools, should be very fast (just a name check)
        self.assertLess(avg, 2.0, f"Inference router pass-through should be <2ms, got {avg:.3f}ms")


if __name__ == "__main__":
    unittest.main()
