"""Tests for Objective L — Garden-Routed Improvement Evaluation."""

from __future__ import annotations

from whitemagic.core.evolution.garden_router import GardenRouter


class TestClassification:
    def test_refactor_is_courage(self):
        router = GardenRouter()
        assert router.classify("performance", "Refactor the memory module") == "courage"

    def test_doc_is_wisdom(self):
        router = GardenRouter()
        assert router.classify("quality", "Fix documentation naming") == "wisdom"

    def test_experiment_is_play(self):
        router = GardenRouter()
        assert router.classify("emergence", "Experimental novel approach") == "play"

    def test_debt_is_grief(self):
        router = GardenRouter()
        assert router.classify("codebase_quality", "Technical debt cleanup") == "grief"

    def test_research_is_mystery(self):
        router = GardenRouter()
        assert router.classify("gap", "Research unknown patterns") == "mystery"

    def test_default_by_category(self):
        router = GardenRouter()
        assert router.classify("quality", "") == "wisdom"
        assert router.classify("performance", "") == "courage"


class TestGardenPriors:
    def test_courage_high_variance(self):
        router = GardenRouter()
        mean, var = router.get_prior("courage")
        assert var > 0.15  # High variance

    def test_wisdom_low_variance(self):
        router = GardenRouter()
        mean, var = router.get_prior("wisdom")
        assert var < 0.1  # Low variance

    def test_confidence_threshold(self):
        router = GardenRouter()
        assert router.get_confidence_threshold(
            "courage"
        ) > router.get_confidence_threshold("wisdom")

    def test_mc_trial_multiplier(self):
        router = GardenRouter()
        assert router.get_mc_trial_multiplier(
            "mystery"
        ) > router.get_mc_trial_multiplier("wisdom")


class TestCalibration:
    def test_record_outcome(self):
        router = GardenRouter()
        brier = router.record_outcome("wisdom", predicted=0.8, actual=1.0)
        assert 0 <= brier <= 1.0

    def test_brier_decreases_with_accuracy(self):
        router = GardenRouter()
        # Perfect predictions
        for _ in range(10):
            router.record_outcome("wisdom", predicted=0.9, actual=0.9)
        cal = router.get_calibration("wisdom")
        assert cal.brier_score < 0.1


class TestPortfolioBalance:
    def test_balance(self):
        router = GardenRouter()
        hyps = [
            {"garden": "courage"},
            {"garden": "courage"},
            {"garden": "wisdom"},
            {"garden": "wisdom"},
            {"garden": "play"},
        ]
        balance = router.get_portfolio_balance(hyps)
        assert abs(balance["courage"] - 0.4) < 1e-6
        assert abs(balance["wisdom"] - 0.4) < 1e-6

    def test_targets_high_debt(self):
        router = GardenRouter()
        targets = router.get_portfolio_targets("high_debt")
        assert targets["grief"] > 0.5

    def test_targets_stagnation(self):
        router = GardenRouter()
        targets = router.get_portfolio_targets("stagnation")
        assert targets["play"] > 0.2 or targets["courage"] > 0.2

    def test_check_balance(self):
        router = GardenRouter()
        current = {
            "courage": 0.1,
            "wisdom": 0.7,
            "play": 0.1,
            "grief": 0.05,
            "mystery": 0.05,
        }
        targets = router.get_portfolio_targets("balanced")
        result = router.check_balance(current, targets)
        assert isinstance(result["balanced"], bool)
        assert isinstance(result["deficits"], dict)


class TestStats:
    def test_stats(self):
        router = GardenRouter()
        router.record_outcome("wisdom", 0.8, 1.0)
        stats = router.get_stats()
        assert "gardens" in stats
        assert stats["gardens"]["wisdom"]["outcome_count"] == 1
