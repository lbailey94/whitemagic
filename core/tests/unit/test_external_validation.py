"""Tests for Objective X — External Cross-Validation."""

from __future__ import annotations

from pathlib import Path

from whitemagic.core.evolution.external_validation import (
    EXTERNAL_BASELINES,
    ExternalValidator,
)
from whitemagic.core.memory.db_manager import safe_connect


def _make_test_db(db_path: Path, n_outcomes: int = 20) -> None:
    """Create a test feedback.db with sample outcomes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = safe_connect(str(db_path))
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS pattern_applications (
            application_id TEXT PRIMARY KEY,
            pattern_id TEXT,
            pattern_type TEXT,
            timestamp REAL,
            initial_confidence REAL,
            context TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pattern_outcomes (
            application_id TEXT,
            pattern_id TEXT,
            success INTEGER,
            performance_gain REAL,
            quality_score REAL,
            user_feedback TEXT,
            measured_at REAL,
            metrics TEXT
        )
    """)

    import time

    base_time = time.time()

    for i in range(n_outcomes):
        app_id = f"app_{i}"
        pattern_id = f"pattern_{i % 5}"
        confidence = 0.6 + (i % 3) * 0.1
        success = 1 if i % 3 != 2 else 0

        c.execute(
            "INSERT INTO pattern_applications VALUES (?, ?, ?, ?, ?, ?)",
            (app_id, pattern_id, "test", base_time + i, confidence, "{}"),
        )
        c.execute(
            "INSERT INTO pattern_outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (app_id, pattern_id, success, None, None, None, base_time + i, "{}"),
        )

    conn.commit()
    conn.close()


class TestCrossValidation:
    def test_insufficient_data(self, tmp_path):
        validator = ExternalValidator(db_path=tmp_path / "test.db")
        result = validator.cross_validate()
        assert result.train_size == 0
        assert result.validation_size == 0
        assert "error" in result.metadata

    def test_basic_split(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        _make_test_db(db_path, n_outcomes=20)
        validator = ExternalValidator(db_path=db_path)
        result = validator.cross_validate(split_ratio=0.7)
        assert result.train_size == 14
        assert result.validation_size == 6
        assert 0.0 <= result.train_success_rate <= 1.0
        assert 0.0 <= result.validation_success_rate <= 1.0

    def test_overfitting_detection(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        _make_test_db(db_path, n_outcomes=20)
        validator = ExternalValidator(db_path=db_path)
        result = validator.cross_validate()
        # With our test data, overfitting gap should be computed
        assert isinstance(result.overfitting_detected, bool)
        assert isinstance(result.overfitting_gap, float)

    def test_confidence_calibration(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        _make_test_db(db_path, n_outcomes=20)
        validator = ExternalValidator(db_path=db_path)
        result = validator.cross_validate()
        assert isinstance(result.train_confidence, float)
        assert isinstance(result.validation_confidence, float)
        assert isinstance(result.confidence_calibration_gap, float)


class TestAdversarialTests:
    def test_flip_predictions_with_data(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        _make_test_db(db_path, n_outcomes=20)
        validator = ExternalValidator(db_path=db_path)
        result = validator.adversarial_test_flip_predictions()
        assert result.test_name == "flip_predictions"
        assert isinstance(result.passed, bool)
        assert "original_brier" in result.metadata

    def test_flip_predictions_insufficient(self, tmp_path):
        validator = ExternalValidator(db_path=tmp_path / "test.db")
        result = validator.adversarial_test_flip_predictions()
        assert result.passed is False
        assert "Insufficient" in result.description

    def test_random_baseline_with_data(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        _make_test_db(db_path, n_outcomes=20)
        validator = ExternalValidator(db_path=db_path)
        result = validator.adversarial_test_random_baseline()
        assert result.test_name == "random_baseline"
        assert isinstance(result.passed, bool)
        assert result.metadata["random_brier"] == 0.25

    def test_random_baseline_insufficient(self, tmp_path):
        validator = ExternalValidator(db_path=tmp_path / "test.db")
        result = validator.adversarial_test_random_baseline()
        assert result.passed is False


class TestFullValidation:
    def test_full_report_with_data(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        _make_test_db(db_path, n_outcomes=20)
        validator = ExternalValidator(db_path=db_path)
        report = validator.run_full_validation()
        assert report.cross_validation is not None
        assert len(report.adversarial_tests) == 2
        assert "random_brier_score" in report.external_baselines
        assert isinstance(report.self_assessment_match, bool)
        assert len(report.summary) > 0

    def test_full_report_no_data(self, tmp_path):
        validator = ExternalValidator(db_path=tmp_path / "test.db")
        report = validator.run_full_validation()
        assert report.cross_validation is not None
        assert report.cross_validation.train_size == 0
        assert "Insufficient" in report.summary


class TestExternalBaselines:
    def test_baselines_defined(self):
        assert "random_success_rate" in EXTERNAL_BASELINES
        assert "random_brier_score" in EXTERNAL_BASELINES
        assert EXTERNAL_BASELINES["random_brier_score"] == 0.25
        assert EXTERNAL_BASELINES["perfect_brier_score"] == 0.0
