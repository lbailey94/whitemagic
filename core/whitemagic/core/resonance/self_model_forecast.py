"""Self-Model Forecasting (ported from Julia)
=============================================

Time-series forecasting for the Self-Model predictive introspection system.

Ported from Julia's SelfModelForecast module:
- Exponential smoothing (Holt-Winters double)
- Anomaly detection via residual z-scores
- Multi-metric correlation analysis
- Forecast confidence intervals
- Batch forecasting for all Self-Model metrics

Usage:
    from whitemagic.core.resonance.self_model_forecast import SelfModelForecaster

    forecaster = SelfModelForecaster()
    result = forecaster.forecast_metric([0.5, 0.6, 0.55, 0.7, 0.65], steps=3)
    anomalies = forecaster.detect_anomalies([0.5, 0.6, 0.55, 1.5, 0.65])
    correlations = forecaster.correlation_matrix({"a": [1,2,3], "b": [1,2,3]})
    batch = forecaster.batch_forecast({"energy": [0.5, 0.6, 0.7], "error_rate": [0.1, 0.2, 0.15]})
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HoltWintersState:
    """State for Holt-Winters double exponential smoothing."""

    level: float
    trend: float
    alpha: float
    beta: float
    residuals: list[float] = field(default_factory=list)


def holt_winters_fit(
    series: list[float], alpha: float = 0.3, beta: float = 0.1
) -> HoltWintersState:
    """Fit Holt-Winters double exponential smoothing to a time series."""
    n = len(series)
    if n < 2:
        return HoltWintersState(
            level=series[0] if n > 0 else 0.0,
            trend=0.0,
            alpha=alpha,
            beta=beta,
            residuals=[],
        )

    # Initialize: level = first value, trend = first difference
    level = series[0]
    trend = series[1] - series[0]
    residuals = []

    for t in range(1, n):
        # Forecast for this step
        forecast = level + trend
        residuals.append(series[t] - forecast)

        # Update
        new_level = alpha * series[t] + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
        trend = new_trend

    return HoltWintersState(level, trend, alpha, beta, residuals)


def holt_winters_forecast(state: HoltWintersState, steps: int) -> dict[str, Any]:
    """Generate forecasts with confidence intervals."""
    forecasts = []
    lower_80 = []
    upper_80 = []
    lower_95 = []
    upper_95 = []

    # Estimate forecast error from residuals
    if len(state.residuals) > 1:
        mean_r = sum(state.residuals) / len(state.residuals)
        variance = sum((r - mean_r) ** 2 for r in state.residuals) / (
            len(state.residuals) - 1
        )
        sigma = math.sqrt(variance)
    else:
        sigma = 0.1

    for h in range(1, steps + 1):
        f = state.level + h * state.trend
        # Prediction interval widens with horizon
        se = sigma * math.sqrt(h)
        forecasts.append(round(f, 6))
        lower_80.append(round(f - 1.28 * se, 6))
        upper_80.append(round(f + 1.28 * se, 6))
        lower_95.append(round(f - 1.96 * se, 6))
        upper_95.append(round(f + 1.96 * se, 6))

    return {
        "forecasts": forecasts,
        "confidence_80": {"lower": lower_80, "upper": upper_80},
        "confidence_95": {"lower": lower_95, "upper": upper_95},
        "level": round(state.level, 6),
        "trend": round(state.trend, 6),
        "residual_std": round(sigma, 6),
    }


class SelfModelForecaster:
    """Self-Model forecasting with Holt-Winters exponential smoothing."""

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    def forecast_metric(
        self,
        values: list[float],
        steps: int = 5,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> dict[str, Any]:
        """Forecast a single Self-Model metric using Holt-Winters smoothing."""
        n = len(values)
        if n == 0:
            return {"error": "Empty time series"}

        # Fit model
        state = holt_winters_fit(values, alpha=alpha, beta=beta)

        # Generate forecasts
        fc = holt_winters_forecast(state, steps)

        fc["series_length"] = n
        fc["last_value"] = values[-1]
        fc["series_mean"] = round(self._mean(values), 6)
        fc["series_std"] = round(self._std(values), 6)
        fc["trend_direction"] = (
            "increasing"
            if state.trend > 0.001
            else "decreasing"
            if state.trend < -0.001
            else "stable"
        )

        return fc

    def detect_anomalies(
        self,
        values: list[float],
        threshold: float = 2.5,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> dict[str, Any]:
        """Detect anomalies using Holt-Winters residual z-scores."""
        n = len(values)
        if n < 3:
            return {"anomalies": [], "count": 0}

        state = holt_winters_fit(values, alpha=alpha, beta=beta)
        residuals = state.residuals
        sigma = self._std(residuals)
        mu = self._mean(residuals)

        anomalies = []
        for i, r in enumerate(residuals):
            z = abs(r - mu) / sigma if sigma > 0 else 0.0
            if z > threshold:
                anomalies.append(
                    {
                        "index": i
                        + 1,  # 1-indexed, offset by 1 since residuals start at t=2
                        "value": round(values[i + 1], 6),
                        "expected": round(values[i + 1] - r, 6),
                        "residual": round(r, 6),
                        "z_score": round(z, 4),
                        "direction": "above" if r > 0 else "below",
                    }
                )

        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "residual_mean": round(mu, 6),
            "residual_std": round(sigma, 6),
            "threshold": threshold,
        }

    def correlation_matrix(
        self,
        metrics: dict[str, list[float]],
    ) -> dict[str, Any]:
        """Compute pairwise Pearson correlations between Self-Model metrics."""
        names = list(metrics.keys())
        n = len(names)
        if n < 2:
            return {"error": "Need at least 2 metrics"}

        # Ensure all vectors have the same length (truncate to shortest)
        min_len = min(len(v) for v in metrics.values())
        if min_len < 3:
            return {"error": "Need at least 3 data points per metric"}

        # Truncate
        truncated = {name: values[:min_len] for name, values in metrics.items()}

        # Compute correlation matrix
        corr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                vi = truncated[names[i]]
                vj = truncated[names[j]]
                corr[i][j] = self._pearson(vi, vj)

        # Find strong correlations (|r| > 0.7)
        strong = []
        for i in range(n):
            for j in range(i + 1, n):
                r = corr[i][j]
                if abs(r) > 0.7:
                    strong.append(
                        {
                            "metric_a": names[i],
                            "metric_b": names[j],
                            "correlation": round(r, 4),
                            "relationship": "positive" if r > 0 else "negative",
                            "strength": "very_strong" if abs(r) > 0.9 else "strong",
                        }
                    )

        return {
            "metric_names": names,
            "correlation_matrix": [[round(c, 4) for c in row] for row in corr],
            "strong_correlations": strong,
            "sample_size": min_len,
        }

    @staticmethod
    def _pearson(x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    def batch_forecast(
        self,
        metrics: dict[str, list[float]],
        steps: int = 5,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> dict[str, Any]:
        """Forecast all Self-Model metrics in one call."""
        forecasts = {}
        alerts = []

        for name, values in metrics.items():
            fc = self.forecast_metric(values, steps=steps, alpha=alpha, beta=beta)
            forecasts[name] = fc

            # Generate alerts for concerning trends
            if "trend_direction" in fc:
                trend = fc["trend_direction"]
                last_val = fc["last_value"]

                # Alert thresholds (domain-specific)
                if name == "energy" and trend == "decreasing" and last_val < 0.4:
                    alerts.append(
                        {
                            "metric": name,
                            "alert": "low_energy_declining",
                            "severity": "warning",
                        }
                    )
                elif name == "error_rate" and trend == "increasing" and last_val > 0.2:
                    alerts.append(
                        {
                            "metric": name,
                            "alert": "error_rate_rising",
                            "severity": "critical",
                        }
                    )
                elif name == "karma_debt" and trend == "increasing" and last_val > 0.5:
                    alerts.append(
                        {
                            "metric": name,
                            "alert": "karma_debt_growing",
                            "severity": "warning",
                        }
                    )

        return {
            "forecasts": forecasts,
            "alerts": alerts,
            "metrics_count": len(metrics),
            "forecast_horizon": steps,
        }
