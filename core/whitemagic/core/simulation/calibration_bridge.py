"""PredictionCalibrationBridge — Honest Forecasting (P5.5).

Every simulation produces calibrated predictions. Auto-store in
TemporalForecastDB with confidence. Apply calibration adjustment
from historical Brier gap. Resolve against reality. Feed calibration
gap back into simulation parameters. Publish honest scorecard.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """A calibrated prediction from a simulation."""
    id: str
    scenario_name: str
    statement: str
    probability: float  # [0, 1] — predicted probability of occurrence
    confidence: float  # [0, 1] — how confident the simulation is
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    outcome: bool | None = None  # True=occurred, False=did not, None=unresolved
    brier_score: float | None = None
    calibration_adjustment: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def resolve(self, outcome: bool) -> float:
        """Resolve the prediction against reality and compute Brier score.

        Brier score = (predicted_prob - actual_outcome)^2
        Lower is better (0 = perfect, 1 = worst).
        """
        self.outcome = outcome
        self.resolved = True
        actual = 1.0 if outcome else 0.0
        self.brier_score = (self.probability - actual) ** 2
        return self.brier_score


class PredictionCalibrationBridge:
    """Manages calibrated predictions from simulations.

    Pipeline:
    1. Simulation produces predictions with probabilities
    2. Apply historical calibration adjustment (Brier gap)
    3. Store predictions in TemporalForecastDB
    4. When reality arrives, resolve predictions
    5. Compute calibration metrics and feed back into simulations
    6. Publish honest scorecard
    """

    def __init__(self) -> None:
        self._predictions: dict[str, Prediction] = {}
        self._calibration_history: list[float] = []  # historical Brier scores
        self._calibration_gap: float = 0.0  # average Brier gap

    def record_prediction(
        self,
        scenario_name: str,
        statement: str,
        probability: float,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Prediction:
        """Record a new prediction from a simulation.

        Args:
            scenario_name: Name of the simulation scenario.
            statement: What is being predicted.
            probability: Predicted probability [0, 1].
            confidence: Confidence in the prediction [0, 1].
            metadata: Additional metadata.

        Returns:
            The recorded Prediction.
        """
        # Apply calibration adjustment
        adjusted_prob = max(0.0, min(1.0, probability + self._calibration_gap))

        pid = hashlib.sha256(f"{scenario_name}_{statement}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        pred = Prediction(
            id=pid,
            scenario_name=scenario_name,
            statement=statement,
            probability=adjusted_prob,
            confidence=confidence,
            calibration_adjustment=self._calibration_gap,
            metadata=metadata or {},
        )
        self._predictions[pid] = pred
        logger.info("Recorded prediction %s: P=%.2f (adjusted from %.2f)",
                     statement[:50], adjusted_prob, probability)
        return pred

    def resolve_prediction(self, prediction_id: str, outcome: bool) -> dict[str, Any]:
        """Resolve a prediction against reality.

        Args:
            prediction_id: ID of the prediction to resolve.
            outcome: Whether the predicted event occurred.

        Returns:
            Dict with Brier score and updated calibration.
        """
        pred = self._predictions.get(prediction_id)
        if pred is None:
            return {"status": "error", "error": "Prediction not found"}

        brier = pred.resolve(outcome)
        self._calibration_history.append(brier)

        # Update calibration gap (moving average of last 50)
        recent = self._calibration_history[-50:]
        avg_brier = sum(recent) / len(recent)
        self._calibration_gap = avg_brier * 0.1  # small adjustment

        return {
            "status": "success",
            "prediction_id": prediction_id,
            "brier_score": brier,
            "calibration_gap": self._calibration_gap,
            "resolved": pred.resolved,
        }

    def get_scorecard(self) -> dict[str, Any]:
        """Publish an honest scorecard of prediction performance."""
        resolved = [p for p in self._predictions.values() if p.resolved]
        unresolved = [p for p in self._predictions.values() if not p.resolved]

        brier_scores = [p.brier_score for p in resolved if p.brier_score is not None]
        avg_brier = sum(brier_scores) / max(len(brier_scores), 1)

        # Calibration analysis: bin predictions by probability range
        bins = {f"{i/10:.1f}-{(i+1)/10:.1f}": {"count": 0, "actual_rate": 0.0}
                for i in range(10)}
        for p in resolved:
            bin_idx = min(int(p.probability * 10), 9)
            bin_key = f"{bin_idx/10:.1f}-{(bin_idx+1)/10:.1f}"
            bins[bin_key]["count"] += 1
            bins[bin_key]["actual_rate"] += 1.0 if p.outcome else 0.0

        for bin_key, bin_data in bins.items():
            if bin_data["count"] > 0:
                bin_data["actual_rate"] /= bin_data["count"]

        return {
            "total_predictions": len(self._predictions),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "avg_brier_score": avg_brier,
            "calibration_gap": self._calibration_gap,
            "calibration_bins": bins,
            "perfect_calibration": avg_brier < 0.05,
            "good_calibration": avg_brier < 0.15,
        }

    def get_prediction(self, prediction_id: str) -> Prediction | None:
        return self._predictions.get(prediction_id)

    def list_predictions(self, resolved: bool | None = None) -> list[Prediction]:
        if resolved is None:
            return list(self._predictions.values())
        return [p for p in self._predictions.values() if p.resolved == resolved]

    def stats(self) -> dict[str, Any]:
        return {
            "total_predictions": len(self._predictions),
            "resolved": sum(1 for p in self._predictions.values() if p.resolved),
            "calibration_gap": self._calibration_gap,
            "history_length": len(self._calibration_history),
        }


# Singleton
_bridge: PredictionCalibrationBridge | None = None


def get_calibration_bridge() -> PredictionCalibrationBridge:
    global _bridge
    if _bridge is None:
        _bridge = PredictionCalibrationBridge()
    return _bridge
