"""Tests for the forecasting.scoring module — continuous scoring rules."""

import pytest

from whitemagic.forecasting.scoring import (
    crps_decomposition,
    crps_gaussian,
    crps_point,
    crps_skill_score,
    dagstuhl_score,
    ecce,
    log_score,
    mean_crps,
    quantile_score,
    weighted_interval_score,
)


class TestCRPSGaussian:
    def test_perfect_prediction_small(self):
        """CRPS at z=0 should be small but nonzero (sigma-dependent)."""
        crps = crps_gaussian(1.0, 1.0, 0.1)
        assert crps < 0.05
        assert crps > 0  # Not zero — Gaussian has spread

    def test_far_prediction_large(self):
        """CRPS should be large when prediction is far from actual."""
        crps = crps_gaussian(100.0, 1.0, 0.1)
        assert crps > 90  # Close to absolute error

    def test_non_negative(self):
        """CRPS is a proper scoring rule — always non-negative."""
        for pred in [0.001, 0.1, 1.0, 10.0, 100.0]:
            for actual in [0.001, 0.1, 1.0, 10.0, 100.0]:
                for sigma in [0.01, 0.1, 1.0, 10.0]:
                    assert crps_gaussian(pred, actual, sigma) >= 0

    def test_reduces_to_absolute_error(self):
        """As sigma → 0, CRPS → |prediction - actual|."""
        for pred, actual in [(1.0, 1.5), (5.0, 3.0), (0.1, 0.3)]:
            crps = crps_gaussian(pred, actual, 0.0001)
            assert abs(crps - abs(pred - actual)) < 0.01

    def test_symmetric(self):
        """CRPS should be symmetric: CRPS(p, a) == CRPS(a, p) with same sigma."""
        assert abs(crps_gaussian(1.0, 2.0, 0.5) - crps_gaussian(2.0, 1.0, 0.5)) < 1e-10


class TestCRPSPoint:
    def test_absolute_error(self):
        assert crps_point(5.0, 3.0) == 2.0
        assert crps_point(3.0, 5.0) == 2.0
        assert crps_point(1.0, 1.0) == 0.0


class TestMeanCRPS:
    def test_perfect_predictions(self):
        """Mean CRPS of perfect predictions should be small."""
        preds = [1.0, 2.0, 3.0]
        actuals = [1.0, 2.0, 3.0]
        mc = mean_crps(preds, actuals)
        assert mc < 0.1

    def test_bad_predictions(self):
        """Mean CRPS of bad predictions should be large."""
        preds = [10.0, 20.0, 30.0]
        actuals = [1.0, 2.0, 3.0]
        mc = mean_crps(preds, actuals)
        assert mc > 5

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            mean_crps([1.0, 2.0], [1.0])

    def test_empty(self):
        with pytest.raises(ValueError):
            mean_crps([], [])


class TestCRPSSkillScore:
    def test_perfect_skill(self):
        """Perfect predictions should have skill score near 1."""
        preds = [1.0, 2.0, 3.0, 4.0, 5.0]
        actuals = [1.0, 2.0, 3.0, 4.0, 5.0]
        ss = crps_skill_score(preds, actuals)
        assert ss > 0.7

    def test_no_skill(self):
        """Predicting the mean should have skill score near 0."""
        actuals = [1.0, 2.0, 3.0, 4.0, 5.0]
        mean_val = sum(actuals) / len(actuals)
        preds = [mean_val] * len(actuals)
        ss = crps_skill_score(preds, actuals)
        assert abs(ss) < 0.3


class TestCRPSDecomposition:
    def test_well_calibrated(self):
        """Good predictions should have low miscalibration."""
        preds = [1.0, 2.0, 3.0, 4.0, 5.0]
        actuals = [1.1, 2.1, 2.9, 4.1, 4.9]
        decomp = crps_decomposition(preds, actuals)
        assert decomp["miscalibration"] < 0.5
        assert decomp["discrimination"] > 0
        assert decomp["uncertainty"] > 0
        assert decomp["count"] == 5

    def test_poorly_calibrated(self):
        """Bad predictions should have high miscalibration."""
        preds = [10.0, 20.0, 30.0, 40.0, 50.0]
        actuals = [1.0, 2.0, 3.0, 4.0, 5.0]
        decomp = crps_decomposition(preds, actuals)
        assert decomp["miscalibration"] > 1.0
        assert decomp["skill_score"] < 0


class TestQuantileScore:
    def test_median_perfect(self):
        """QS at 0.5 for perfect prediction should be 0."""
        assert quantile_score(5.0, 5.0, 0.5) == 0.0

    def test_median_overestimate(self):
        """QS at 0.5 for overestimate should equal absolute error."""
        qs = quantile_score(7.0, 5.0, 0.5)
        assert abs(qs - 2.0) < 0.01

    def test_median_underestimate(self):
        """QS at 0.5 for underestimate should equal absolute error."""
        qs = quantile_score(3.0, 5.0, 0.5)
        assert abs(qs - 2.0) < 0.01

    def test_high_quantile_penalizes_overestimates_less(self):
        """At q=0.9, overestimates are penalized less than underestimates."""
        qs_over = quantile_score(7.0, 5.0, 0.9)
        qs_under = quantile_score(3.0, 5.0, 0.9)
        assert qs_under > qs_over


class TestWIS:
    def test_perfect_prediction(self):
        """WIS with perfect median and tight intervals should be small."""
        wis = weighted_interval_score(5.0, 5.0, [4.9], [5.1], [0.1])
        assert wis < 0.5

    def test_outside_interval(self):
        """WIS should penalize when actual is outside the interval."""
        wis_inside = weighted_interval_score(5.0, 5.0, [3.0], [7.0], [0.1])
        wis_outside = weighted_interval_score(5.0, 8.0, [3.0], [7.0], [0.1])
        assert wis_outside > wis_inside

    def test_no_intervals(self):
        """WIS with no intervals should be just absolute error of median."""
        wis = weighted_interval_score(5.0, 3.0, [], [], [])
        assert wis == 2.0


class TestECCE:
    def test_perfect_calibration(self):
        """ECCE for well-calibrated forecasts should be lower than miscalibrated."""
        # Forecasts that match outcome frequencies
        ecce_good = ecce([0.1, 0.3, 0.5, 0.7, 0.9], [0, 0, 1, 1, 1])
        # All forecasts at 0.9 but half are wrong
        ecce_bad = ecce([0.9, 0.9, 0.9, 0.9], [1, 1, 0, 0])
        assert ecce_good < ecce_bad

    def test_poor_calibration(self):
        """ECCE for poorly calibrated forecasts should be higher."""
        # All forecasts at 0.9, but only half are validated
        ecce_val = ecce([0.9, 0.9, 0.9, 0.9], [1, 1, 0, 0])
        assert ecce_val > 0.1

    def test_empty(self):
        assert ecce([], []) == 0.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            ecce([0.5, 0.6], [1])


class TestLogScore:
    def test_perfect_prediction(self):
        """Log score for perfect prediction should be low (negative)."""
        ls = log_score(1.0, 1.0, 0.1)
        assert ls < 0  # Negative log-likelihood is negative for good fit

    def test_bad_prediction(self):
        """Log score for bad prediction should be high (positive)."""
        ls_good = log_score(1.0, 1.0, 0.1)
        ls_bad = log_score(10.0, 1.0, 0.1)
        assert ls_bad > ls_good


class TestDagstuhlScore:
    def test_comprehensive_output(self):
        """Dagstuhl score should return all metrics."""
        preds = [1.0, 2.0, 3.0, 4.0, 5.0]
        actuals = [1.1, 2.1, 2.9, 4.1, 4.9]
        result = dagstuhl_score(preds, actuals)

        assert "count" in result
        assert "mean_crps" in result
        assert "crps_decomposition" in result
        assert "crps_skill_score" in result
        assert "mean_log_score" in result
        assert "mean_quantile_score_50" in result
        assert "mean_quantile_score_90" in result
        assert "mae" in result
        assert "mape" in result
        assert "bias" in result
        assert "mean_log_ratio_error" in result
        assert "mae_log_ratio_error" in result
        assert "per_prediction_crps" in result
        assert result["count"] == 5
        assert len(result["per_prediction_crps"]) == 5

    def test_empty(self):
        result = dagstuhl_score([], [])
        assert result["count"] == 0
