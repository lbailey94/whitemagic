"""Predictive Coding for Self-Model (Objective R).

Implements hierarchical predictive coding — a multi-layer generative model
where each layer predicts the layer below and computes prediction errors.

Layers:
  1. Operational: "I expect N untitled memories, M untagged memories"
  2. Strategic: "I expect kaizen to find quality issues in cycle N"
  3. Meta-cognitive: "I expect my predictions to be calibrated (Brier < 0.2)"
  4. Self-referential: "I expect my improvement rate to be increasing"

Each layer sends prediction errors upward and predictions downward.
Anomalies at each level have different implications.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PredictionError:
    """A single prediction error at a specific layer."""

    layer: int
    layer_name: str
    predicted: float
    actual: float
    error: float  # actual - predicted
    squared_error: float
    timestamp: float = 0.0
    anomaly: bool = False  # True if error exceeds threshold


@dataclass
class LayerState:
    """State of a single predictive coding layer."""

    layer: int
    name: str
    predicted_value: float = 0.0
    confidence: float = 0.5
    error_history: list[PredictionError] = field(default_factory=list)
    anomaly_threshold: float = 2.0  # Std devs from expected

    @property
    def mean_error(self) -> float:
        if not self.error_history:
            return 0.0
        return sum(e.error for e in self.error_history) / len(self.error_history)

    @property
    def error_variance(self) -> float:
        if len(self.error_history) < 2:
            return 0.0
        mean = self.mean_error
        return sum((e.error - mean) ** 2 for e in self.error_history) / (
            len(self.error_history) - 1
        )

    @property
    def is_anomalous(self) -> bool:
        """True if the most recent error exceeds the anomaly threshold."""
        if not self.error_history:
            return False
        return self.error_history[-1].anomaly


class PredictiveCodingModel:
    """4-layer hierarchical predictive coding for self-modeling.

    Each layer predicts the layer below. Prediction errors propagate
    upward and drive system adjustments.
    """

    def __init__(self) -> None:
        self._layers: dict[int, LayerState] = {
            1: LayerState(
                layer=1, name="operational", predicted_value=0.0, anomaly_threshold=2.0
            ),
            2: LayerState(
                layer=2, name="strategic", predicted_value=0.0, anomaly_threshold=2.0
            ),
            3: LayerState(
                layer=3,
                name="meta_cognitive",
                predicted_value=0.2,
                anomaly_threshold=1.5,
            ),
            4: LayerState(
                layer=4,
                name="self_referential",
                predicted_value=0.0,
                anomaly_threshold=2.0,
            ),
        }

    def set_prediction(self, layer: int, value: float, confidence: float = 0.5) -> None:
        """Set the prediction for a layer.

        Args:
            layer: Layer number (1-4).
            value: Predicted value.
            confidence: Confidence in the prediction (0-1).
        """
        if layer in self._layers:
            self._layers[layer].predicted_value = value
            self._layers[layer].confidence = confidence

    def compute_error(
        self, layer: int, actual: float, timestamp: float = 0.0
    ) -> PredictionError:
        """Compute prediction error for a layer.

        Args:
            layer: Layer number (1-4).
            actual: Actual observed value.
            timestamp: Optional timestamp.

        Returns:
            PredictionError with computed error and anomaly flag.
        """
        state = self._layers.get(layer)
        if state is None:
            return PredictionError(
                layer=layer,
                layer_name="unknown",
                predicted=0.0,
                actual=actual,
                error=actual,
                squared_error=actual**2,
            )

        error = actual - state.predicted_value
        squared = error**2

        anomaly = False
        if state.error_variance > 0:
            z_score = abs(error) / math.sqrt(state.error_variance)
            anomaly = z_score > state.anomaly_threshold
        elif (
            abs(error) > state.anomaly_threshold * 0.1
        ):  # No history → use raw threshold
            anomaly = True

        pe = PredictionError(
            layer=layer,
            layer_name=state.name,
            predicted=state.predicted_value,
            actual=actual,
            error=error,
            squared_error=squared,
            timestamp=timestamp,
            anomaly=anomaly,
        )
        state.error_history.append(pe)

        # Update prediction using simple exponential smoothing
        alpha = 0.1 * state.confidence
        state.predicted_value = state.predicted_value + alpha * error

        return pe

    def propagate_upward(self, layer: int, actual: float) -> list[PredictionError]:
        """Compute error at a layer and propagate upward.

        Lower layer errors inform higher layer predictions.

        Args:
            layer: Starting layer (1-3, can't propagate from 4).
            actual: Actual observed value.

        Returns:
            List of prediction errors generated (one per layer touched).
        """
        errors = []
        pe = self.compute_error(layer, actual)
        errors.append(pe)

        # Propagate to next layer up
        if layer < 4 and pe.anomaly:
            # Anomaly at lower layer → adjust upper layer prediction
            upper = self._layers.get(layer + 1)
            if upper:
                # Upper layer's prediction is adjusted by the error
                adjustment = pe.error * 0.3
                upper.predicted_value += adjustment

        return errors

    def get_layer(self, layer: int) -> LayerState | None:
        return self._layers.get(layer)

    def get_anomalies(self) -> dict[int, bool]:
        """Get anomaly status for all layers."""
        return {layer: state.is_anomalous for layer, state in self._layers.items()}

    def get_anomaly_interpretation(self, layer: int) -> str:
        """Get human-readable interpretation of an anomaly at a layer.

        Args:
            layer: Layer number (1-4).

        Returns:
            Description string.
        """
        interpretations = {
            1: "Operational anomaly: something is wrong with the system's basic metrics",
            2: "Strategic anomaly: kaizen isn't finding enough improvements — exploration may be stagnating",
            3: "Meta-cognitive anomaly: predictions are poorly calibrated — MC engine needs recalibration",
            4: "Self-referential anomaly: the improvement loop itself may be degrading",
        }
        return interpretations.get(layer, "Unknown anomaly")

    def get_stats(self) -> dict[str, Any]:
        return {
            "layers": {
                str(layer): {
                    "name": state.name,
                    "predicted": state.predicted_value,
                    "mean_error": state.mean_error,
                    "error_variance": state.error_variance,
                    "is_anomalous": state.is_anomalous,
                    "error_count": len(state.error_history),
                }
                for layer, state in self._layers.items()
            },
            "any_anomaly": any(state.is_anomalous for state in self._layers.values()),
        }
