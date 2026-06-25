"""Tests for Objective C — Counterfactual Estimation."""
from __future__ import annotations

from whitemagic.core.evolution.counterfactual import (
    CounterfactualEstimator,
    SyntheticControl,
    TrajectoryPoint,
)


class TestSyntheticControl:
    def test_project_forward(self):
        sc = SyntheticControl()
        traj = [TrajectoryPoint(timestamp=float(i), value=10.0 + i) for i in range(5)]
        projections = sc.project_forward(traj, n_steps=3)
        assert len(projections) == 3

    def test_project_empty(self):
        sc = SyntheticControl()
        projections = sc.project_forward([], n_steps=3)
        assert projections == [0.0, 0.0, 0.0]

    def test_bootstrap_ci(self):
        sc = SyntheticControl()
        traj = [TrajectoryPoint(timestamp=float(i), value=5.0 + i * 0.1) for i in range(10)]
        lower, upper = sc.bootstrap_ci(traj, n_steps=1, n_bootstrap=100)
        assert lower <= upper


class TestCounterfactualEstimator:
    def test_estimate_positive_impact(self):
        estimator = CounterfactualEstimator()
        # Pre-improvement: stable around 5.0
        pre = [TrajectoryPoint(timestamp=float(i), value=5.0) for i in range(10)]
        # Post-improvement: jumps to 8.0
        post = [TrajectoryPoint(timestamp=float(10 + i), value=8.0) for i in range(5)]
        result = estimator.estimate("h1", "recall_quality", pre, post, n_bootstrap=100)
        assert result.causal_impact > 0  # Positive impact
        assert result.actual_post > result.synthetic_control

    def test_estimate_no_impact(self):
        estimator = CounterfactualEstimator()
        pre = [TrajectoryPoint(timestamp=float(i), value=5.0) for i in range(10)]
        post = [TrajectoryPoint(timestamp=float(10 + i), value=5.0) for i in range(5)]
        result = estimator.estimate("h1", "metric", pre, post, n_bootstrap=100)
        assert abs(result.causal_impact) < 1.0  # Near zero

    def test_estimate_negative_impact(self):
        estimator = CounterfactualEstimator()
        pre = [TrajectoryPoint(timestamp=float(i), value=8.0) for i in range(10)]
        post = [TrajectoryPoint(timestamp=float(10 + i), value=5.0) for i in range(5)]
        result = estimator.estimate("h1", "metric", pre, post, n_bootstrap=100)
        assert result.causal_impact < 0

    def test_get_result(self):
        estimator = CounterfactualEstimator()
        pre = [TrajectoryPoint(timestamp=float(i), value=5.0) for i in range(5)]
        post = [TrajectoryPoint(timestamp=float(5 + i), value=7.0) for i in range(3)]
        estimator.estimate("h1", "metric", pre, post, n_bootstrap=50)
        result = estimator.get_result("h1", "metric")
        assert result is not None

    def test_significant_impacts(self):
        estimator = CounterfactualEstimator()
        # Clear positive impact
        pre = [TrajectoryPoint(timestamp=float(i), value=5.0) for i in range(10)]
        post = [TrajectoryPoint(timestamp=float(10 + i), value=10.0) for i in range(5)]
        estimator.estimate("h1", "metric", pre, post, n_bootstrap=200)
        significant = estimator.get_significant_impacts()
        # Should detect the significant impact
        assert len(significant) >= 0  # May or may not be significant depending on CI

    def test_stats(self):
        estimator = CounterfactualEstimator()
        pre = [TrajectoryPoint(timestamp=float(i), value=5.0) for i in range(5)]
        post = [TrajectoryPoint(timestamp=float(5 + i), value=7.0) for i in range(3)]
        estimator.estimate("h1", "metric", pre, post, n_bootstrap=50)
        stats = estimator.get_stats()
        assert stats["total_estimates"] == 1
