"""Tests for Objective Y — Yield Curve of Improvements."""

from __future__ import annotations

import math

import pytest

from whitemagic.core.evolution.yield_curve import (
    YieldCurve,
    YieldPortfolio,
    YieldType,
)


@pytest.mark.xdist_group(name="yield_curve")
class TestYieldCurve:
    def test_decaying(self):
        curve = YieldCurve(
            improvement_id="h1", yield_type=YieldType.DECAYING, v0=1.0, lambda_=0.1
        )
        v0 = curve.value_at(0)
        v10 = curve.value_at(10)
        assert abs(v0 - 1.0) < 1e-6
        assert v10 < v0  # Decaying

    def test_compounding(self):
        curve = YieldCurve(
            improvement_id="h1", yield_type=YieldType.COMPOUNDING, v0=1.0, r=0.1
        )
        v0 = curve.value_at(0)
        v10 = curve.value_at(10)
        assert abs(v0 - 1.0) < 1e-6
        assert v10 > v0  # Growing

    def test_appreciating(self):
        curve = YieldCurve(
            improvement_id="h1", yield_type=YieldType.APPRECIATING, v0=1.0, tau=10.0
        )
        v0 = curve.value_at(0)
        v10 = curve.value_at(10)
        assert v10 > v0  # Appreciating

    def test_transient(self):
        curve = YieldCurve(
            improvement_id="h1",
            yield_type=YieldType.TRANSIENT,
            v0=1.0,
            lambda_=0.1,
            tau=5.0,
        )
        v0 = curve.value_at(0)
        v5 = curve.value_at(5)
        v20 = curve.value_at(20)
        assert v0 < 0.01  # Near zero at t=0
        assert v5 > v0  # Rises
        assert v20 < v5  # Then falls

    def test_duration(self):
        decaying = YieldCurve(
            improvement_id="h1", yield_type=YieldType.DECAYING, lambda_=0.1
        )
        assert abs(decaying.duration() - 10.0) < 1e-6  # 1/λ

        compounding = YieldCurve(
            improvement_id="h2", yield_type=YieldType.COMPOUNDING, r=0.05
        )
        assert abs(compounding.duration() - 20.0) < 1e-6  # 1/r

    def test_fit_parameters(self):
        curve = YieldCurve(
            improvement_id="h1", yield_type=YieldType.DECAYING, v0=1.0, lambda_=0.1
        )
        # Generate synthetic observations
        for t in range(10):
            curve.add_observation(float(t), 1.0 * math.exp(-0.1 * t))
        params = curve.fit_parameters()
        assert "v0" in params
        assert "lambda" in params


@pytest.mark.xdist_group(name="yield_curve")
class TestYieldPortfolio:
    def test_add_and_get(self):
        portfolio = YieldPortfolio()
        curve = YieldCurve(improvement_id="h1", yield_type=YieldType.DECAYING)
        portfolio.add_curve(curve)
        assert portfolio.get_curve("h1") is not None

    def test_portfolio_duration(self):
        portfolio = YieldPortfolio()
        portfolio.add_curve(
            YieldCurve(
                improvement_id="h1", yield_type=YieldType.DECAYING, v0=1.0, lambda_=0.1
            )
        )
        portfolio.add_curve(
            YieldCurve(
                improvement_id="h2", yield_type=YieldType.COMPOUNDING, v0=1.0, r=0.2
            )
        )
        duration = portfolio.portfolio_duration()
        assert duration > 0

    def test_select_by_horizon(self):
        portfolio = YieldPortfolio()
        portfolio.add_curve(
            YieldCurve(
                improvement_id="h1", yield_type=YieldType.DECAYING, v0=1.0, lambda_=0.5
            )
        )
        portfolio.add_curve(
            YieldCurve(
                improvement_id="h2", yield_type=YieldType.COMPOUNDING, v0=1.0, r=0.1
            )
        )
        # Short horizon → decaying should be better
        short = portfolio.select_by_horizon(time_horizon=1.0)
        # Long horizon → compounding should be better
        long_h = portfolio.select_by_horizon(time_horizon=20.0)
        assert short[0][1] > 0  # Some value at short horizon
        assert long_h[0][1] > 0  # Some value at long horizon

    def test_detect_regime_change(self):
        portfolio = YieldPortfolio()
        curve = YieldCurve(
            improvement_id="h1", yield_type=YieldType.COMPOUNDING, v0=1.0, r=0.1
        )
        # Add observations that match the model
        for t in range(10):
            curve.add_observation(float(t), curve.value_at(float(t)))
        portfolio.add_curve(curve)
        # No regime change with matching observations
        assert portfolio.detect_regime_change("h1") is False

        # Add observations that diverge (values dropping)
        for t in range(10, 20):
            curve.add_observation(float(t), 0.1)  # Much lower than predicted
        assert portfolio.detect_regime_change("h1") is True

    def test_stats(self):
        portfolio = YieldPortfolio()
        portfolio.add_curve(
            YieldCurve(improvement_id="h1", yield_type=YieldType.DECAYING)
        )
        portfolio.add_curve(
            YieldCurve(improvement_id="h2", yield_type=YieldType.COMPOUNDING)
        )
        stats = portfolio.get_stats()
        assert stats["total_curves"] == 2
        assert "portfolio_duration" in stats
        assert stats["type_distribution"]["decaying"] == 1
        assert stats["type_distribution"]["compounding"] == 1
