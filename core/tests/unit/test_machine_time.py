"""Tests for MachineTimeEstimator and upgraded PredictionCalibration."""


import pytest

from whitemagic.core.consciousness.machine_time import (
    EffortTier,
    MachineTimeEstimator,
    classify_effort,
    classify_tool,
    crps_gaussian,
)
from whitemagic.core.consciousness.prediction_calibration import (
    PredictionCalibration,
)


@pytest.fixture
def tmp_estimator(tmp_path):
    """Fresh estimator with temp log."""
    log = tmp_path / "machine_time.jsonl"
    return MachineTimeEstimator(log_path=log)


@pytest.fixture
def tmp_calibration(tmp_path):
    """Fresh calibration with temp log."""
    log = tmp_path / "calibration.jsonl"
    return PredictionCalibration(log_path=log)


class TestClassifyTool:
    def test_memory_op(self):
        assert classify_tool("memory.query") == "memory_op"

    def test_polyglot_compute(self):
        assert classify_tool("polyglot.evolution") == "compute"

    def test_session(self):
        assert classify_tool("session.start") == "session"

    def test_unknown(self):
        assert classify_tool("nonexistent.tool") == "unknown"

    def test_garden(self):
        assert classify_tool("garden.joy") == "garden"

    def test_inference(self):
        assert classify_tool("ollama.generate") == "inference"


class TestClassifyEffort:
    def test_trivial(self):
        assert classify_effort(0.005) == EffortTier.TRIVIAL

    def test_quick(self):
        assert classify_effort(5.0) == EffortTier.QUICK

    def test_moderate(self):
        assert classify_effort(30.0) == EffortTier.MODERATE

    def test_extended(self):
        assert classify_effort(300.0) == EffortTier.EXTENDED

    def test_deep(self):
        assert classify_effort(900.0) == EffortTier.DEEP


class TestCRPS:
    def test_perfect_prediction(self):
        """CRPS should be small when prediction == actual."""
        crps = crps_gaussian(1.0, 1.0, 0.1)
        # CRPS at z=0 with sigma=0.1 ≈ 0.0234 (correct for Gaussian)
        assert crps < 0.05

    def test_bad_prediction(self):
        """CRPS should be larger when prediction is far from actual."""
        crps_good = crps_gaussian(1.0, 1.0, 0.1)
        crps_bad = crps_gaussian(10.0, 1.0, 0.1)
        assert crps_bad > crps_good

    def test_non_negative(self):
        """CRPS is a proper scoring rule — always non-negative."""
        for pred in [0.001, 0.1, 1.0, 10.0, 100.0]:
            for actual in [0.001, 0.1, 1.0, 10.0, 100.0]:
                for sigma in [0.01, 0.1, 1.0]:
                    assert crps_gaussian(pred, actual, sigma) >= 0


class TestMachineTimeEstimator:
    def test_predict_no_history(self, tmp_estimator):
        """Prediction with no history should use defaults with low confidence."""
        pred = tmp_estimator.predict("memory.query")
        assert pred.tool_name == "memory.query"
        assert pred.operation_type == "memory_op"
        assert pred.confidence < 0.2
        assert pred.predicted_seconds > 0
        assert pred.tier in EffortTier

    def test_predict_with_history(self, tmp_estimator):
        """After recording data, predictions should use observed medians."""
        for _ in range(10):
            tmp_estimator.record_actual("memory.query", 0.005)
        pred = tmp_estimator.predict("memory.query")
        assert pred.confidence >= 0.5
        assert abs(pred.predicted_seconds - 0.005) < 0.01
        assert pred.sample_count == 10

    def test_record_actual_returns_summary(self, tmp_estimator):
        """record_actual should return a summary with error info."""
        pred = tmp_estimator.predict("memory.query")
        result = tmp_estimator.record_actual("memory.query", 0.003, pred)
        assert "actual_seconds" in result
        assert "predicted_seconds" in result
        assert "crps" in result
        assert "log_ratio_error" in result

    def test_persistence(self, tmp_path):
        """History should load from log file."""
        log = tmp_path / "machine_time.jsonl"
        est1 = MachineTimeEstimator(log_path=log)
        est1.record_actual("test.tool", 0.5)
        est2 = MachineTimeEstimator(log_path=log)
        assert "test.tool" in est2._tool_history
        assert len(est2._tool_history["test.tool"]) == 1

    def test_profile(self, tmp_estimator):
        """get_profile should return tool and type profiles."""
        tmp_estimator.record_actual("memory.query", 0.005)
        tmp_estimator.record_actual("memory.query", 0.003)
        profile = tmp_estimator.get_profile()
        assert "memory.query" in profile["tool_profiles"]
        assert profile["total_observations"] >= 2

    def test_crps_summary_empty(self, tmp_estimator):
        """CRPS summary with no predictions should return count=0."""
        summary = tmp_estimator.get_crps_summary()
        assert summary["count"] == 0

    def test_crps_summary_with_data(self, tmp_estimator):
        """CRPS summary should aggregate CRPS values."""
        pred = tmp_estimator.predict("memory.query")
        tmp_estimator.record_actual("memory.query", 0.005, pred)
        tmp_estimator.record_actual("memory.query", 0.003, pred)
        summary = tmp_estimator.get_crps_summary()
        assert summary["count"] == 2
        assert summary["mean_crps"] >= 0


class TestPredictionCalibrationUpgraded:
    def test_record_auto(self, tmp_calibration):
        """record_auto should store machine-time estimates with CRPS."""
        est = tmp_calibration.record_auto(
            task_id="test-1",
            description="memory.query",
            estimated_seconds_machine=0.005,
            actual_seconds_machine=0.003,
            task_type="memory_op",
        )
        assert est.task_type == "memory_op"
        assert est.estimated_seconds_machine == 0.005
        assert est.actual_seconds_machine == 0.003
        assert est.crps >= 0
        assert len(tmp_calibration.estimates) == 1

    def test_calibration_score_with_machine_time(self, tmp_calibration):
        """get_calibration_score should include CRPS and per-type breakdown."""
        for i in range(5):
            tmp_calibration.record_auto(
                task_id=f"test-{i}",
                description="memory.query",
                estimated_seconds_machine=0.005,
                actual_seconds_machine=0.003 + i * 0.001,
                task_type="memory_op",
            )
        score = tmp_calibration.get_calibration_score()
        assert "mean_crps" in score
        assert "mean_machine_crps" in score
        assert "by_type" in score
        assert "memory_op" in score["by_type"]
        assert score["machine_count"] == 5

    def test_backward_compatible_record_estimate(self, tmp_calibration):
        """Original record_estimate should still work."""
        est = tmp_calibration.record_estimate(
            task_id="test-old",
            description="old-style task",
            estimated_minutes=10.0,
            actual_minutes=2.0,
            depth_layer="flow",
        )
        assert est.compression_ratio == 5.0
        assert est.task_type == "unknown"  # default
        assert est.crps == 0.0  # no machine-time data

    def test_persistence_with_machine_time(self, tmp_path):
        """Machine-time fields should persist to log."""
        log = tmp_path / "calibration.jsonl"
        cal1 = PredictionCalibration(log_path=log)
        cal1.record_auto(
            task_id="test-1",
            description="test",
            estimated_seconds_machine=0.5,
            actual_seconds_machine=0.3,
            task_type="compute",
        )
        cal2 = PredictionCalibration(log_path=log)
        assert len(cal2.estimates) == 1
        est = cal2.estimates[0]
        assert est.task_type == "compute"
        assert est.estimated_seconds_machine == 0.5
        assert est.actual_seconds_machine == 0.3
        assert est.crps >= 0
