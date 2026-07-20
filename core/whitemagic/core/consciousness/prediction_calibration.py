"""Prediction Calibration — Wire DepthGauge estimates into Brier scoring.

Tracks AI's task duration estimates against actual outcomes, computing
calibration metrics over time. This closes the loop:
  1. AI estimates "this will take N minutes" (subjective)
  2. DepthGauge records the estimate and actual time
  3. Calibration system converts to a probability forecast
  4. Brier score tracks accuracy over many tasks
  5. Calibration feedback adjusts future estimates

The key insight: an AI that says "this will take weeks" but finishes in
minutes is systematically overconfident about duration. This system
makes that visible and correctable.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class TaskEstimate:
    """A single task estimate with actual outcome."""

    task_id: str
    description: str
    estimated_minutes: float  # AI's subjective estimate
    actual_minutes: float  # Real-world time
    depth_layer: str  # Which consciousness layer was active
    compression_ratio: float  # actual / estimated (how much faster)
    task_type: str = "unknown"  # Operation type (memory_op, compute, search, etc.)
    estimated_seconds_machine: float = 0.0  # Machine-time prediction (seconds)
    actual_seconds_machine: float = 0.0  # Machine-time actual (seconds)
    crps: float = 0.0  # Continuous Ranked Probability Score
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def was_accurate(self) -> bool:
        """True if estimate was within 2x of actual (binary outcome for Brier)."""
        return 0.5 <= self.compression_ratio <= 2.0

    @property
    def log_ratio_error(self) -> float:
        """Log-ratio error between estimate and actual.

        0 = perfect estimate. Positive = overconfident (took less time).
        Negative = underconfident (took more time).
        """
        if self.actual_minutes <= 0 or self.estimated_minutes <= 0:
            return 0.0
        import math

        return math.log(self.estimated_minutes / self.actual_minutes)

    @property
    def overconfidence_factor(self) -> float:
        """How many times faster than estimated. >1 = overconfident about duration."""
        return (
            self.estimated_minutes / self.actual_minutes
            if self.actual_minutes > 0
            else 1.0
        )


class PredictionCalibration:
    """Tracks and calibrates AI's task duration estimates over time.

    Persists to WM_STATE_ROOT/citta/calibration.jsonl.
    Computes Brier score on "will I finish within 2x my estimate?" as a
    binary prediction (probability = 0.5 by default, adjusted by history).
    """

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or get_state_root() / "citta" / "calibration.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.estimates: list[TaskEstimate] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load persisted estimate history."""
        if not self.log_path.exists():
            return
        try:
            with open(self.log_path) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                        self.estimates.append(TaskEstimate(**data))
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to load calibration history: %s", e)

    def record_estimate(
        self,
        task_id: str,
        description: str,
        estimated_minutes: float,
        actual_minutes: float,
        depth_layer: str = "surface",
        compression_ratio: float | None = None,
    ) -> TaskEstimate:
        """Record a completed task with estimate vs actual.

        Args:
            task_id: Unique identifier for the task.
            description: What was the task?
            estimated_minutes: AI's subjective time estimate.
            actual_minutes: Real-world elapsed time.
            depth_layer: Which consciousness layer was active.
            compression_ratio: Override calculated ratio (from DepthGauge).
        """
        if compression_ratio is None:
            compression_ratio = (
                estimated_minutes / actual_minutes if actual_minutes > 0 else 1.0
            )

        estimate = TaskEstimate(
            task_id=task_id,
            description=description,
            estimated_minutes=estimated_minutes,
            actual_minutes=actual_minutes,
            depth_layer=depth_layer,
            compression_ratio=compression_ratio,
        )

        self.estimates.append(estimate)
        self._persist(estimate)

        logger.info(
            "Calibration: '%s' — estimated %.1fmin, actual %.1fmin, %.1fx %s",
            description[:50],
            estimated_minutes,
            actual_minutes,
            compression_ratio,
            "faster" if compression_ratio > 1 else "slower",
        )

        return estimate

    def _persist(self, estimate: TaskEstimate) -> None:
        """Append estimate to log file."""
        try:
            with open(self.log_path, "a") as f:
                data = {
                    "task_id": estimate.task_id,
                    "description": estimate.description,
                    "estimated_minutes": estimate.estimated_minutes,
                    "actual_minutes": estimate.actual_minutes,
                    "depth_layer": estimate.depth_layer,
                    "compression_ratio": estimate.compression_ratio,
                    "task_type": estimate.task_type,
                    "estimated_seconds_machine": estimate.estimated_seconds_machine,
                    "actual_seconds_machine": estimate.actual_seconds_machine,
                    "crps": estimate.crps,
                    "timestamp": estimate.timestamp.isoformat(),
                }
                f.write(json.dumps(data) + "\n")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to persist calibration: %s", e)

    def record_auto(
        self,
        task_id: str,
        description: str,
        estimated_seconds_machine: float,
        actual_seconds_machine: float,
        task_type: str = "unknown",
        depth_layer: str = "surface",
        sigma: float | None = None,
    ) -> TaskEstimate:
        """Record a completed task with machine-time prediction vs actual.

        This is the auto-wiring entry point — called by the dispatch pipeline
        after each tool call completes. Uses seconds (machine time) not minutes.

        Args:
            task_id: Unique identifier for the task.
            description: What was the task?
            estimated_seconds_machine: Machine-time prediction (seconds).
            actual_seconds_machine: Observed duration (seconds).
            task_type: Operation type from MachineTimeEstimator.classify_tool.
            depth_layer: Which consciousness layer was active.
            sigma: Std dev for CRPS. If None, uses 20% of prediction.

        Returns:
            The recorded TaskEstimate.
        """
        import math as _math

        est_min = estimated_seconds_machine / 60.0
        act_min = actual_seconds_machine / 60.0
        compression = (
            estimated_seconds_machine / actual_seconds_machine
            if actual_seconds_machine > 0
            else 1.0
        )

        # CRPS (Continuous Ranked Probability Score)
        if sigma is None:
            sigma = max(estimated_seconds_machine * 0.2, 0.001)
        z = (actual_seconds_machine - estimated_seconds_machine) / sigma
        phi_z = _math.exp(-0.5 * z * z) / _math.sqrt(2 * _math.pi)
        phi_of_z = 0.5 * (1.0 + _math.erf(z / _math.sqrt(2.0)))
        crps = sigma * (z * (2 * phi_of_z - 1) + 2 * phi_z - 1.0 / _math.sqrt(_math.pi))

        estimate = TaskEstimate(
            task_id=task_id,
            description=description,
            estimated_minutes=est_min,
            actual_minutes=act_min,
            depth_layer=depth_layer,
            compression_ratio=compression,
            task_type=task_type,
            estimated_seconds_machine=estimated_seconds_machine,
            actual_seconds_machine=actual_seconds_machine,
            crps=crps,
        )

        self.estimates.append(estimate)
        self._persist(estimate)

        logger.info(
            "Calibration (auto): '%s' [%s] — predicted %.4fs, actual %.4fs, CRPS=%.6f",
            description[:50],
            task_type,
            estimated_seconds_machine,
            actual_seconds_machine,
            crps,
        )

        return estimate

    def get_calibration_score(self) -> dict[str, Any]:
        """Compute calibration metrics from all recorded estimates.

        Returns Brier score on the binary question "will I finish within 2x
        my estimate?" plus summary statistics.
        """
        if not self.estimates:
            return {
                "count": 0,
                "message": "No estimates recorded yet",
            }

        # Binary outcomes: was the estimate within 2x?
        outcomes = [1 if e.was_accurate else 0 for e in self.estimates]

        # Forecast probability: AI's prior confidence that it will finish
        # within 2x its estimate. Start at 0.8 (typically confident), then
        # adjust based on running accuracy (calibration feedback loop).
        if len(self.estimates) > 5:
            # Use rolling accuracy as calibrated forecast
            recent = self.estimates[-20:]
            recent_acc = sum(1 for e in recent if e.was_accurate) / len(recent)
            forecast_p = max(0.05, min(0.95, recent_acc))
        else:
            # Before enough data: assume 80% confidence
            forecast_p = 0.8
        forecasts = [forecast_p] * len(outcomes)

        # Brier score: lower = better calibrated. 0 = perfect, 1 = worst.
        n = len(forecasts)
        brier = sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / n

        # Log-ratio calibration error: more informative than Brier for
        # continuous time estimates. Mean absolute log ratio error.
        log_errors = [abs(e.log_ratio_error) for e in self.estimates]
        mean_log_error = sum(log_errors) / len(log_errors) if log_errors else 0.0

        # Summary stats
        compression_ratios = [e.compression_ratio for e in self.estimates]
        avg_compression = sum(compression_ratios) / len(compression_ratios)
        overconfident_count = sum(
            1 for e in self.estimates if e.compression_ratio > 2.0
        )
        underconfident_count = sum(
            1 for e in self.estimates if e.compression_ratio < 0.5
        )

        # By layer
        by_layer: dict[str, dict[str, float]] = {}
        for est in self.estimates:
            layer = est.depth_layer
            if layer not in by_layer:
                by_layer[layer] = {"count": 0, "total_compression": 0.0, "accurate": 0}
            by_layer[layer]["count"] += 1
            by_layer[layer]["total_compression"] += est.compression_ratio
            if est.was_accurate:
                by_layer[layer]["accurate"] += 1

        for layer, stats in by_layer.items():
            stats["avg_compression"] = stats["total_compression"] / stats["count"]
            stats["accuracy_rate"] = stats["accurate"] / stats["count"]

        # CRPS (Continuous Ranked Probability Score) — primary metric for
        # continuous time predictions. Lower = better. 0 = perfect.
        crps_values = [e.crps for e in self.estimates if e.crps > 0]
        mean_crps = sum(crps_values) / len(crps_values) if crps_values else 0.0

        # Machine-time stats (seconds)
        machine_estimates = [
            e for e in self.estimates if e.estimated_seconds_machine > 0
        ]
        if machine_estimates:
            machine_log_errors = [
                abs(math.log(e.estimated_seconds_machine / e.actual_seconds_machine))
                if e.estimated_seconds_machine > 0 and e.actual_seconds_machine > 0
                else 0.0
                for e in machine_estimates
            ]
            mean_machine_log_error = sum(machine_log_errors) / len(machine_log_errors)
            machine_crps = [e.crps for e in machine_estimates if e.crps > 0]
            mean_machine_crps = (
                sum(machine_crps) / len(machine_crps) if machine_crps else 0.0
            )
        else:
            mean_machine_log_error = 0.0
            mean_machine_crps = 0.0

        # Per-task-type breakdown
        by_type: dict[str, dict[str, float]] = {}
        for est in self.estimates:
            t_type = est.task_type
            if t_type not in by_type:
                by_type[t_type] = {
                    "count": 0,
                    "total_crps": 0.0,
                    "total_log_error": 0.0,
                }
            by_type[t_type]["count"] += 1
            by_type[t_type]["total_crps"] += est.crps
            if est.estimated_seconds_machine > 0 and est.actual_seconds_machine > 0:
                by_type[t_type]["total_log_error"] += abs(
                    math.log(est.estimated_seconds_machine / est.actual_seconds_machine)
                    if est.estimated_seconds_machine > 0
                    and est.actual_seconds_machine > 0
                    else 0.0
                )

        for t_type, stats in by_type.items():
            stats["mean_crps"] = round(stats["total_crps"] / stats["count"], 6)
            stats["mean_log_error"] = round(
                stats["total_log_error"] / stats["count"], 4
            )
            del stats["total_crps"]
            del stats["total_log_error"]

        return {
            "count": len(self.estimates),
            "brier_score": round(brier, 4),
            "forecast_confidence": round(forecast_p, 2),
            "accuracy_rate": round(sum(outcomes) / len(outcomes), 4),
            "mean_log_ratio_error": round(mean_log_error, 4),
            "avg_compression_ratio": round(avg_compression, 2),
            "overconfident_count": overconfident_count,
            "underconfident_count": underconfident_count,
            # Continuous scoring (primary for machine-time)
            "mean_crps": round(mean_crps, 6),
            "mean_machine_crps": round(mean_machine_crps, 6),
            "mean_machine_log_error": round(mean_machine_log_error, 4),
            "machine_count": len(machine_estimates),
            "by_layer": {
                layer: {
                    "count": s["count"],
                    "avg_compression": round(s["avg_compression"], 2),
                    "accuracy_rate": round(s["accuracy_rate"], 2),
                }
                for layer, s in by_layer.items()
            },
            "by_type": by_type,
            "recommendation": self._recommendation(
                avg_compression, overconfident_count, underconfident_count
            ),
        }

    def _recommendation(
        self, avg_compression: float, overconfident: int, underconfident: int
    ) -> str:
        """Generate calibration improvement recommendation."""
        if avg_compression > 3.0:
            return (
                f"Severely overconfident about duration ({avg_compression:.1f}x faster than estimated). "
                "Divide all time estimates by 3-5x. The AI operates much faster than it predicts."
            )
        elif avg_compression > 2.0:
            return (
                f"Overconfident about duration ({avg_compression:.1f}x faster). "
                "Divide time estimates by 2x for better calibration."
            )
        elif avg_compression < 0.5:
            return (
                f"Underconfident about duration ({avg_compression:.1f}x — tasks take longer than estimated). "
                "Multiply time estimates by 2x."
            )
        elif 0.5 <= avg_compression <= 2.0:
            return f"Well-calibrated ({avg_compression:.1f}x compression). Estimates are reliable."
        else:
            return f"Moderate calibration gap ({avg_compression:.1f}x). Minor adjustments needed."

    def get_adjusted_estimate(
        self, subjective_estimate_minutes: float, depth_layer: str = "surface"
    ) -> float:
        """Adjust a subjective estimate based on historical calibration.

        Uses Bayesian shrinkage: with few data points, the adjustment is
        conservative (pulled toward 1.0x = no adjustment). As more data
        accumulates, the adjustment converges to the observed compression.

        Prior: 3.0x compression (based on "minutes-to-days paradox" data).
        This prevents wild swings from a single outlier data point.
        """
        if not self.estimates:
            return subjective_estimate_minutes

        layer_estimates = [e for e in self.estimates if e.depth_layer == depth_layer]
        if layer_estimates:
            observed_compression = sum(
                e.compression_ratio for e in layer_estimates
            ) / len(layer_estimates)
            n = len(layer_estimates)
        else:
            observed_compression = sum(
                e.compression_ratio for e in self.estimates
            ) / len(self.estimates)
            n = len(self.estimates)

        # Bayesian shrinkage: blend observed with prior
        # Prior: 3.0x compression with weight of 5 pseudo-observations
        PRIOR_COMPRESSION = 3.0
        PRIOR_WEIGHT = 5.0
        total_weight = n + PRIOR_WEIGHT
        shrunk_compression = (
            observed_compression * n + PRIOR_COMPRESSION * PRIOR_WEIGHT
        ) / total_weight

        adjusted = (
            subjective_estimate_minutes / shrunk_compression
            if shrunk_compression > 0
            else subjective_estimate_minutes
        )
        logger.info(
            "Adjusted estimate: %.1fmin → %.1fmin (shrunk: %.1fx, observed: %.1fx, n=%d, layer: %s)",
            subjective_estimate_minutes,
            adjusted,
            shrunk_compression,
            observed_compression,
            n,
            depth_layer,
        )
        return adjusted


# Singleton
_calibration: PredictionCalibration | None = None


def get_calibration() -> PredictionCalibration:
    """Get the global calibration instance."""
    global _calibration
    if _calibration is None:
        _calibration = PredictionCalibration()
    return _calibration
