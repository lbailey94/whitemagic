"""P6.3 — Retrieval stage instrumentation tests.

Tests that:
1. StageTelemetryCollector correctly aggregates per-stage timings
2. p50/p95/p99 percentiles are computed correctly
3. Degraded stages are tracked
4. Budget compliance is reported
5. Telemetry from SearchQueryPlanner can be collected
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

from benchmarks.stage_telemetry import (
    StageTelemetryCollector,
    StagePercentiles,
    TelemetryReport,
    _percentile,
)


class TestPercentileFunction:
    """Test the percentile helper."""

    def test_median_odd(self):
        assert _percentile([1, 2, 3, 4, 5], 50) == 3.0

    def test_median_even(self):
        assert _percentile([1, 2, 3, 4], 50) == 2.5

    def test_p95(self):
        values = list(range(1, 101))
        result = _percentile(values, 95)
        assert 94 <= result <= 96

    def test_p99(self):
        values = list(range(1, 101))
        result = _percentile(values, 99)
        assert 98 <= result <= 100

    def test_empty(self):
        assert _percentile([], 50) == 0.0

    def test_single_value(self):
        assert _percentile([42.0], 50) == 42.0


class TestStageTelemetryCollector:
    """Test the telemetry collector."""

    def test_record_dict_telemetry(self):
        collector = StageTelemetryCollector()
        collector.record({
            "total_duration_ms": 10.5,
            "within_budget": True,
            "stages": [
                {"stage": "lexical_ranking", "duration_ms": 2.0, "candidates_in": 0, "candidates_out": 30, "ok": True},
                {"stage": "semantic_ranking", "duration_ms": 5.0, "candidates_in": 30, "candidates_out": 20, "ok": True},
            ],
            "degraded_stages": [],
        })
        rpt = collector.report()
        assert rpt.total_queries == 1
        assert rpt.within_budget_count == 1
        assert "lexical_ranking" in rpt.stages
        assert "semantic_ranking" in rpt.stages

    def test_record_multiple_queries(self):
        collector = StageTelemetryCollector()
        for i in range(10):
            collector.record({
                "total_duration_ms": float(i + 1),
                "within_budget": i < 8,
                "stages": [
                    {"stage": "lexical_ranking", "duration_ms": float(i + 1) * 0.5, "candidates_out": 30, "ok": True},
                ],
                "degraded_stages": ["semantic_ranking"] if i % 3 == 0 else [],
            })
        rpt = collector.report()
        assert rpt.total_queries == 10
        assert rpt.within_budget_count == 8
        assert rpt.over_budget_count == 2
        assert rpt.degraded_stage_count.get("semantic_ranking") == 4

    def test_percentiles_computed(self):
        collector = StageTelemetryCollector()
        durations = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        for d in durations:
            collector.record({
                "total_duration_ms": d,
                "within_budget": True,
                "stages": [
                    {"stage": "test_stage", "duration_ms": d, "candidates_out": 10, "ok": True},
                ],
                "degraded_stages": [],
            })
        rpt = collector.report()
        stage = rpt.stages["test_stage"]
        assert stage.count == 10
        assert stage.p50_ms == pytest.approx(5.5, abs=0.5)
        assert stage.p95_ms == pytest.approx(10.0, abs=1.0)
        assert stage.mean_ms == 5.5

    def test_error_tracking(self):
        collector = StageTelemetryCollector()
        collector.record({
            "total_duration_ms": 5.0,
            "within_budget": True,
            "stages": [
                {"stage": "semantic_ranking", "duration_ms": 0.0, "candidates_out": 0, "ok": False, "error": "semantic_ranking"},
            ],
            "degraded_stages": ["semantic_ranking"],
        })
        rpt = collector.report()
        assert rpt.stages["semantic_ranking"].error_count == 1
        assert rpt.degraded_stage_count["semantic_ranking"] == 1

    def test_to_dict_serializable(self):
        collector = StageTelemetryCollector()
        collector.record({
            "total_duration_ms": 5.0,
            "within_budget": True,
            "stages": [
                {"stage": "lexical_ranking", "duration_ms": 2.0, "candidates_out": 30, "ok": True},
            ],
            "degraded_stages": [],
        })
        rpt = collector.report()
        d = rpt.to_dict()
        assert "total_queries" in d
        assert "stages" in d
        assert "total_duration_ms" in d
        assert isinstance(d["stages"], dict)

    def test_print_report_does_not_crash(self):
        collector = StageTelemetryCollector()
        collector.record({
            "total_duration_ms": 5.0,
            "within_budget": True,
            "stages": [
                {"stage": "lexical_ranking", "duration_ms": 2.0, "candidates_out": 30, "ok": True},
            ],
            "degraded_stages": [],
        })
        collector.print_report()


class TestRetrievalResultIntegration:
    """Test that RetrievalResult telemetry can be collected."""

    def test_retrieval_result_to_telemetry_dict(self):
        """RetrievalResult should produce collectible telemetry."""
        from whitemagic.core.memory.retrieval_plan import (
            RetrievalResult,
            RetrievalStage,
            StageTiming,
        )

        result = RetrievalResult(
            total_duration_ms=15.0,
            galaxies_searched=1,
            query_class="simple",
            degraded_stages=[],
        )
        result.stage_timings.append(StageTiming(
            stage=RetrievalStage.LEXICAL_RANKING,
            duration_ms=2.0,
            candidates_out=30,
        ))
        result.stage_timings.append(StageTiming(
            stage=RetrievalStage.SEMANTIC_RANKING,
            duration_ms=5.0,
            candidates_out=20,
        ))

        collector = StageTelemetryCollector()
        collector.record(result)
        rpt = collector.report()
        assert rpt.total_queries == 1
        assert "lexical_ranking" in rpt.stages
        assert "semantic_ranking" in rpt.stages
        assert rpt.stages["lexical_ranking"].p50_ms == 2.0

    def test_latency_budgets_defined(self):
        """Latency budgets should be defined for all query classes."""
        from whitemagic.core.memory.retrieval_plan import LATENCY_BUDGETS

        assert "simple" in LATENCY_BUDGETS
        assert "complex" in LATENCY_BUDGETS
        assert "federated" in LATENCY_BUDGETS
        assert "degraded" in LATENCY_BUDGETS

        for name, budget in LATENCY_BUDGETS.items():
            assert budget.p50 > 0
            assert budget.p95 >= budget.p50
            assert budget.p99 >= budget.p95
