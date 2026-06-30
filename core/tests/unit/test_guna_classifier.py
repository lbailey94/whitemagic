"""Tests for Objective V — Guna-Based Improvement Classification."""

from __future__ import annotations

from whitemagic.core.evolution.guna_classifier import (
    Guna,
    GunaClassifier,
    GunaPortfolio,
)


class TestClassification:
    def test_sattvic(self):
        clf = GunaClassifier()
        assert clf.classify("quality", "Fix documentation naming") == Guna.SATTVIC

    def test_rajasic(self):
        clf = GunaClassifier()
        assert clf.classify("performance", "New feature acceleration") == Guna.RAJASIC

    def test_tamasic(self):
        clf = GunaClassifier()
        assert (
            clf.classify("codebase_quality", "Technical debt cleanup") == Guna.TAMASIC
        )

    def test_default_by_category(self):
        clf = GunaClassifier()
        assert clf.classify("quality", "") == Guna.SATTVIC
        assert clf.classify("performance", "") == Guna.RAJASIC
        assert clf.classify("codebase_quality", "") == Guna.TAMASIC


class TestGunaPriors:
    def test_sattvic_reliable(self):
        clf = GunaClassifier()
        mean, var = clf.get_prior(Guna.SATTVIC)
        assert mean > 0.7  # High mean
        assert var < 0.1  # Low variance

    def test_rajasic_high_variance(self):
        clf = GunaClassifier()
        mean, var = clf.get_prior(Guna.RAJASIC)
        assert var > 0.15  # High variance


class TestOutcomes:
    def test_record_outcome(self):
        clf = GunaClassifier()
        clf.record_outcome(Guna.SATTVIC, success=True)
        clf.record_outcome(Guna.SATTVIC, success=True)
        clf.record_outcome(Guna.SATTVIC, success=False)
        rate = clf.get_success_rate(Guna.SATTVIC)
        assert abs(rate - 2 / 3) < 1e-6

    def test_default_success_rate(self):
        clf = GunaClassifier()
        rate = clf.get_success_rate(Guna.SATTVIC)
        assert rate == 0.8  # Default prior mean


class TestPortfolio:
    def test_default_portfolio(self):
        portfolio = GunaPortfolio()
        assert abs(portfolio.sattvic - 0.33) < 0.01

    def test_dominant(self):
        portfolio = GunaPortfolio(sattvic=0.6, rajasic=0.2, tamasic=0.2)
        assert portfolio.dominant == Guna.SATTVIC

    def test_current_portfolio(self):
        clf = GunaClassifier()
        clf.classify("quality", "docs")  # sattvic
        clf.classify("quality", "docs")  # sattvic
        clf.classify("performance", "feature")  # rajasic
        portfolio = clf.get_current_portfolio()
        assert portfolio.sattvic > portfolio.rajasic

    def test_target_high_debt(self):
        clf = GunaClassifier()
        target = clf.get_target_portfolio("high_debt")
        assert target.tamasic > 0.5

    def test_target_stagnation(self):
        clf = GunaClassifier()
        target = clf.get_target_portfolio("stagnation")
        assert target.rajasic > 0.5

    def test_target_chaos(self):
        clf = GunaClassifier()
        target = clf.get_target_portfolio("chaos")
        assert target.sattvic > 0.5

    def test_check_balance(self):
        clf = GunaClassifier()
        current = GunaPortfolio(sattvic=0.1, rajasic=0.1, tamasic=0.8)
        target = clf.get_target_portfolio("balanced")
        result = clf.check_balance(current, target, tolerance=0.1)
        assert isinstance(result["balanced"], bool)
        assert isinstance(result["deficits"], dict)


class TestStats:
    def test_stats(self):
        clf = GunaClassifier()
        clf.classify("quality", "docs")
        clf.classify("performance", "feature")
        stats = clf.get_stats()
        assert stats["classifications"] == 2
        assert "success_rates" in stats
