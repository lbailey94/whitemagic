"""Tests for the forecasting module — brier.py and temporal_db.py."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pytest

from whitemagic.forecasting.brier import (
    brier_score,
    brier_skill_score,
    calibration_curve,
    decompose_brier,
    lead_time_points,
    resolution,
)
from whitemagic.forecasting.temporal_db import TemporalForecastDB

# ---------------------------------------------------------------------------
# brier.py tests
# ---------------------------------------------------------------------------


class TestBrierScore:
    def test_perfect_forecast(self):
        assert brier_score([1.0, 1.0, 0.0, 0.0], [1, 1, 0, 0]) == pytest.approx(0.0)

    def test_worst_forecast(self):
        assert brier_score([0.0, 0.0, 1.0, 1.0], [1, 1, 0, 0]) == pytest.approx(1.0)

    def test_uninformed(self):
        assert brier_score([0.5, 0.5, 0.5, 0.5], [1, 1, 0, 0]) == pytest.approx(0.25)

    def test_single_correct(self):
        assert brier_score([1.0], [1]) == pytest.approx(0.0)

    def test_single_incorrect(self):
        assert brier_score([1.0], [0]) == pytest.approx(1.0)

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            brier_score([0.5, 0.5], [1])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            brier_score([], [])

    def test_high_confidence_correct_is_good(self):
        bs = brier_score([0.9] * 10, [1] * 10)
        assert bs < 0.05


class TestBrierSkillScore:
    def test_perfect_skill(self):
        bss = brier_skill_score([1.0] * 4, [1, 1, 1, 1])
        assert bss == pytest.approx(1.0)

    def test_uninformed_has_zero_skill(self):
        bss = brier_skill_score([0.5, 0.5], [1, 0])
        assert bss == pytest.approx(0.0)

    def test_skilled_forecaster_positive(self):
        bss = brier_skill_score([0.9, 0.9, 0.1, 0.1], [1, 1, 0, 0])
        assert bss > 0

    def test_custom_reference_probability(self):
        bss = brier_skill_score([0.8], [1], reference_probability=0.5)
        assert bss > 0


class TestCalibrationCurve:
    def test_returns_n_bins(self):
        curve = calibration_curve([0.1, 0.5, 0.9], [0, 1, 1], n_bins=3)
        assert len(curve) == 3

    def test_bin_structure(self):
        curve = calibration_curve([0.5], [1], n_bins=5)
        for bucket in curve:
            assert "bin_lower" in bucket
            assert "bin_upper" in bucket
            assert "mean_forecast" in bucket
            assert "mean_outcome" in bucket
            assert "count" in bucket

    def test_empty_bins_have_zero_count(self):
        curve = calibration_curve([0.5], [1], n_bins=5)
        empty = [b for b in curve if b["count"] == 0]
        assert all(math.isnan(b["mean_outcome"]) for b in empty)


class TestResolution:
    def test_constant_forecast_has_zero_resolution(self):
        res = resolution([0.5, 0.5, 0.5], [1, 0, 1])
        assert res == pytest.approx(0.0, abs=1e-9)

    def test_perfect_resolution_is_positive(self):
        res = resolution([1.0, 0.0], [1, 0])
        assert res > 0


class TestDecompose:
    def test_decomposition_keys(self):
        result = decompose_brier([0.7, 0.3], [1, 0])
        assert set(result.keys()) == {
            "brier_score",
            "reliability",
            "resolution",
            "uncertainty",
            "bss",
            "brier_index",
            "calibration_gap",
        }

    def test_brier_score_consistent(self):
        forecasts = [0.8, 0.6, 0.4, 0.2]
        outcomes = [1, 1, 0, 0]
        decomp = decompose_brier(forecasts, outcomes)
        direct = brier_score(forecasts, outcomes)
        assert decomp["brier_score"] == pytest.approx(direct)


class TestLeadTimePoints:
    def test_floor_applied(self):
        assert lead_time_points(3.9) == 3.0
        assert lead_time_points(4.0) == 4.0

    def test_negative_clamped_to_zero(self):
        assert lead_time_points(-2.0) == 0.0

    def test_zero(self):
        assert lead_time_points(0.0) == 0.0


# ---------------------------------------------------------------------------
# temporal_db.py tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path) -> TemporalForecastDB:
    return TemporalForecastDB(db_path=tmp_path / "test_predictions.db")


class TestTemporalForecastDB:
    def test_creates_db_file(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        TemporalForecastDB(db_path=db_path)
        assert db_path.exists()

    def test_schema_creates_table(self, tmp_db: TemporalForecastDB):
        conn = sqlite3.connect(tmp_db.db_path)
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        conn.close()
        assert "predictions" in tables

    def test_add_prediction_returns_id(self, tmp_db: TemporalForecastDB):
        pid = tmp_db.add_prediction(
            claim="Test claim",
            source_date="2025-01-01",
            confidence=0.7,
            category="test",
        )
        assert isinstance(pid, str)
        assert len(pid) == 36  # UUID4

    def test_add_prediction_invalid_confidence_raises(self, tmp_db: TemporalForecastDB):
        with pytest.raises(ValueError, match="confidence"):
            tmp_db.add_prediction("claim", "2025-01-01", confidence=1.5)

    def test_validate_computes_lead_weeks(self, tmp_db: TemporalForecastDB):
        pid = tmp_db.add_prediction("claim", "2025-01-01", confidence=0.8)
        result = tmp_db.validate(pid, "2025-03-01")
        # Jan 1 → Mar 1 = 59 days = ~8.4 weeks
        assert result["lead_weeks"] == pytest.approx(59 / 7, rel=0.01)
        assert result["points"] == 8.0

    def test_validate_nonexistent_raises(self, tmp_db: TemporalForecastDB):
        with pytest.raises(KeyError):
            tmp_db.validate("00000000-0000-0000-0000-000000000000", "2025-01-01")

    def test_falsify_sets_status(self, tmp_db: TemporalForecastDB):
        pid = tmp_db.add_prediction("claim", "2025-01-01", confidence=0.5)
        tmp_db.falsify(pid)
        preds = tmp_db.all_predictions()
        assert preds[0]["status"] == "falsified"

    def test_seed_validated_claims_inserts_all(self, tmp_db: TemporalForecastDB):
        result = tmp_db.seed_validated_claims()
        assert (
            result["inserted"] == 24
        )  # 21 validated + 2 pending + 1 expired = 24 total

    def test_seed_syncs_existing_rows(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        second = tmp_db.seed_validated_claims()
        # YAML is source of truth — second call updates all 24 rows to match
        assert second["inserted"] == 0
        assert second["updated"] == 24
        assert second["removed"] == 0

    def test_summary_after_seed(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        s = tmp_db.summary()
        assert s["total"] == 24
        assert s["validated"] == 21
        assert s["pending"] == 2
        assert s["falsified"] == 0
        assert s["total_points"] > 510  # known: 522+
        assert s["avg_lead_weeks"] > 20

    def test_summary_brier_score_after_seed(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        s = tmp_db.summary()
        # All validated claims have outcome=1; all have confidence > 0.5
        # So BS should be < 0.25 (better than uninformed baseline)
        assert s["brier_score"] is not None
        assert s["brier_score"] < 0.25
        assert s["brier_skill_score"] is not None
        assert s["brier_skill_score"] > 0

    def test_calibration_curve_after_seed(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        curve = tmp_db.calibration(n_bins=5)
        assert len(curve) == 5
        populated = [b for b in curve if b["count"] > 0]
        assert len(populated) >= 1

    def test_get_by_category(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        gov = tmp_db.get_by_category("ai_governance")
        assert len(gov) >= 4
        assert all(r["category"] == "ai_governance" for r in gov)

    def test_all_predictions_returns_list(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        all_preds = tmp_db.all_predictions()
        assert isinstance(all_preds, list)
        assert len(all_preds) == 24

    def test_total_points_matches_known_score(self, tmp_db: TemporalForecastDB):
        tmp_db.seed_validated_claims()
        s = tmp_db.summary()
        # Known from 2026-05-29 validation burst: 522+ points
        assert s["total_points"] >= 520
