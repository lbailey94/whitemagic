"""Counterfactual Estimation (Objective C).

Implements synthetic control / difference-in-differences estimation.
For each applied improvement, constructs a synthetic baseline from the
system's own pre-improvement trajectory projected forward.

Estimated causal impact = actual_trajectory - synthetic_control
Confidence interval from MC bootstrap of the synthetic control.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from whitemagic.core.evolution._rust_bridge import call as _rust_call


@dataclass
class TrajectoryPoint:
    """A single point in a metric trajectory."""
    timestamp: float
    value: float


@dataclass
class CounterfactualResult:
    """Result of a counterfactual estimation."""
    improvement_id: str
    metric: str
    actual_post: float          # Actual post-improvement average
    synthetic_control: float    # Projected baseline
    causal_impact: float        # actual_post - synthetic_control
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    confidence_level: float = 0.0
    n_pre_points: int = 0
    n_post_points: int = 0
    bootstrap_samples: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class SyntheticControl:
    """Constructs synthetic control baselines for counterfactual estimation.

    Uses exponential smoothing of pre-improvement metrics to project
    what would have happened without the improvement.
    """

    def __init__(self, smoothing_alpha: float = 0.3) -> None:
        self._alpha = smoothing_alpha

    def project_forward(
        self,
        pre_trajectory: list[TrajectoryPoint],
        n_steps: int = 1,
    ) -> list[float]:
        """Project pre-improvement trajectory forward using exponential smoothing.

        Args:
            pre_trajectory: Metric values before the improvement.
            n_steps: Number of steps to project forward.

        Returns:
            List of projected values.
        """
        if not pre_trajectory:
            return [0.0] * n_steps if n_steps > 0 else []

        # Try Rust bridge
        pre_values = [p.value for p in pre_trajectory]
        result = _rust_call("cf_project_forward",
            pre_values=pre_values,
            smoothing_alpha=self._alpha,
            n_steps=n_steps)
        if result is not None and "projections" in result:
            return result["projections"]

        # Python fallback
        sorted_traj = sorted(pre_trajectory, key=lambda p: p.timestamp)
        values = [p.value for p in sorted_traj]

        smoothed = values[0]
        for v in values[1:]:
            smoothed = self._alpha * v + (1 - self._alpha) * smoothed

        if len(values) >= 2:
            trend = values[-1] - values[-2]
        else:
            trend = 0.0

        projections = []
        current = smoothed
        for _ in range(n_steps):
            current = current + trend * self._alpha
            projections.append(current)

        return projections

    def bootstrap_ci(
        self,
        pre_trajectory: list[TrajectoryPoint],
        n_steps: int,
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Bootstrap confidence interval for the synthetic control.

        Args:
            pre_trajectory: Pre-improvement values.
            n_steps: Steps to project.
            n_bootstrap: Number of bootstrap samples.
            confidence: Confidence level (0-1).

        Returns:
            (lower, upper) confidence interval.
        """
        if not pre_trajectory or n_bootstrap < 10:
            return (0.0, 0.0)

        # Try Rust bridge
        pre_values = [p.value for p in pre_trajectory]
        result = _rust_call("cf_bootstrap_ci",
            pre_values=pre_values,
            smoothing_alpha=self._alpha,
            n_steps=n_steps,
            n_bootstrap=n_bootstrap,
            confidence=confidence)
        if result is not None and "ci_lower" in result:
            return (result["ci_lower"], result["ci_upper"])

        # Python fallback
        values = [p.value for p in pre_trajectory]
        samples = []

        for _ in range(n_bootstrap):
            boot = [random.choice(values) for _ in range(len(values))]
            boot_traj = [
                TrajectoryPoint(timestamp=float(i), value=v)
                for i, v in enumerate(boot)
            ]
            projection = self.project_forward(boot_traj, n_steps)
            if projection:
                samples.append(projection[-1])

        if not samples:
            return (0.0, 0.0)

        samples.sort()
        alpha = (1 - confidence) / 2
        lower_idx = int(alpha * len(samples))
        upper_idx = int((1 - alpha) * len(samples))
        return (samples[lower_idx], samples[upper_idx])


class CounterfactualEstimator:
    """Estimates causal impact of improvements using synthetic control.

    estimated_causal_impact = actual_post - synthetic_control
    """

    def __init__(self, smoothing_alpha: float = 0.3) -> None:
        self._sc = SyntheticControl(smoothing_alpha=smoothing_alpha)
        self._results: dict[str, CounterfactualResult] = {}

    def estimate(
        self,
        improvement_id: str,
        metric: str,
        pre_trajectory: list[TrajectoryPoint],
        post_trajectory: list[TrajectoryPoint],
        n_bootstrap: int = 500,
        confidence: float = 0.95,
    ) -> CounterfactualResult:
        """Estimate causal impact of an improvement.

        Args:
            improvement_id: The improvement ID.
            metric: The metric being analyzed.
            pre_trajectory: Metric values before the improvement.
            post_trajectory: Metric values after the improvement.
            n_bootstrap: Bootstrap samples for CI.
            confidence: Confidence level for CI.

        Returns:
            CounterfactualResult with causal impact estimate.
        """
        n_post = len(post_trajectory)
        n_pre = len(pre_trajectory)

        # Try Rust bridge for the full estimation
        pre_values = [p.value for p in pre_trajectory]
        post_values = [p.value for p in post_trajectory]
        rust_result = _rust_call("cf_estimate_impact",
            pre_values=pre_values,
            post_values=post_values,
            smoothing_alpha=self._sc._alpha,
            n_bootstrap=n_bootstrap,
            confidence=confidence)

        if rust_result is not None and "causal_impact" in rust_result:
            result = CounterfactualResult(
                improvement_id=improvement_id,
                metric=metric,
                actual_post=rust_result["actual_post"],
                synthetic_control=rust_result["synthetic_control"],
                causal_impact=rust_result["causal_impact"],
                confidence_interval=(
                    rust_result.get("ci_lower", 0.0),
                    rust_result.get("ci_upper", 0.0),
                ),
                confidence_level=confidence,
                n_pre_points=n_pre,
                n_post_points=n_post,
                bootstrap_samples=n_bootstrap,
            )
            self._results[f"{improvement_id}_{metric}"] = result
            return result

        # Python fallback
        projections = self._sc.project_forward(pre_trajectory, n_post)
        synthetic_control = sum(projections) / len(projections) if projections else 0.0

        actual_post = sum(p.value for p in post_trajectory) / n_post if post_trajectory else 0.0

        causal_impact = actual_post - synthetic_control

        ci = self._sc.bootstrap_ci(
            pre_trajectory, n_post, n_bootstrap=n_bootstrap, confidence=confidence,
        )

        result = CounterfactualResult(
            improvement_id=improvement_id,
            metric=metric,
            actual_post=actual_post,
            synthetic_control=synthetic_control,
            causal_impact=causal_impact,
            confidence_interval=ci,
            confidence_level=confidence,
            n_pre_points=n_pre,
            n_post_points=n_post,
            bootstrap_samples=n_bootstrap,
        )
        self._results[f"{improvement_id}_{metric}"] = result
        return result

    def get_result(self, improvement_id: str, metric: str) -> CounterfactualResult | None:
        return self._results.get(f"{improvement_id}_{metric}")

    def get_all_results(self) -> dict[str, CounterfactualResult]:
        return dict(self._results)

    def get_significant_impacts(self, alpha: float = 0.05) -> list[CounterfactualResult]:
        """Get improvements with statistically significant causal impact.

        Args:
            alpha: Significance level (1 - confidence).

        Returns:
            List of significant results.
        """
        significant = []
        for result in self._results.values():
            lower, upper = result.confidence_interval
            # Significant if CI doesn't contain 0
            if (lower > 0 and upper > 0) or (lower < 0 and upper < 0):
                significant.append(result)
        return significant

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_estimates": len(self._results),
            "significant_count": len(self.get_significant_impacts()),
        }
