"""P6.6 — Native acceleration decision gate tests.

Tests that:
1. All 8 required evidence fields are checked
2. Proposals with missing evidence are rejected
3. Complete proposals with good metrics are approved
4. FFI overhead threshold works
5. End-to-end speedup threshold works
6. Percentage of end-to-end threshold works
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

import time

import pytest

from benchmarks.acceleration_gate import (
    AccelerationProposal,
    GateDecision,
    evaluate_proposal,
    measure_python_baseline,
    print_decision,
)


def _make_complete_proposal(**overrides) -> AccelerationProposal:
    """Create a complete proposal that should pass all checks."""
    defaults = dict(
        name="test_accel",
        target_function="euclidean_distance",
        language="rust",
        profiler_trace="cProfile showing 15% in distance",
        pct_of_end_to_end=15.0,
        ffi_cost_estimate_ms=0.01,
        python_baseline_ms=0.5,
        native_microbenchmark_ms=0.03,
        integration_benchmark_with_ms=8.0,
        integration_benchmark_without_ms=12.0,
        fallback_behavior="Python loop fallback",
        maintenance_owner="core team",
    )
    defaults.update(overrides)
    return AccelerationProposal(**defaults)


class TestAccelerationProposal:
    """Test AccelerationProposal dataclass."""

    def test_speedup_factor(self):
        p = _make_complete_proposal()
        assert p.speedup_factor == pytest.approx(0.5 / 0.03, rel=0.01)

    def test_end_to_end_speedup(self):
        p = _make_complete_proposal()
        assert p.end_to_end_speedup == pytest.approx(12.0 / 8.0, rel=0.01)

    def test_ffi_overhead_pct(self):
        p = _make_complete_proposal()
        assert p.ffi_overhead_pct == pytest.approx((0.01 / 0.03) * 100, rel=0.1)

    def test_zero_speedup_when_no_native(self):
        p = AccelerationProposal(name="test", target_function="f", language="rust")
        assert p.speedup_factor == 0.0
        assert p.end_to_end_speedup == 0.0
        assert p.ffi_overhead_pct == 0.0


class TestGateDecision:
    """Test GateDecision structure."""

    def test_to_dict_serializable(self):
        p = _make_complete_proposal()
        d = evaluate_proposal(p)
        result = d.to_dict()
        assert "approved" in result
        assert "reason" in result
        assert "checks" in result
        assert "proposal" in result

    def test_print_decision_does_not_crash(self):
        p = _make_complete_proposal()
        d = evaluate_proposal(p)
        print_decision(d)


class TestEvaluateProposal:
    """Test the decision gate evaluation."""

    def test_complete_proposal_approved(self):
        """A complete proposal with good metrics should be approved."""
        p = _make_complete_proposal()
        d = evaluate_proposal(p)
        assert d.approved is True

    def test_missing_profiler_trace_rejected(self):
        p = _make_complete_proposal(profiler_trace="")
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["profiler_trace"] is False

    def test_low_pct_rejected(self):
        p = _make_complete_proposal(pct_of_end_to_end=2.0)
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["significant_pct"] is False

    def test_missing_ffi_cost_rejected(self):
        p = _make_complete_proposal(ffi_cost_estimate_ms=0.0)
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["ffi_cost_estimated"] is False

    def test_missing_python_baseline_rejected(self):
        p = _make_complete_proposal(python_baseline_ms=0.0)
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["python_baseline"] is False

    def test_missing_native_benchmark_rejected(self):
        p = _make_complete_proposal(native_microbenchmark_ms=0.0)
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["native_microbenchmark"] is False

    def test_missing_integration_benchmark_rejected(self):
        p = _make_complete_proposal(integration_benchmark_with_ms=0.0)
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["integration_benchmark"] is False

    def test_missing_fallback_rejected(self):
        p = _make_complete_proposal(fallback_behavior="")
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["fallback_behavior"] is False

    def test_missing_maintenance_owner_rejected(self):
        p = _make_complete_proposal(maintenance_owner="")
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["maintenance_owner"] is False

    def test_low_end_to_end_speedup_rejected(self):
        p = _make_complete_proposal(
            integration_benchmark_with_ms=11.5,
            integration_benchmark_without_ms=12.0,
        )
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["meaningful_speedup"] is False

    def test_high_ffi_overhead_rejected(self):
        p = _make_complete_proposal(
            ffi_cost_estimate_ms=0.05,
            native_microbenchmark_ms=0.03,
        )
        d = evaluate_proposal(p)
        assert d.approved is False
        assert d.checks["ffi_overhead_acceptable"] is False

    def test_all_checks_listed(self):
        """All 10 checks should be present in the decision."""
        p = _make_complete_proposal()
        d = evaluate_proposal(p)
        expected_checks = {
            "profiler_trace",
            "significant_pct",
            "ffi_cost_estimated",
            "python_baseline",
            "native_microbenchmark",
            "integration_benchmark",
            "fallback_behavior",
            "maintenance_owner",
            "meaningful_speedup",
            "ffi_overhead_acceptable",
        }
        assert set(d.checks.keys()) == expected_checks


class TestMeasurePythonBaseline:
    """Test the measurement utility."""

    def test_returns_float(self):
        def dummy():
            pass
        result = measure_python_baseline(dummy, iterations=5)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_slow_function_measured(self):
        def slow():
            time.sleep(0.001)
        result = measure_python_baseline(slow, iterations=3)
        assert result > 0.0
