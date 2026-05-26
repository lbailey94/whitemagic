"""Brier scoring and calibration utilities for the prescience track record.

Brier score: mean squared error between probability forecasts and binary outcomes.
  BS = (1/N) * sum((f_i - o_i)^2)
  Range: 0.0 (perfect) to 1.0 (worst). Reference score = 0.25 (uninformed, p=0.5).

Brier Skill Score: how much better than climatological baseline.
  BSS = 1 - (BS / BS_ref)
  BSS > 0 means skill; BSS = 1 is perfect.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def brier_score(forecasts: Sequence[float], outcomes: Sequence[int]) -> float:
    """Compute the mean Brier score over a set of (probability, outcome) pairs.

    Args:
        forecasts: Predicted probabilities in [0, 1].
        outcomes: Binary outcomes (1 = event occurred, 0 = did not occur).

    Returns:
        Brier score in [0, 1]. Lower is better.

    Raises:
        ValueError: If inputs are empty or lengths differ.
    """
    if len(forecasts) != len(outcomes):
        raise ValueError(
            f"forecasts and outcomes must have the same length "
            f"({len(forecasts)} vs {len(outcomes)})"
        )
    if not forecasts:
        raise ValueError("Cannot compute Brier score on empty inputs")
    total = sum((f - o) ** 2 for f, o in zip(forecasts, outcomes))
    return total / len(forecasts)


def brier_skill_score(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
    reference_probability: float = 0.5,
) -> float:
    """Compute the Brier Skill Score relative to an uninformed reference.

    Args:
        forecasts: Predicted probabilities in [0, 1].
        outcomes: Binary outcomes.
        reference_probability: The baseline forecast probability (default 0.5).

    Returns:
        BSS in (-inf, 1]. Positive = better than baseline; 1.0 = perfect.
    """
    bs = brier_score(forecasts, outcomes)
    bs_ref = brier_score(
        [reference_probability] * len(outcomes),
        outcomes,
    )
    if bs_ref == 0.0:
        return 1.0 if bs == 0.0 else float("-inf")
    return 1.0 - (bs / bs_ref)


def calibration_curve(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
    n_bins: int = 5,
) -> list[dict]:
    """Bucket forecasts into probability bins and compute mean forecast vs mean outcome.

    Useful for plotting a reliability (calibration) diagram.

    Args:
        forecasts: Predicted probabilities in [0, 1].
        outcomes: Binary outcomes.
        n_bins: Number of equally-spaced bins (default 5).

    Returns:
        List of dicts with keys:
            bin_lower, bin_upper, mean_forecast, mean_outcome, count
    """
    if len(forecasts) != len(outcomes):
        raise ValueError("forecasts and outcomes must have the same length")

    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]

    for f, o in zip(forecasts, outcomes):
        idx = min(int(f * n_bins), n_bins - 1)
        bins[idx].append((f, o))

    result = []
    for i, bucket in enumerate(bins):
        lower = i / n_bins
        upper = (i + 1) / n_bins
        if bucket:
            mean_f = sum(f for f, _ in bucket) / len(bucket)
            mean_o = sum(o for _, o in bucket) / len(bucket)
            count = len(bucket)
        else:
            mean_f = (lower + upper) / 2
            mean_o = float("nan")
            count = 0
        result.append(
            {
                "bin_lower": lower,
                "bin_upper": upper,
                "mean_forecast": mean_f,
                "mean_outcome": mean_o,
                "count": count,
            }
        )
    return result


def resolution(forecasts: Sequence[float], outcomes: Sequence[int]) -> float:
    """Compute the resolution component of the Brier score decomposition.

    Resolution measures how much the forecast probabilities vary around the
    base rate — higher resolution = more informative forecasts.

    Returns:
        Resolution score >= 0. Higher is better.
    """
    if not outcomes:
        raise ValueError("outcomes must not be empty")
    base_rate = sum(outcomes) / len(outcomes)
    n = len(outcomes)

    bins: dict[float, list[int]] = {}
    for f, o in zip(forecasts, outcomes):
        key = round(f, 2)
        bins.setdefault(key, []).append(o)

    res = 0.0
    for bucket in bins.values():
        n_k = len(bucket)
        o_bar_k = sum(bucket) / n_k
        res += n_k * (o_bar_k - base_rate) ** 2
    return res / n


def brier_index(bs: float) -> float:
    """Convert Brier score to Brier Index (0–100%, intuitive scale).

    Brier Index = (1 - sqrt(BS)) * 100%

    - 50% = always predicting 50/50 (uninformed)
    - 100% = perfect foresight
    - Superforecasters on ForecastBench ≈ 71%
    """
    return (1.0 - math.sqrt(bs)) * 100.0


def calibration_gap(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    """Mean forecast probability minus mean outcome (base rate).

    Positive = systematically underconfident (forecasts lower than reality).
    Negative = systematically overconfident (forecasts higher than reality).
    Near zero = well-calibrated.
    """
    if not forecasts or not outcomes or len(forecasts) != len(outcomes):
        return float("nan")
    return sum(forecasts) / len(forecasts) - sum(outcomes) / len(outcomes)


def decompose_brier(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
) -> dict[str, float]:
    """Full Brier score decomposition: reliability + resolution + uncertainty.

    BS = reliability - resolution + uncertainty

    Returns:
        Dict with keys: brier_score, reliability, resolution, uncertainty,
        bss, brier_index, calibration_gap
    """
    bs = brier_score(forecasts, outcomes)
    base_rate = sum(outcomes) / len(outcomes) if outcomes else 0.5
    uncertainty = base_rate * (1 - base_rate)
    res = resolution(forecasts, outcomes)

    # reliability = BS - uncertainty + resolution
    reliability = bs - uncertainty + res

    bss = brier_skill_score(forecasts, outcomes)
    bi = brier_index(bs)
    cg = calibration_gap(forecasts, outcomes)

    return {
        "brier_score": bs,
        "reliability": max(reliability, 0.0),
        "resolution": res,
        "uncertainty": uncertainty,
        "bss": bss,
        "brier_index": bi,
        "calibration_gap": cg,
    }


def lead_time_points(lead_weeks: float) -> float:
    """Convert lead time (weeks) to prescience points (1 week = 1 point).

    Args:
        lead_weeks: Number of weeks the prediction preceded public validation.

    Returns:
        Point value (non-negative).
    """
    return max(0.0, math.floor(lead_weeks))
