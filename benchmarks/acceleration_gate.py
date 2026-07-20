"""P6.6 — Native acceleration decision gate.

Before adding Rust/Zig/Koka acceleration, require:
1. Profiler trace showing the bottleneck
2. Percentage of end-to-end time
3. FFI cost estimate
4. Python baseline measurement
5. Native microbenchmark
6. Integration benchmark (end-to-end with and without)
7. Fallback behavior verification
8. Maintenance owner assignment

This module provides the decision gate framework and evaluation tooling.

Usage:
    from benchmarks.acceleration_gate import AccelerationProposal, evaluate_proposal
    result = evaluate_proposal(proposal)
"""

from __future__ import annotations

import gc
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class AccelerationProposal:
    """A proposal to add native acceleration for a hot path.

    All fields must be filled before evaluation. The decision gate
    will reject proposals with missing evidence.
    """

    name: str
    target_function: str
    language: str  # "rust", "zig", "koka"
    profiler_trace: str = ""  # Path or description of profiler output
    pct_of_end_to_end: float = 0.0  # % of total runtime this function consumes
    ffi_cost_estimate_ms: float = 0.0  # Estimated FFI overhead per call
    python_baseline_ms: float = 0.0  # Measured Python baseline
    native_microbenchmark_ms: float = 0.0  # Measured native speed
    integration_benchmark_with_ms: float = 0.0  # End-to-end with native
    integration_benchmark_without_ms: float = 0.0  # End-to-end without native
    fallback_behavior: str = ""  # Description of fallback when native unavailable
    maintenance_owner: str = ""  # Who maintains the native code
    notes: str = ""

    @property
    def speedup_factor(self) -> float:
        """Raw microbenchmark speedup (Python / Native)."""
        if self.native_microbenchmark_ms <= 0:
            return 0.0
        return self.python_baseline_ms / self.native_microbenchmark_ms

    @property
    def end_to_end_speedup(self) -> float:
        """End-to-end speedup (without / with native)."""
        if self.integration_benchmark_with_ms <= 0:
            return 0.0
        return self.integration_benchmark_without_ms / self.integration_benchmark_with_ms

    @property
    def ffi_overhead_pct(self) -> float:
        """FFI overhead as % of native execution time."""
        if self.native_microbenchmark_ms <= 0:
            return 0.0
        return (self.ffi_cost_estimate_ms / self.native_microbenchmark_ms) * 100


@dataclass
class GateDecision:
    """Decision from the acceleration gate."""

    approved: bool
    reason: str
    proposal: AccelerationProposal | None = None
    checks: dict[str, bool] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "checks": self.checks,
            "recommendations": self.recommendations,
            "proposal": {
                "name": self.proposal.name if self.proposal else "",
                "target_function": self.proposal.target_function if self.proposal else "",
                "language": self.proposal.language if self.proposal else "",
                "speedup_factor": self.proposal.speedup_factor if self.proposal else 0,
                "end_to_end_speedup": self.proposal.end_to_end_speedup if self.proposal else 0,
                "ffi_overhead_pct": self.proposal.ffi_overhead_pct if self.proposal else 0,
                "pct_of_end_to_end": self.proposal.pct_of_end_to_end if self.proposal else 0,
            } if self.proposal else {},
        }


def evaluate_proposal(proposal: AccelerationProposal) -> GateDecision:
    """Evaluate an acceleration proposal against the decision gate.

    Returns a GateDecision with approval status and recommendations.
    """
    checks: dict[str, bool] = {}
    recommendations: list[str] = []

    # Check 1: Profiler trace provided
    checks["profiler_trace"] = bool(proposal.profiler_trace)
    if not checks["profiler_trace"]:
        recommendations.append("Provide a profiler trace (cProfile/py-spy) showing the bottleneck.")

    # Check 2: Percentage of end-to-end time
    checks["significant_pct"] = proposal.pct_of_end_to_end >= 5.0
    if not checks["significant_pct"]:
        recommendations.append(
            f"Target function is only {proposal.pct_of_end_to_end:.1f}% of end-to-end time. "
            f"Need ≥5% to justify native acceleration."
        )

    # Check 3: FFI cost estimated
    checks["ffi_cost_estimated"] = proposal.ffi_cost_estimate_ms > 0
    if not checks["ffi_cost_estimated"]:
        recommendations.append("Estimate FFI overhead (PyO3/cffi call cost per invocation).")

    # Check 4: Python baseline measured
    checks["python_baseline"] = proposal.python_baseline_ms > 0
    if not checks["python_baseline"]:
        recommendations.append("Measure Python baseline performance for the target function.")

    # Check 5: Native microbenchmark
    checks["native_microbenchmark"] = proposal.native_microbenchmark_ms > 0
    if not checks["native_microbenchmark"]:
        recommendations.append("Provide native microbenchmark measurement.")

    # Check 6: Integration benchmark (both with and without)
    checks["integration_benchmark"] = (
        proposal.integration_benchmark_with_ms > 0
        and proposal.integration_benchmark_without_ms > 0
    )
    if not checks["integration_benchmark"]:
        recommendations.append("Provide integration benchmarks both with and without native acceleration.")

    # Check 7: Fallback behavior described
    checks["fallback_behavior"] = bool(proposal.fallback_behavior)
    if not checks["fallback_behavior"]:
        recommendations.append("Describe fallback behavior when native module is unavailable.")

    # Check 8: Maintenance owner assigned
    checks["maintenance_owner"] = bool(proposal.maintenance_owner)
    if not checks["maintenance_owner"]:
        recommendations.append("Assign a maintenance owner for the native code.")

    # Check 9: End-to-end speedup is meaningful (>1.1x)
    checks["meaningful_speedup"] = proposal.end_to_end_speedup >= 1.1
    if not checks["meaningful_speedup"] and proposal.integration_benchmark_with_ms > 0:
        recommendations.append(
            f"End-to-end speedup is only {proposal.end_to_end_speedup:.2f}x. "
            f"Need ≥1.1x to justify maintenance burden."
        )

    # Check 10: FFI overhead is not dominant (<50% of native time)
    checks["ffi_overhead_acceptable"] = proposal.ffi_overhead_pct < 50.0
    if not checks["ffi_overhead_acceptable"] and proposal.native_microbenchmark_ms > 0:
        recommendations.append(
            f"FFI overhead is {proposal.ffi_overhead_pct:.1f}% of native execution time. "
            f"Consider batching calls or keeping the hot path in Python."
        )

    all_passed = all(checks.values())
    approved = all_passed

    if approved:
        reason = (
            f"Approved: {proposal.speedup_factor:.1f}x microbenchmark speedup, "
            f"{proposal.end_to_end_speedup:.2f}x end-to-end, "
            f"FFI overhead {proposal.ffi_overhead_pct:.1f}%, "
            f"{proposal.pct_of_end_to_end:.1f}% of end-to-end time."
        )
    else:
        failed = [k for k, v in checks.items() if not v]
        reason = f"Rejected: {len(failed)} check(s) failed: {', '.join(failed)}"

    return GateDecision(
        approved=approved,
        reason=reason,
        proposal=proposal,
        checks=checks,
        recommendations=recommendations,
    )


def measure_python_baseline(
    fn: Any,
    args: tuple = (),
    kwargs: dict | None = None,
    iterations: int = 100,
) -> float:
    """Measure Python baseline for a function.

    Returns mean execution time in milliseconds.
    """
    if kwargs is None:
        kwargs = {}

    timings: list[float] = []
    for _ in range(iterations):
        gc.collect()
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        timings.append(elapsed)

    return statistics.mean(timings)


def measure_end_to_end(
    fn: Any,
    args: tuple = (),
    kwargs: dict | None = None,
    iterations: int = 50,
) -> float:
    """Measure end-to-end latency for a function (including all overhead).

    Returns mean execution time in milliseconds.
    """
    if kwargs is None:
        kwargs = {}

    timings: list[float] = []
    for _ in range(iterations):
        gc.collect()
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        timings.append(elapsed)

    return statistics.mean(timings)


def print_decision(decision: GateDecision) -> None:
    """Print a formatted decision report."""
    p = decision.proposal
    print(f"\n{'=' * 70}")
    print(f"Acceleration Gate: {p.name if p else 'N/A'}")
    print(f"{'=' * 70}")
    print(f"\nStatus: {'APPROVED' if decision.approved else 'REJECTED'}")
    print(f"Reason: {decision.reason}")

    print(f"\n{'Check':<35} {'Status':>8}")
    print("-" * 45)
    for check, passed in decision.checks.items():
        print(f"{check:<35} {'PASS' if passed else 'FAIL':>8}")

    if p:
        print(f"\nMetrics:")
        print(f"  Language:              {p.language}")
        print(f"  Target function:       {p.target_function}")
        print(f"  % of end-to-end:       {p.pct_of_end_to_end:.1f}%")
        print(f"  Python baseline:       {p.python_baseline_ms:.3f}ms")
        print(f"  Native microbenchmark: {p.native_microbenchmark_ms:.3f}ms")
        print(f"  Speedup factor:        {p.speedup_factor:.2f}x")
        print(f"  FFI cost:              {p.ffi_cost_estimate_ms:.3f}ms ({p.ffi_overhead_pct:.1f}%)")
        print(f"  E2E with native:       {p.integration_benchmark_with_ms:.3f}ms")
        print(f"  E2E without native:    {p.integration_benchmark_without_ms:.3f}ms")
        print(f"  E2E speedup:           {p.end_to_end_speedup:.2f}x")
        print(f"  Fallback:              {p.fallback_behavior}")
        print(f"  Maintenance owner:     {p.maintenance_owner}")

    if decision.recommendations:
        print(f"\nRecommendations:")
        for r in decision.recommendations:
            print(f"  - {r}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Native acceleration decision gate")
    parser.add_argument("--proposal", "-p", default=None, help="Path to proposal JSON file")
    args = parser.parse_args()

    if args.proposal:
        data = json.loads(Path(args.proposal).read_text())
        proposal = AccelerationProposal(**data)
    else:
        # Example proposal
        proposal = AccelerationProposal(
            name="example",
            target_function="euclidean_distance",
            language="rust",
            profiler_trace="cProfile output showing 15% of time in distance computation",
            pct_of_end_to_end=15.0,
            ffi_cost_estimate_ms=0.01,
            python_baseline_ms=0.5,
            native_microbenchmark_ms=0.03,
            integration_benchmark_with_ms=8.0,
            integration_benchmark_without_ms=12.0,
            fallback_behavior="Python loop fallback when Rust module unavailable",
            maintenance_owner="core team",
        )

    decision = evaluate_proposal(proposal)
    print_decision(decision)


if __name__ == "__main__":
    main()
