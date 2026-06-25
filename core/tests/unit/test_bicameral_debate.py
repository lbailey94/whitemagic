"""Tests for Objective O — Bicameral Improvement Debate."""
from __future__ import annotations

from whitemagic.core.evolution.bicameral_debate import BicameralDebate


class TestDebate:
    def test_basic_debate(self):
        debate = BicameralDebate()
        result = debate.debate(
            hypothesis_id="h1",
            predicted_impact=0.8,
            feasibility=0.7,
            risk=0.3,
        )
        assert result.hypothesis_id == "h1"
        assert 0 <= result.left_score <= 1
        assert 0 <= result.right_score <= 1

    def test_high_impact_left_wins(self):
        debate = BicameralDebate()
        result = debate.debate(
            hypothesis_id="h1",
            predicted_impact=0.9,
            feasibility=0.9,
            risk=0.1,
            historical_failure_rate=0.1,
            opportunity_cost=0.1,
        )
        assert result.left_score > result.right_score

    def test_high_risk_right_wins(self):
        debate = BicameralDebate()
        result = debate.debate(
            hypothesis_id="h1",
            predicted_impact=0.3,
            feasibility=0.3,
            risk=0.8,
            historical_failure_rate=0.7,
            opportunity_cost=0.6,
        )
        assert result.right_score > result.left_score

    def test_agreement_and_contention(self):
        debate = BicameralDebate()
        result = debate.debate("h1", predicted_impact=0.5, risk=0.5)
        assert abs(result.agreement + result.contention - 1.0) < 1e-6

    def test_convergence(self):
        debate = BicameralDebate()
        result = debate.debate("h1", predicted_impact=0.5, risk=0.5)
        assert result.convergence >= 0.0

    def test_net_score(self):
        debate = BicameralDebate()
        result = debate.debate("h1", predicted_impact=0.8, risk=0.2)
        assert 0 <= result.net_score <= 1.0


class TestExplorationBoost:
    def test_high_contention_boost(self):
        debate = BicameralDebate()
        # Create a high-contention scenario
        result = debate.debate(
            "h1",
            predicted_impact=0.8,
            feasibility=0.8,
            risk=0.7,
            historical_failure_rate=0.6,
        )
        boost = debate.get_exploration_boost("h1")
        if result.is_high_contention:
            assert boost > 0
        else:
            assert boost == 0.0

    def test_low_contention_no_boost(self):
        debate = BicameralDebate()
        debate.debate("h1", predicted_impact=0.9, risk=0.1, historical_failure_rate=0.1)
        boost = debate.get_exploration_boost("h1")
        # One side dominates → no boost
        assert boost == 0.0

    def test_nonexistent_debate(self):
        debate = BicameralDebate()
        assert debate.get_exploration_boost("h1") == 0.0


class TestCalibration:
    def test_record_validation(self):
        debate = BicameralDebate()
        debate.debate("h1", predicted_impact=0.7, risk=0.4)
        debate.record_validation("h1", skeptic_was_right=True)
        stats = debate.get_stats()
        assert stats["calibration_count"] == 1


class TestStats:
    def test_stats(self):
        debate = BicameralDebate()
        debate.debate("h1", predicted_impact=0.7, risk=0.3)
        debate.debate("h2", predicted_impact=0.5, risk=0.5)
        stats = debate.get_stats()
        assert stats["total_debates"] == 2
        assert "avg_contention" in stats
