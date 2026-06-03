"""WhiteMagic Forecasting Module.

Tracks predictions over time, scores them against public validation events
using Brier scoring, and computes the prescience calibration curve.
"""

from whitemagic.forecasting.brier import brier_score, brier_skill_score, calibration_curve
from whitemagic.forecasting.temporal_db import TemporalForecastDB
from whitemagic.forecasting.tzpf import compute_tzpf

__all__ = [
    "TemporalForecastDB",
    "brier_score",
    "brier_skill_score",
    "calibration_curve",
    "compute_tzpf",
]
