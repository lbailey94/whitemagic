# ruff: noqa: BLE001
"""
Confidence Learning System — Calibrates confidence weights from outcomes.

Tracks task outcomes and adjusts confidence factor weights based on
predictive power, enabling the system to learn which factors actually
correlate with success.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class TaskOutcome:
    """Record of a task prediction and its actual result."""

    task_id: str
    task_name: str
    predicted_confidence: float
    actual_success: bool
    factors: dict[str, float]
    category: str = "general"
    notes: str = ""
    timestamp: float = field(default_factory=time.time)


class ConfidenceLearner:
    """Learns and calibrates confidence weights from task outcomes."""

    DEFAULT_WEIGHTS: dict[str, float] = {
        "test_coverage": 0.25,
        "reversibility": 0.20,
        "past_success_rate": 0.25,
        "complexity": 0.10,
        "familiarity": 0.10,
        "risk_level": 0.10,
    }

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "agentic"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.outcomes_file = self.data_dir / "outcomes.jsonl"
        self.weights_file = self.data_dir / "confidence_weights.json"
        self.outcomes: list[TaskOutcome] = []
        self.weights: dict[str, float] = dict(self.DEFAULT_WEIGHTS)
        self._load_outcomes()
        self._load_weights()

    def _load_outcomes(self) -> None:
        if self.outcomes_file.exists():
            for line in self.outcomes_file.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.outcomes.append(TaskOutcome(**d))
                    except Exception:
                        logger.debug("Skipping malformed outcome line")

    def _load_weights(self) -> None:
        if self.weights_file.exists():
            try:
                self.weights = json.loads(self.weights_file.read_text())
            except Exception:
                logger.debug("Using default weights")

    def _save_weights(self) -> None:
        self.weights_file.write_text(json.dumps(self.weights, indent=2))

    def record_outcome(
        self,
        task_id: str,
        task_name: str,
        predicted_confidence: float,
        actual_success: bool,
        factors: dict[str, float],
        category: str = "general",
        notes: str = "",
    ) -> None:
        outcome = TaskOutcome(
            task_id=task_id,
            task_name=task_name,
            predicted_confidence=predicted_confidence,
            actual_success=actual_success,
            factors=factors,
            category=category,
            notes=notes,
        )
        self.outcomes.append(outcome)
        with open(self.outcomes_file, "a") as f:
            f.write(json.dumps(asdict(outcome)) + "\n")
        logger.debug("Recorded outcome for task %s", task_id)

    def auto_calibrate(self, min_samples: int = 10) -> dict[str, float]:
        if len(self.outcomes) < min_samples:
            logger.debug(
                "Not enough outcomes for calibration (%d < %d)",
                len(self.outcomes),
                min_samples,
            )
            return self.weights

        factor_analysis: dict[str, dict[str, float]] = {}
        for factor_name in self.weights:
            correlations: list[float] = []
            for o in self.outcomes:
                val = o.factors.get(factor_name)
                if val is not None:
                    correlations.append(1.0 if o.actual_success else -1.0)
            if correlations:
                mean_corr = sum(correlations) / len(correlations)
                factor_analysis[factor_name] = {"predictive_power": mean_corr}
            else:
                factor_analysis[factor_name] = {"predictive_power": 0.0}

        total_power = sum(abs(a["predictive_power"]) for a in factor_analysis.values())
        if total_power > 0:
            new_weights = {
                f: abs(a["predictive_power"]) / total_power
                for f, a in factor_analysis.items()
            }
        else:
            new_weights = dict(self.weights)

        smoothed: dict[str, float] = {}
        for f in set(list(self.weights.keys()) + list(new_weights.keys())):
            old = self.weights.get(f, 0.5)
            new = new_weights.get(f, 0.5)
            smoothed[f] = 0.8 * old + 0.2 * new

        total = sum(smoothed.values())
        if total > 0:
            smoothed = {k: v / total for k, v in smoothed.items()}

        self.weights = smoothed
        self._save_weights()
        logger.info("Calibrated confidence weights: %s", self.weights)
        return self.weights

    def get_category_stats(self, category: str) -> dict[str, float]:
        cat_outcomes = [o for o in self.outcomes if o.category == category]
        if not cat_outcomes:
            return {
                "total_predictions": 0,
                "accuracy": 0.0,
                "mean_confidence": 0.0,
                "success_rate": 0.0,
            }
        correct = sum(
            1
            for o in cat_outcomes
            if (o.predicted_confidence >= 0.7) == o.actual_success
        )
        successes = sum(1 for o in cat_outcomes if o.actual_success)
        mean_conf = sum(o.predicted_confidence for o in cat_outcomes) / len(
            cat_outcomes
        )
        return {
            "total_predictions": len(cat_outcomes),
            "accuracy": correct / len(cat_outcomes),
            "mean_confidence": mean_conf,
            "success_rate": successes / len(cat_outcomes),
        }


_learner: ConfidenceLearner | None = None


def get_learner(data_dir: Path | None = None) -> ConfidenceLearner:
    global _learner
    if _learner is None:
        _learner = ConfidenceLearner(data_dir)
    return _learner


def record_outcome(
    task_id: str,
    task_name: str,
    predicted_confidence: float,
    actual_success: bool,
    factors: dict[str, float],
    category: str = "general",
    notes: str = "",
) -> None:
    get_learner().record_outcome(
        task_id,
        task_name,
        predicted_confidence,
        actual_success,
        factors,
        category,
        notes,
    )


def auto_calibrate(min_samples: int = 10) -> dict[str, float]:
    return get_learner().auto_calibrate(min_samples)
