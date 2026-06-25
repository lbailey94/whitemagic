"""Tests for Objective R — Predictive Coding for Self-Model."""
from __future__ import annotations

from whitemagic.core.evolution.predictive_coding import (
    PredictiveCodingModel,
)


class TestPredictiveCoding:
    def test_4_layers_initialized(self):
        model = PredictiveCodingModel()
        for i in range(1, 5):
            assert model.get_layer(i) is not None

    def test_set_prediction(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=10.0, confidence=0.8)
        layer = model.get_layer(1)
        assert layer.predicted_value == 10.0
        assert layer.confidence == 0.8

    def test_compute_error(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0)
        pe = model.compute_error(1, actual=7.0)
        assert pe.error == 2.0
        assert pe.squared_error == 4.0

    def test_error_updates_prediction(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0, confidence=1.0)
        model.compute_error(1, actual=7.0)
        # Prediction should shift toward actual
        layer = model.get_layer(1)
        assert layer.predicted_value > 5.0

    def test_anomaly_detection(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0)
        # First few errors establish baseline
        for actual in [5.1, 4.9, 5.0, 5.1, 4.9]:
            model.compute_error(1, actual=actual)
        # Large deviation should be anomalous
        pe = model.compute_error(1, actual=20.0)
        assert pe.anomaly is True

    def test_no_anomaly_for_small_error(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0)
        for actual in [5.1, 4.9, 5.0, 5.1, 4.9]:
            model.compute_error(1, actual=actual)
        pe = model.compute_error(1, actual=5.05)
        assert pe.anomaly is False

    def test_propagate_upward(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0)
        errors = model.propagate_upward(1, actual=20.0)
        assert len(errors) >= 1
        assert errors[0].anomaly is True

    def test_get_anomalies(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0)
        for actual in [5.0, 5.0, 5.0, 5.0, 5.0]:
            model.compute_error(1, actual=actual)
        model.compute_error(1, actual=20.0)
        anomalies = model.get_anomalies()
        assert 1 in anomalies

    def test_anomaly_interpretation(self):
        model = PredictiveCodingModel()
        for layer in range(1, 5):
            interp = model.get_anomaly_interpretation(layer)
            assert isinstance(interp, str)
            assert len(interp) > 10

    def test_stats(self):
        model = PredictiveCodingModel()
        model.set_prediction(1, value=5.0)
        model.compute_error(1, actual=6.0)
        stats = model.get_stats()
        assert "layers" in stats
        assert "any_anomaly" in stats
