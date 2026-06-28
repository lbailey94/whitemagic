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
import time
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
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def was_accurate(self) -> bool:
        """True if estimate was within 2x of actual (binary outcome for Brier)."""
        return 0.5 <= self.compression_ratio <= 2.0

    @property
    def overconfidence_factor(self) -> float:
        """How many times faster than estimated. >1 = overconfident about duration."""
        return self.estimated_minutes / self.actual_minutes if self.actual_minutes > 0 else 1.0


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
        except Exception as e:
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
                estimated_minutes / actual_minutes
                if actual_minutes > 0
                else 1.0
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
                    "timestamp": estimate.timestamp.isoformat(),
                }
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.warning("Failed to persist calibration: %s", e)

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

        # Forecast probability: our default confidence before calibration
        # Start at 0.5 (uninformed), adjust based on running accuracy
        base_rate = sum(outcomes) / len(outcomes)
        forecasts = [base_rate] * len(outcomes)

        # Brier score
        n = len(forecasts)
        brier = sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / n

        # Summary stats
        compression_ratios = [e.compression_ratio for e in self.estimates]
        avg_compression = sum(compression_ratios) / len(compression_ratios)
        overconfident_count = sum(1 for e in self.estimates if e.compression_ratio > 2.0)
        underconfident_count = sum(1 for e in self.estimates if e.compression_ratio < 0.5)

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

        return {
            "count": len(self.estimates),
            "brier_score": round(brier, 4),
            "accuracy_rate": round(base_rate, 4),
            "avg_compression_ratio": round(avg_compression, 2),
            "overconfident_count": overconfident_count,
            "underconfident_count": underconfident_count,
            "by_layer": {
                layer: {
                    "count": s["count"],
                    "avg_compression": round(s["avg_compression"], 2),
                    "accuracy_rate": round(s["accuracy_rate"], 2),
                }
                for layer, s in by_layer.items()
            },
            "recommendation": self._recommendation(avg_compression, overconfident_count, underconfident_count),
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

        Uses the average compression ratio for the given layer to produce
        a better-calibrated estimate.
        """
        if not self.estimates:
            return subjective_estimate_minutes

        # Get layer-specific compression if available
        layer_estimates = [e for e in self.estimates if e.depth_layer == depth_layer]
        if layer_estimates:
            avg_compression = sum(e.compression_ratio for e in layer_estimates) / len(layer_estimates)
        else:
            avg_compression = sum(e.compression_ratio for e in self.estimates) / len(self.estimates)

        adjusted = subjective_estimate_minutes / avg_compression if avg_compression > 0 else subjective_estimate_minutes
        logger.info(
            "Adjusted estimate: %.1fmin → %.1fmin (compression: %.1fx, layer: %s)",
            subjective_estimate_minutes,
            adjusted,
            avg_compression,
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
