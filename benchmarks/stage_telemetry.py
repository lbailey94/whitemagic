"""P6.3 — Retrieval stage telemetry aggregator.

Collects per-stage timing across multiple queries and computes
p50/p95/p99 percentiles for each stage, enabling latency budget
validation and stage-level bottleneck identification.

Usage:
    from benchmarks.stage_telemetry import StageTelemetryCollector

    collector = StageTelemetryCollector()
    for query in queries:
        results, telemetry = planner.execute(query=query, limit=10)
        collector.record(telemetry)

    report = collector.report()
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StagePercentiles:
    """Percentile timings for a single stage across many queries."""

    stage: str
    count: int = 0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    mean_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    error_count: int = 0
    candidates_in_mean: float = 0.0
    candidates_out_mean: float = 0.0


@dataclass
class TelemetryReport:
    """Aggregated telemetry report across all queries and stages."""

    total_queries: int = 0
    total_duration_p50_ms: float = 0.0
    total_duration_p95_ms: float = 0.0
    total_duration_p99_ms: float = 0.0
    total_duration_mean_ms: float = 0.0
    stages: dict[str, StagePercentiles] = field(default_factory=dict)
    degraded_stage_count: dict[str, int] = field(default_factory=dict)
    within_budget_count: int = 0
    over_budget_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "total_duration_ms": {
                "p50": round(self.total_duration_p50_ms, 2),
                "p95": round(self.total_duration_p95_ms, 2),
                "p99": round(self.total_duration_p99_ms, 2),
                "mean": round(self.total_duration_mean_ms, 2),
            },
            "stages": {
                name: {
                    "count": s.count,
                    "p50_ms": round(s.p50_ms, 2),
                    "p95_ms": round(s.p95_ms, 2),
                    "p99_ms": round(s.p99_ms, 2),
                    "mean_ms": round(s.mean_ms, 2),
                    "min_ms": round(s.min_ms, 2),
                    "max_ms": round(s.max_ms, 2),
                    "error_count": s.error_count,
                    "candidates_in_mean": round(s.candidates_in_mean, 1),
                    "candidates_out_mean": round(s.candidates_out_mean, 1),
                }
                for name, s in self.stages.items()
            },
            "degraded_stage_count": dict(self.degraded_stage_count),
            "within_budget_count": self.within_budget_count,
            "over_budget_count": self.over_budget_count,
        }


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute percentile from a sorted list."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    k = (n - 1) * pct / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


class StageTelemetryCollector:
    """Collects per-stage timing across multiple queries.

    Records RetrievalResult telemetry from SearchQueryPlanner.execute()
    and computes p50/p95/p99 percentiles per stage.
    """

    def __init__(self) -> None:
        self._stage_durations: dict[str, list[float]] = {}
        self._stage_candidates_in: dict[str, list[int]] = {}
        self._stage_candidates_out: dict[str, list[int]] = {}
        self._stage_errors: dict[str, int] = {}
        self._total_durations: list[float] = []
        self._degraded_counts: dict[str, int] = {}
        self._within_budget: int = 0
        self._over_budget: int = 0

    def record(self, telemetry: Any) -> None:
        """Record telemetry from a single query execution.

        Args:
            telemetry: A RetrievalResult object or its to_telemetry_dict() output.
        """
        # Accept either RetrievalResult or dict
        if hasattr(telemetry, "to_telemetry_dict"):
            data = telemetry.to_telemetry_dict()
        elif isinstance(telemetry, dict):
            data = telemetry
        else:
            return

        total_ms = data.get("total_duration_ms", 0.0)
        self._total_durations.append(total_ms)

        if data.get("within_budget", True):
            self._within_budget += 1
        else:
            self._over_budget += 1

        for stage in data.get("stages", []):
            stage_name = stage.get("stage", "unknown")
            duration = stage.get("duration_ms", 0.0)

            self._stage_durations.setdefault(stage_name, []).append(duration)
            self._stage_candidates_in.setdefault(stage_name, []).append(stage.get("candidates_in", 0))
            self._stage_candidates_out.setdefault(stage_name, []).append(stage.get("candidates_out", 0))

            if not stage.get("ok", True):
                self._stage_errors[stage_name] = self._stage_errors.get(stage_name, 0) + 1

        for degraded in data.get("degraded_stages", []):
            self._degraded_counts[degraded] = self._degraded_counts.get(degraded, 0) + 1

    def report(self) -> TelemetryReport:
        """Generate aggregated percentile report."""
        rpt = TelemetryReport()
        rpt.total_queries = len(self._total_durations)
        rpt.within_budget_count = self._within_budget
        rpt.over_budget_count = self._over_budget
        rpt.degraded_stage_count = dict(self._degraded_counts)

        if self._total_durations:
            sorted_totals = sorted(self._total_durations)
            rpt.total_duration_p50_ms = _percentile(sorted_totals, 50)
            rpt.total_duration_p95_ms = _percentile(sorted_totals, 95)
            rpt.total_duration_p99_ms = _percentile(sorted_totals, 99)
            rpt.total_duration_mean_ms = statistics.mean(self._total_durations)

        for stage_name, durations in self._stage_durations.items():
            sorted_durations = sorted(durations)
            sp = StagePercentiles(
                stage=stage_name,
                count=len(durations),
                p50_ms=_percentile(sorted_durations, 50),
                p95_ms=_percentile(sorted_durations, 95),
                p99_ms=_percentile(sorted_durations, 99),
                mean_ms=statistics.mean(durations),
                min_ms=min(durations),
                max_ms=max(durations),
                error_count=self._stage_errors.get(stage_name, 0),
                candidates_in_mean=statistics.mean(self._stage_candidates_in.get(stage_name, [0])),
                candidates_out_mean=statistics.mean(self._stage_candidates_out.get(stage_name, [0])),
            )
            rpt.stages[stage_name] = sp

        return rpt

    def print_report(self) -> None:
        """Print a formatted telemetry report."""
        rpt = self.report()
        print(f"\n{'=' * 70}")
        print(f"Stage Telemetry Report ({rpt.total_queries} queries)")
        print(f"{'=' * 70}")

        print(f"\nTotal duration: p50={rpt.total_duration_p50_ms:.1f}ms  "
              f"p95={rpt.total_duration_p95_ms:.1f}ms  "
              f"p99={rpt.total_duration_p99_ms:.1f}ms  "
              f"mean={rpt.total_duration_mean_ms:.1f}ms")
        print(f"Budget: {rpt.within_budget_count} within, {rpt.over_budget_count} over")

        if rpt.degraded_stage_count:
            print(f"\nDegraded stages: {rpt.degraded_stage_count}")

        print(f"\n{'Stage':<25} {'p50(ms)':>8} {'p95(ms)':>8} {'p99(ms)':>8} "
              f"{'mean(ms)':>9} {'errors':>7} {'cand_out':>9}")
        print("-" * 76)
        for stage_name, s in sorted(rpt.stages.items()):
            print(
                f"{stage_name:<25} "
                f"{s.p50_ms:>8.2f} "
                f"{s.p95_ms:>8.2f} "
                f"{s.p99_ms:>8.2f} "
                f"{s.mean_ms:>9.2f} "
                f"{s.error_count:>7} "
                f"{s.candidates_out_mean:>9.1f}"
            )
