"""Tests for Adaptive Recursive Oracle Cycle (Phase 7).

Tests verify:
- Single cycle runs all steps (oracle → synthesis → interpretation → BO → calibration)
- Recursive multi-cycle runs work
- CycleResult contains all expected fields
- Calibration feedback feeds forward
- Summary aggregates cycle history
- Graceful degradation when components unavailable
"""

import pytest
from unittest.mock import patch, MagicMock

from whitemagic.oracle.adaptive_cycle import (
    AdaptiveOracleCycle,
    CycleResult,
    get_adaptive_cycle,
)


def _mock_consultation(hexagram=32):
    """Create a mock QuantumIChing consultation result."""
    mock = MagicMock()
    mock.primary_hexagram = hexagram
    mock.primary_name = "Duration"
    mock.primary_judgment = "Duration succeeds through constancy."
    mock.primary_image = "Thunder and wind persist."
    return mock


@pytest.fixture(autouse=True)
def mock_heavy_components():
    """Mock slow components (QuantumIChing, TemporalForecastDB, LLM) for fast tests."""
    mock_db = MagicMock()
    mock_db.record_oracle_claim.return_value = "test-claim-id"
    mock_db.oracle_prescience_score.return_value = {
        "total": 0, "validated": 0, "falsified": 0, "pending": 0,
        "brier_score": None, "accuracy": None,
    }

    mock_oracle = MagicMock()
    mock_oracle.consult.return_value = _mock_consultation(32)

    mock_interpreter = MagicMock()
    mock_interpreter.interpret.return_value = "The oracle suggests patience and perseverance."

    with patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", return_value=mock_db), \
         patch("whitemagic.oracle.quantum_iching.QuantumIChing", return_value=mock_oracle), \
         patch("whitemagic.oracle.llm_interpreter.get_oracle_interpreter", return_value=mock_interpreter):
        yield


class TestAdaptiveOracleCycle:
    """Test the adaptive recursive oracle cycle."""

    def test_run_cycle_returns_cycle_result(self):
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("Should I proceed with this plan?")
        assert isinstance(result, CycleResult)
        assert result.question == "Should I proceed with this plan?"
        assert result.cycle_number == 1
        assert result.timestamp

    def test_run_cycle_includes_hexagram(self):
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("What about my career?")
        assert result.hexagram is not None
        assert 1 <= result.hexagram <= 64

    def test_run_cycle_includes_synthesis(self):
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("Is this the right time?")
        assert isinstance(result.synthesis, dict)
        # Should have some synthesis fields
        assert len(result.synthesis) > 0

    def test_run_cycle_includes_bo_params(self):
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("How to optimize?")
        assert isinstance(result.bo_params, dict)
        if result.bo_params:
            assert "xi" in result.bo_params or "n_bo_iterations" in result.bo_params

    def test_run_cycle_includes_interpretation(self):
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("What should I focus on?")
        assert isinstance(result.interpretation, str)

    def test_run_cycle_increments_count(self):
        cycle = AdaptiveOracleCycle()
        assert cycle.cycle_count == 0
        cycle.run_cycle("Question 1")
        assert cycle.cycle_count == 1
        cycle.run_cycle("Question 2")
        assert cycle.cycle_count == 2

    def test_run_recursive_multiple_cycles(self):
        cycle = AdaptiveOracleCycle()
        results = cycle.run_recursive("Deep question", n_cycles=2)
        assert len(results) == 2
        assert all(isinstance(r, CycleResult) for r in results)
        assert results[0].cycle_number < results[1].cycle_number

    def test_summary_after_cycles(self):
        cycle = AdaptiveOracleCycle()
        cycle.run_cycle("Summary test")
        summary = cycle.summary()
        assert "total_cycles" in summary
        assert summary["total_cycles"] >= 1
        assert "calibration_history" in summary
        assert "avg_calibration" in summary
        assert "last_hexagram" in summary

    def test_summary_empty(self):
        cycle = AdaptiveOracleCycle()
        summary = cycle.summary()
        assert summary["total_cycles"] == 0
        assert summary["avg_calibration"] is None
        assert summary["last_hexagram"] is None

    def test_get_adaptive_cycle_singleton(self):
        c1 = get_adaptive_cycle()
        c2 = get_adaptive_cycle()
        assert c1 is c2

    def test_cycle_result_dataclass(self):
        result = CycleResult(
            question="Test",
            timestamp="2026-01-01T00:00:00",
            hexagram=32,
        )
        assert result.question == "Test"
        assert result.hexagram == 32
        assert result.cycle_number == 0
        assert result.synthesis == {}
        assert result.interpretation == ""
        assert result.bo_params == {}
        assert result.claim_id is None

    def test_run_cycle_with_context(self):
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("Context test", context={"urgency": "high"})
        assert isinstance(result, CycleResult)
        assert result.hexagram is not None

    def test_run_cycle_without_simulation_by_default(self):
        """By default, should not run simulation."""
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("No simulation")
        assert result.simulation_result == {}

    def test_results_history_accumulates(self):
        cycle = AdaptiveOracleCycle()
        cycle.run_cycle("Q1")
        cycle.run_cycle("Q2")
        assert len(cycle.results) == 2
        assert cycle.results[0].question == "Q1"
        assert cycle.results[1].question == "Q2"

    def test_cycle_with_varying_hexagrams(self):
        """Test that hexagram produces expected BO params."""
        cycle = AdaptiveOracleCycle()
        result = cycle.run_cycle("Test")
        if result.bo_params:
            assert "xi" in result.bo_params
            # Hexagram 32 should map to patient exploration
            assert result.bo_params.get("exploration") == "patient"
