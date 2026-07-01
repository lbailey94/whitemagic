"""Continuous scoring rules for probabilistic predictions.

Supplements brier.py with proper scoring rules for continuous outcomes:
- CRPS (Continuous Ranked Probability Score) — primary metric
- CRPS decomposition (Miscalibration, Discrimination, Uncertainty)
- Quantile Score / Weighted Interval Score (WIS) — CRPS approximation
- ECCE (Empirical Cumulative Calibration Error) — testable calibration
- Pinball Loss — quantile-specific scoring

These replace Brier score for continuous time/effort predictions where
binary outcomes lose information. Brier remains for binary event forecasts.

References:
- Matheson & Winkler (1976) — CRPS definition
- Arnold et al. (2023) — CRPS decomposition (MSC/DSC/UNC)
- Gneiting & Raftery (2007) — Strictly proper scoring rules
- Tygert (2022) — ECCE calibration metric
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from typing import Any


def crps_gaussian(
    prediction: float,
    actual: float,
    sigma: float,
) -> float:
    """CRPS for a Gaussian prediction with mean=prediction, std=sigma.

    CRPS = sigma * [z * (2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi)]
    where z = (actual - prediction) / sigma.

    Lower is better. 0 = perfect prediction.
    Reduces to absolute error when sigma → 0.

    Args:
        prediction: Predicted mean.
        actual: Observed value.
        sigma: Predicted standard deviation (uncertainty).

    Returns:
        CRPS score (same units as input, lower is better).
    """
    if sigma <= 0:
        sigma = 0.001
    z = (actual - prediction) / sigma
    phi_z = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    phi_of_z = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return sigma * (z * (2 * phi_of_z - 1) + 2 * phi_z - 1.0 / math.sqrt(math.pi))


def crps_point(prediction: float, actual: float) -> float:
    """CRPS for a point prediction (deterministic, no uncertainty).

    This is simply the absolute error: |prediction - actual|.
    """
    return abs(prediction - actual)


def mean_crps(
    predictions: Sequence[float],
    actuals: Sequence[float],
    sigmas: Sequence[float] | None = None,
) -> float:
    """Mean CRPS over a set of predictions.

    Args:
        predictions: Predicted means.
        actuals: Observed values.
        sigmas: Predicted std devs. If None, uses 20% of each prediction.

    Returns:
        Mean CRPS (lower is better).
    """
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have the same length")
    if not predictions:
        raise ValueError("Cannot compute mean CRPS on empty inputs")

    if sigmas is None:
        sigmas = [max(abs(p) * 0.2, 0.001) for p in predictions]

    total = sum(crps_gaussian(p, a, s) for p, a, s in zip(predictions, actuals, sigmas))
    return total / len(predictions)


def crps_skill_score(
    predictions: Sequence[float],
    actuals: Sequence[float],
    sigmas: Sequence[float] | None = None,
) -> float:
    """CRPS Skill Score: how much better than a climatological baseline.

    BSS = 1 - (CRPS / CRPS_baseline)
    Baseline: predict the mean of actuals with std of actuals.
    Positive = skill; 1.0 = perfect.
    """
    if not actuals:
        return 0.0

    mean_actual = statistics.mean(actuals)
    std_actual = statistics.stdev(actuals) if len(actuals) > 1 else 0.001
    if std_actual == 0:
        std_actual = 0.001

    crps_forecast = mean_crps(predictions, actuals, sigmas)
    crps_baseline = mean_crps(
        [mean_actual] * len(actuals),
        actuals,
        [std_actual] * len(actuals),
    )

    if crps_baseline == 0:
        return 1.0 if crps_forecast == 0 else float("-inf")
    return 1.0 - (crps_forecast / crps_baseline)


def crps_decomposition(
    predictions: Sequence[float],
    actuals: Sequence[float],
    sigmas: Sequence[float] | None = None,
) -> dict[str, float]:
    """Decompose mean CRPS into Miscalibration, Discrimination, Uncertainty.

    Following Arnold et al. (2023) isotonicity-based decomposition:
    mean_crps = MSC - DSC + UNC

    - MSC (Miscalibration): How far forecast CDF is from isotonic (ideal).
      Lower = better calibrated.
    - DSC (Discrimination): How much the forecast differs from climatology.
      Higher = more informative.
    - UNC (Uncertainty): Irreducible variability of outcomes.
      Constant for a given dataset.

    For Gaussian forecasts, we approximate this via:
    - UNC = mean(|actual - median(actuals)|)
    - MSC = mean CRPS of forecast vs actual
    - DSC = UNC - mean CRPS of climatology vs actual

    Args:
        predictions: Predicted means.
        actuals: Observed values.
        sigmas: Predicted std devs. If None, uses 20% of each prediction.

    Returns:
        Dict with mean_crps, miscalibration, discrimination, uncertainty,
        skill_score, and per-prediction breakdown.
    """
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have the same length")
    if not predictions:
        raise ValueError("Cannot decompose CRPS on empty inputs")

    if sigmas is None:
        sigmas = [max(abs(p) * 0.2, 0.001) for p in predictions]

    n = len(predictions)
    crps_values = [
        crps_gaussian(p, a, s) for p, a, s in zip(predictions, actuals, sigmas)
    ]
    mean_crps_val = sum(crps_values) / n

    # Uncertainty: mean absolute deviation of actuals from their median
    median_actual = statistics.median(actuals)
    unc = sum(abs(a - median_actual) for a in actuals) / n

    # Climatological baseline: predict median with std of actuals
    std_actual = statistics.stdev(actuals) if len(actuals) > 1 else 0.001
    if std_actual == 0:
        std_actual = 0.001
    crps_climatology = (
        sum(crps_gaussian(median_actual, a, std_actual) for a in actuals) / n
    )

    # Discrimination: how much better than climatology
    dsc = max(0.0, unc - crps_climatology)

    # Miscalibration: excess CRPS beyond what climatology explains
    msc = mean_crps_val - unc + dsc

    skill = crps_skill_score(predictions, actuals, sigmas)

    return {
        "mean_crps": round(mean_crps_val, 6),
        "miscalibration": round(max(msc, 0.0), 6),
        "discrimination": round(dsc, 6),
        "uncertainty": round(unc, 6),
        "crps_climatology": round(crps_climatology, 6),
        "skill_score": round(skill, 4),
        "count": n,
    }


def quantile_score(
    prediction: float,
    actual: float,
    quantile: float,
) -> float:
    """Pinball/quantile loss for a single quantile prediction.

    QS = 2 * max(quantile * (actual - prediction), (1 - quantile) * (prediction - actual))

    Lower is better. 0 = perfect quantile prediction.
    Proper scoring rule for quantile forecasts.

    Args:
        prediction: Predicted quantile value.
        actual: Observed value.
        quantile: Probability level in [0, 1] (e.g., 0.5 for median).

    Returns:
        Quantile score (lower is better).
    """
    diff = actual - prediction
    return 2 * max(quantile * diff, (1 - quantile) * (-diff))


def weighted_interval_score(
    median: float,
    actual: float,
    lower_bounds: Sequence[float],
    upper_bounds: Sequence[float],
    quantile_levels: Sequence[float],
) -> float:
    """Weighted Interval Score (WIS) — approximation to CRPS.

    WIS = |median - actual| + (1/K) * sum_k[2 * alpha_k * (u_k - actual) * I(actual > u_k)
                                                + 2 * alpha_k * (actual - l_k) * I(actual < l_k)]

    where (l_k, u_k) are prediction intervals at level (1 - alpha_k).

    As K → infinity, WIS → CRPS.
    Even with a few intervals, WIS is a proper scoring rule.

    Args:
        median: Predicted median (p50).
        actual: Observed value.
        lower_bounds: Lower bounds of prediction intervals.
        upper_bounds: Upper bounds of prediction intervals.
        quantile_levels: Alpha levels for each interval (e.g., [0.1, 0.05]).

    Returns:
        WIS score (lower is better). Approximates CRPS.
    """
    if len(lower_bounds) != len(upper_bounds) or len(lower_bounds) != len(
        quantile_levels
    ):
        raise ValueError(
            "lower_bounds, upper_bounds, and quantile_levels must have the same length"
        )

    k = len(quantile_levels)
    if k == 0:
        return abs(median - actual)

    # Median component
    wis = abs(median - actual)

    # Interval components
    for i in range(k):
        alpha = quantile_levels[i]
        lower = lower_bounds[i]
        u = upper_bounds[i]
        if actual < lower:
            wis += (2 / k) * alpha * (lower - actual)
        elif actual > u:
            wis += (2 / k) * alpha * (actual - u)

    return wis


def ecce(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    """Empirical Cumulative Calibration Error (ECCE).

    Unlike ECE (Expected Calibration Error), ECCE is:
    - Testable (can be empirically estimated)
    - Independent of bin choice
    - Asymptotically consistent

    ECCE = (1/n) * sum_i |F_n(f_i) - o_bar(f_i)|

    where F_n is the empirical CDF of forecasts and o_bar is the
    empirical outcome rate for forecasts <= f_i.

    For binary outcomes (0/1), this measures how well the forecast
    probabilities calibrate against observed frequencies without
    the bin-dependence of ECE.

    Args:
        forecasts: Predicted probabilities in [0, 1].
        outcomes: Binary outcomes (0 or 1).

    Returns:
        ECCE score in [0, 1]. Lower = better calibrated.
    """
    if len(forecasts) != len(outcomes):
        raise ValueError("forecasts and outcomes must have the same length")
    if not forecasts:
        return 0.0

    n = len(forecasts)
    # Sort by forecast value
    pairs = sorted(zip(forecasts, outcomes), key=lambda x: x[0])

    # Compute cumulative calibration error
    total_error = 0.0
    cumulative_outcomes = 0.0
    for i, (f, o) in enumerate(pairs):
        cumulative_outcomes += o
        # Empirical frequency of outcomes for forecasts <= f_i
        emp_freq = cumulative_outcomes / (i + 1)
        # Empirical CDF value at f_i
        emp_cdf = (i + 1) / n
        total_error += abs(emp_cdf - emp_freq)

    return total_error / n


def log_score(
    prediction: float,
    actual: float,
    sigma: float,
) -> float:
    """Negative log-likelihood (log score) for Gaussian prediction.

    LogS = 0.5 * log(2*pi*sigma^2) + (actual - prediction)^2 / (2*sigma^2)

    Lower is better. More sensitive to outliers than CRPS.
    Strictly proper scoring rule.

    Args:
        prediction: Predicted mean.
        actual: Observed value.
        sigma: Predicted standard deviation.

    Returns:
        Log score (lower is better).
    """
    if sigma <= 0:
        sigma = 0.001
    return 0.5 * math.log(2 * math.pi * sigma * sigma) + (actual - prediction) ** 2 / (
        2 * sigma * sigma
    )


def mean_log_score(
    predictions: Sequence[float],
    actuals: Sequence[float],
    sigmas: Sequence[float] | None = None,
) -> float:
    """Mean log score over a set of predictions.

    More aggressive than CRPS at penalizing overconfident wrong predictions.
    """
    if sigmas is None:
        sigmas = [max(abs(p) * 0.2, 0.001) for p in predictions]
    return sum(
        log_score(p, a, s) for p, a, s in zip(predictions, actuals, sigmas)
    ) / len(predictions)


def dagstuhl_score(
    predictions: Sequence[float],
    actuals: Sequence[float],
    sigmas: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Comprehensive scoring summary using multiple proper scoring rules.

    Returns CRPS, log score, quantile scores, and calibration metrics
    in a single dict. Named after the Dagstuhl seminar on forecasting
    evaluation that established best practices.

    Args:
        predictions: Predicted means.
        actuals: Observed values.
        sigmas: Predicted std devs. If None, uses 20% of each prediction.

    Returns:
        Dict with all scoring metrics.
    """
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have the same length")
    if not predictions:
        return {"count": 0, "message": "No predictions to score"}

    if sigmas is None:
        sigmas = [max(abs(p) * 0.2, 0.001) for p in predictions]

    n = len(predictions)

    # CRPS and decomposition
    crps_decomp = crps_decomposition(predictions, actuals, sigmas)

    # Mean log score
    mls = mean_log_score(predictions, actuals, sigmas)

    # Per-prediction CRPS
    per_pred_crps = [
        crps_gaussian(p, a, s) for p, a, s in zip(predictions, actuals, sigmas)
    ]

    # Quantile scores at p50 (median)
    qs_50 = [quantile_score(p, a, 0.5) for p, a in zip(predictions, actuals)]
    mean_qs50 = sum(qs_50) / n

    # Quantile scores at p90
    p90_preds = [p + 1.2816 * s for p, s in zip(predictions, sigmas)]  # 90th percentile
    qs_90 = [quantile_score(p90, a, 0.9) for p90, a in zip(p90_preds, actuals)]
    mean_qs90 = sum(qs_90) / n

    # Mean absolute error (MAE) — CRPS for point forecasts
    mae = sum(abs(p - a) for p, a in zip(predictions, actuals)) / n

    # Mean absolute percentage error (MAPE)
    mape = (
        sum(abs(p - a) / max(abs(a), 0.001) * 100 for p, a in zip(predictions, actuals))
        / n
    )

    # Bias: mean prediction - mean actual
    bias = statistics.mean(predictions) - statistics.mean(actuals)

    log_ratios = [
        math.log(p / a) if p > 0 and a > 0 else 0.0
        for p, a in zip(predictions, actuals)
    ]
    mean_log_ratio = statistics.mean(log_ratios)
    mae_log_ratio = statistics.mean([abs(x) for x in log_ratios])

    return {
        "count": n,
        "mean_crps": crps_decomp["mean_crps"],
        "crps_decomposition": {
            "miscalibration": crps_decomp["miscalibration"],
            "discrimination": crps_decomp["discrimination"],
            "uncertainty": crps_decomp["uncertainty"],
        },
        "crps_skill_score": crps_decomp["skill_score"],
        "mean_log_score": round(mls, 6),
        "mean_quantile_score_50": round(mean_qs50, 6),
        "mean_quantile_score_90": round(mean_qs90, 6),
        "mae": round(mae, 6),
        "mape": round(mape, 2),
        "bias": round(bias, 6),
        "mean_log_ratio_error": round(mean_log_ratio, 4),
        "mae_log_ratio_error": round(mae_log_ratio, 4),
        "per_prediction_crps": [round(c, 6) for c in per_pred_crps],
    }
