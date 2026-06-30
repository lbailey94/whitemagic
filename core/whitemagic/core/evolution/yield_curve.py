"""Yield Curve of Improvements (Objective Y).

Models the temporal value of improvements as a yield curve.
Each improvement has a value function V(t) that changes over time.

Value function models:
- Decaying (tamasic): V(t) = V₀ · exp(-λt) — cleanup loses value as new debt accumulates
- Compounding (sattvic): V(t) = V₀ · (1 + r)^t — foundational improvements gain value
- Appreciating (rajasic): V(t) = V₀ · log(1 + t/τ) — optimization appreciates then plateaus
- Transient: V(t) = V₀ · exp(-λt) · (1 - exp(-t/τ)) — rise and fall

Portfolio duration: weighted average time to value realization.
Term structure: choose improvements with different durations based on time horizon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from whitemagic.core.evolution._julia_yield_bridge import call as _julia_call


class YieldType(Enum):
    """Type of yield curve for an improvement."""

    DECAYING = "decaying"  # Tamasic: cleanup, debt reduction
    COMPOUNDING = "compounding"  # Sattvic: foundational, naming, architecture
    APPRECIATING = "appreciating"  # Rajasic: optimization, acceleration
    TRANSIENT = "transient"  # Rise and fall


@dataclass
class YieldCurve:
    """Yield curve for a single improvement."""

    improvement_id: str
    yield_type: YieldType
    v0: float = 1.0  # Initial value
    lambda_: float = 0.1  # Decay rate (for decaying/transient)
    r: float = 0.05  # Growth rate (for compounding)
    tau: float = 10.0  # Time constant (for appreciating/transient)
    observations: list[tuple[float, float]] = field(
        default_factory=list
    )  # (time, observed_value)

    def value_at(self, t: float) -> float:
        """Compute V(t) at time t.

        Args:
            t: Time since improvement was applied.

        Returns:
            Value at time t.
        """
        result = _julia_call(
            "value_at",
            yield_type=self.yield_type.value,
            t=t,
            v0=self.v0,
            **{"lambda": self.lambda_},
            r=self.r,
            tau=self.tau,
        )
        if result is not None:
            return result["value"]
        # Python fallback
        if self.yield_type == YieldType.DECAYING:
            return self.v0 * math.exp(-self.lambda_ * t)
        elif self.yield_type == YieldType.COMPOUNDING:
            return self.v0 * (1 + self.r) ** t
        elif self.yield_type == YieldType.APPRECIATING:
            return self.v0 * math.log(1 + t / self.tau)
        elif self.yield_type == YieldType.TRANSIENT:
            return self.v0 * math.exp(-self.lambda_ * t) * (1 - math.exp(-t / self.tau))
        return self.v0

    def duration(self) -> float:
        """Compute the duration (weighted average time to value realization).

        For decaying: 1/λ
        For compounding: 1/r (like bond duration)
        For appreciating: τ · (e - 1) (time to reach ~63% of asymptotic value)
        For transient: peak time = ln(λτ + 1) / (λ - 1/τ) if λ ≠ 1/τ
        """
        result = _julia_call(
            "duration",
            yield_type=self.yield_type.value,
            **{"lambda": self.lambda_},
            r=self.r,
            tau=self.tau,
        )
        if result is not None:
            return result["duration"]
        # Python fallback
        if self.yield_type == YieldType.DECAYING:
            return 1.0 / self.lambda_ if self.lambda_ > 0 else float("inf")
        elif self.yield_type == YieldType.COMPOUNDING:
            return 1.0 / self.r if self.r > 0 else float("inf")
        elif self.yield_type == YieldType.APPRECIATING:
            return self.tau * (math.e - 1)
        elif self.yield_type == YieldType.TRANSIENT:
            if abs(self.lambda_ - 1.0 / self.tau) < 1e-6:
                return self.tau
            return math.log(self.lambda_ * self.tau + 1) / (
                self.lambda_ - 1.0 / self.tau
            )
        return 0.0

    def add_observation(self, t: float, value: float) -> None:
        """Add an observed value at time t."""
        self.observations.append((t, value))

    def fit_parameters(self) -> dict[str, float]:
        """Fit yield curve parameters from observations.

        Simple grid search to find best-fitting parameters.

        Returns:
            Dict of fitted parameters.
        """
        if len(self.observations) < 3:
            return {"v0": self.v0, "lambda": self.lambda_, "r": self.r, "tau": self.tau}

        # Try Julia bridge first
        result = _julia_call(
            "fit_parameters",
            yield_type=self.yield_type.value,
            observations=[[t, val] for t, val in self.observations],
        )
        if result is not None:
            self.v0 = result["v0"]
            self.lambda_ = result["lambda"]
            self.r = result["r"]
            self.tau = result["tau"]
            return {"v0": self.v0, "lambda": self.lambda_, "r": self.r, "tau": self.tau}

        # Python fallback: simple parameter estimation: minimize squared error
        best_error = float("inf")
        best_params = {
            "v0": self.v0,
            "lambda": self.lambda_,
            "r": self.r,
            "tau": self.tau,
        }

        for v0 in [0.5, 1.0, 1.5, 2.0]:
            for lam in [0.01, 0.05, 0.1, 0.2, 0.5]:
                for r in [0.01, 0.05, 0.1, 0.2]:
                    for tau in [5.0, 10.0, 20.0, 50.0]:
                        self.v0 = v0
                        self.lambda_ = lam
                        self.r = r
                        self.tau = tau
                        error = sum(
                            (self.value_at(t) - val) ** 2
                            for t, val in self.observations
                        )
                        if error < best_error:
                            best_error = error
                            best_params = {"v0": v0, "lambda": lam, "r": r, "tau": tau}

        self.v0 = best_params["v0"]
        self.lambda_ = best_params["lambda"]
        self.r = best_params["r"]
        self.tau = best_params["tau"]
        return best_params


class YieldPortfolio:
    """Manages a portfolio of improvement yield curves.

    Computes portfolio duration and helps select improvements
    based on the system's time horizon.
    """

    def __init__(self) -> None:
        self._curves: dict[str, YieldCurve] = {}

    def add_curve(self, curve: YieldCurve) -> None:
        self._curves[curve.improvement_id] = curve

    def get_curve(self, improvement_id: str) -> YieldCurve | None:
        return self._curves.get(improvement_id)

    def portfolio_duration(self) -> float:
        """Compute weighted average duration of all improvements.

        Returns:
            Portfolio duration (weighted by V₀).
        """
        if not self._curves:
            return 0.0
        # Try Julia bridge
        curves_data = [
            {
                "yield_type": c.yield_type.value,
                "v0": c.v0,
                "lambda": c.lambda_,
                "r": c.r,
                "tau": c.tau,
            }
            for c in self._curves.values()
        ]
        result = _julia_call("portfolio_duration", curves=curves_data)
        if result is not None:
            return result["portfolio_duration"]
        # Python fallback
        total_weight = sum(c.v0 for c in self._curves.values())
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(c.v0 * c.duration() for c in self._curves.values())
        return weighted_sum / total_weight

    def select_by_horizon(
        self,
        time_horizon: float,
        candidates: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Select improvements that maximize value within the time horizon.

        Args:
            time_horizon: How far ahead to optimize (in cycles).
            candidates: Optional list of candidate improvement IDs.

        Returns:
            List of (improvement_id, value_at_horizon) sorted by value.
        """
        ids = candidates or list(self._curves.keys())
        # Try Julia bridge
        curves_data = []
        for imp_id in ids:
            curve = self._curves.get(imp_id)
            if curve is None:
                continue
            curves_data.append(
                {
                    "improvement_id": imp_id,
                    "yield_type": curve.yield_type.value,
                    "v0": curve.v0,
                    "lambda": curve.lambda_,
                    "r": curve.r,
                    "tau": curve.tau,
                }
            )
        result = _julia_call(
            "select_by_horizon", curves=curves_data, time_horizon=time_horizon
        )
        if result is not None:
            return [(s["improvement_id"], s["value"]) for s in result["selections"]]
        # Python fallback
        results = []
        for imp_id in ids:
            curve = self._curves.get(imp_id)
            if curve is None:
                continue
            value = curve.value_at(time_horizon)
            results.append((imp_id, value))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def detect_regime_change(self, improvement_id: str, window: int = 5) -> bool:
        """Detect if an improvement's yield curve shape has changed.

        A regime change occurs when a previously compounding improvement
        starts decaying (the codebase has evolved past it).

        Args:
            improvement_id: The improvement to check.
            window: Number of recent observations to compare.

        Returns:
            True if a regime change is detected.
        """
        curve = self._curves.get(improvement_id)
        if curve is None or len(curve.observations) < window * 2:
            return False

        # Try Julia bridge
        result = _julia_call(
            "detect_regime_change",
            yield_type=curve.yield_type.value,
            observations=[[t, val] for t, val in curve.observations],
            v0=curve.v0,
            **{"lambda": curve.lambda_},
            r=curve.r,
            tau=curve.tau,
            window=window,
        )
        if result is not None:
            return result["regime_change"]

        # Python fallback
        recent = curve.observations[-window:]
        below_count = 0
        for t, val in recent:
            predicted = curve.value_at(t)
            if val < predicted * 0.7:
                below_count += 1

        return below_count > window * 0.6

    def get_all_curves(self) -> dict[str, YieldCurve]:
        return dict(self._curves)

    def get_stats(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for c in self._curves.values():
            type_counts[c.yield_type.value] = type_counts.get(c.yield_type.value, 0) + 1
        return {
            "total_curves": len(self._curves),
            "portfolio_duration": self.portfolio_duration(),
            "type_distribution": type_counts,
        }
