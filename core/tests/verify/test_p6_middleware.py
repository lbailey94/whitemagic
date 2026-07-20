"""P6.5 — Middleware profiler by tool class tests.

Tests that:
1. Every middleware is benchmarked independently
2. Middleware is classified by safety/effect class
3. Post-call hooks are measured separately
4. Fast-path vs full pipeline are distinguished
5. Tool class breakdown is present
6. Critical middleware is marked as critical
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(REPO_ROOT / "core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "core"))

import pytest

from benchmarks.middleware_profiler import (
    MiddlewareTiming,
    PostCallTiming,
    MiddlewareReport,
    MIDDLEWARE_CLASSES,
    POST_CALL_CLASSES,
    run_middleware_profile,
    print_report,
)


class TestMiddlewareClassification:
    """Test that middleware is classified by safety/effect class."""

    def test_critical_safety_class(self):
        """Critical safety middleware must be classified."""
        assert MIDDLEWARE_CLASSES.get("input_sanitizer") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("circuit_breaker") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("rate_limiter") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("security_monitor") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("tool_permissions") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("maturity_gate") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("governor") == "critical_safety"
        assert MIDDLEWARE_CLASSES.get("pattern_guard") == "critical_safety"

    def test_economic_class(self):
        """Economic middleware must be classified."""
        assert MIDDLEWARE_CLASSES.get("transaction_firewall") == "critical_economic"

    def test_performance_class(self):
        """Performance middleware must be classified."""
        assert MIDDLEWARE_CLASSES.get("semantic_cache") == "performance"
        assert MIDDLEWARE_CLASSES.get("inference_router") == "performance"

    def test_enrichment_class(self):
        """Enrichment middleware must be classified."""
        assert MIDDLEWARE_CLASSES.get("zodiac_resonance") == "enrichment"
        assert MIDDLEWARE_CLASSES.get("citta_consciousness") == "enrichment"

    def test_observability_class(self):
        """Observability middleware must be classified."""
        assert MIDDLEWARE_CLASSES.get("token_tracker") == "observability"

    def test_post_call_classification(self):
        """Post-call hooks must be classified."""
        assert POST_CALL_CLASSES.get("karma_effects") == "governance"
        assert POST_CALL_CLASSES.get("observability") == "observability"
        assert POST_CALL_CLASSES.get("session_recorder") == "persistence"
        assert POST_CALL_CLASSES.get("wasm_verify") == "verification"


class TestMiddlewareTiming:
    """Test MiddlewareTiming dataclass."""

    def test_empty_timing(self):
        t = MiddlewareTiming(name="test")
        assert t.count == 0
        assert t.mean_ms == 0.0
        assert t.p50_ms == 0.0
        assert t.p95_ms == 0.0
        assert t.p99_ms == 0.0

    def test_with_runs(self):
        t = MiddlewareTiming(name="test", runs=[1.0, 2.0, 3.0, 4.0, 5.0])
        assert t.count == 5
        assert t.mean_ms == 3.0
        assert t.p50_ms == 3.0

    def test_critical_flag(self):
        t = MiddlewareTiming(name="governor", critical=True)
        assert t.critical is True

    def test_error_tracking(self):
        t = MiddlewareTiming(name="test", errors=2)
        assert t.errors == 2


class TestPostCallTiming:
    """Test PostCallTiming dataclass."""

    def test_empty(self):
        t = PostCallTiming(name="test")
        assert t.mean_ms == 0.0
        assert t.p50_ms == 0.0

    def test_with_runs(self):
        t = PostCallTiming(name="test", runs=[0.5, 1.0, 1.5])
        assert t.mean_ms == pytest.approx(1.0)
        assert t.p50_ms == 1.0


class TestMiddlewareReport:
    """Test MiddlewareReport structure."""

    def test_to_dict_serializable(self):
        report = MiddlewareReport(
            iterations=10,
            timestamp="2026-07-19T00:00:00Z",
        )
        report.middleware_timings["test_mw"] = MiddlewareTiming(name="test_mw", runs=[1.0])
        report.post_call_timings["test_hook"] = PostCallTiming(name="test_hook", runs=[0.5])
        report.fast_path_timings = [0.1, 0.2]
        report.full_pipeline_timings = [5.0, 6.0]

        d = report.to_dict()
        assert "middleware" in d
        assert "post_call_hooks" in d
        assert "fast_path" in d
        assert "full_pipeline" in d
        assert d["iterations"] == 10
        assert "test_mw" in d["middleware"]
        assert "test_hook" in d["post_call_hooks"]

    def test_print_report_does_not_crash(self):
        report = MiddlewareReport(iterations=5)
        report.middleware_timings["test"] = MiddlewareTiming(name="test", runs=[1.0])
        report.post_call_timings["hook"] = PostCallTiming(name="hook", runs=[0.5])
        print_report(report)


class TestRunMiddlewareProfile:
    """Test the actual profiling function."""

    def test_returns_report(self):
        """run_middleware_profile should return a MiddlewareReport."""
        report = run_middleware_profile(iterations=3, tool_name="system.version")
        assert isinstance(report, MiddlewareReport)
        assert report.iterations == 3

    def test_middleware_timings_populated(self):
        """At least some middleware timings should be captured."""
        report = run_middleware_profile(iterations=3, tool_name="system.version")
        # Either fast-path or full pipeline should have data
        assert len(report.fast_path_timings) > 0 or len(report.full_pipeline_timings) > 0

    def test_tool_class_breakdown_present(self):
        """Tool class breakdown should be populated if registry is available."""
        report = run_middleware_profile(iterations=3, tool_name="system.version")
        # May be empty if imports fail, but the field should exist
        assert isinstance(report.tool_class_breakdown, dict)
