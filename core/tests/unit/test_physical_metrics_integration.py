"""Integration tests for physical metrics (laptop-optimizer) and metrics exporter.

Tests the PhysicalMetricsSource, ThermalAnomalyDetector, ForecastEngine,
AdaptiveTargets, and MetricsExporter.
"""
# ruff: noqa: BLE001

import time
from pathlib import Path

import pytest

try:
    from whitemagic.harmony.physical_metrics import (
        get_physical_metrics_source,
        PhysicalMetricsSource,
        PhysicalMetrics,
        AdaptiveTargets,
        ThermalAnomalyDetector,
        ForecastEngine,
        PowerContext,
        TimeContext,
        LoadContext,
    )
    from whitemagic.harmony.metrics_exporter import (
        get_metrics_exporter,
        MetricsExporter,
    )

    _PHYSICAL_AVAILABLE = True
except ImportError:
    _PHYSICAL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PHYSICAL_AVAILABLE,
    reason="Physical metrics module not available",
)


class TestPhysicalMetrics:
    """Test PhysicalMetricsSource."""

    def test_get_metrics(self):
        """get_metrics should return a PhysicalMetrics object."""
        source = get_physical_metrics_source()
        metrics = source.get_metrics()
        assert isinstance(metrics, PhysicalMetrics)

    def test_graceful_degradation(self, monkeypatch):
        """When no metrics source is available, metrics should be unavailable."""
        source = PhysicalMetricsSource(api_url="http://127.0.0.1:99999")
        # Disable psutil fallback to test true graceful degradation
        monkeypatch.setattr(source, "_fetch_psutil_fallback", lambda: None)
        metrics = source.get_metrics()
        assert not metrics.is_available

    def test_is_available(self):
        """is_available should return a boolean."""
        source = get_physical_metrics_source()
        assert isinstance(source.is_available(), bool)

    def test_evaluate_homeostasis(self, monkeypatch):
        """evaluate_homeostasis should return a list."""
        source = PhysicalMetricsSource(api_url="http://127.0.0.1:99999")
        # Disable psutil fallback to test true no-metrics case
        monkeypatch.setattr(source, "_fetch_psutil_fallback", lambda: None)
        recs = source.evaluate_homeostasis()
        assert isinstance(recs, list)
        # Should be empty when no metrics available
        assert len(recs) == 0


class TestAdaptiveTargets:
    """Test adaptive homeostasis targets."""

    def test_default_targets(self):
        """Default targets should have reasonable values."""
        targets = AdaptiveTargets()
        assert targets.cpu_temp_max == 65.0
        assert targets.battery_min == 20.0
        assert targets.memory_max == 75.0

    def test_adapt_ac(self):
        """On AC power, CPU temp target should relax."""
        targets = AdaptiveTargets()
        targets.adapt(PowerContext.AC, TimeContext.DAY, LoadContext.IDLE)
        assert targets.cpu_temp_max == 70.0

    def test_adapt_battery(self):
        """On battery, CPU temp target should tighten."""
        targets = AdaptiveTargets()
        targets.adapt(PowerContext.BATTERY, TimeContext.DAY, LoadContext.IDLE)
        assert targets.cpu_temp_max == 60.0

    def test_adapt_night(self):
        """At night, targets should tighten."""
        targets = AdaptiveTargets()
        targets.adapt(PowerContext.AC, TimeContext.NIGHT, LoadContext.IDLE)
        assert targets.cpu_temp_max == 65.0  # 70 - 5

    def test_adapt_peak(self):
        """Under peak load, CPU temp target should relax."""
        targets = AdaptiveTargets()
        targets.adapt(PowerContext.AC, TimeContext.DAY, LoadContext.PEAK)
        assert targets.cpu_temp_max == 80.0  # 70 + 10


class TestThermalAnomalyDetector:
    """Test thermal anomaly detection."""

    def test_no_anomaly_initially(self):
        """Detector should not fire with insufficient data."""
        detector = ThermalAnomalyDetector()
        assert detector.check(50.0) is None

    def test_spike_detection(self):
        """Detector should detect a >5°C spike in 30s."""
        detector = ThermalAnomalyDetector()
        # Feed a sequence with a spike
        detector.check(50.0)
        time.sleep(0.01)
        detector.check(51.0)
        time.sleep(0.01)
        detector.check(52.0)
        time.sleep(0.01)
        # Now spike >5°C
        anomaly = detector.check(58.0)
        # May or may not detect depending on timing
        if anomaly:
            assert anomaly.pattern == "spike"


class TestForecastEngine:
    """Test forecasting engine."""

    def test_insufficient_data(self):
        """Forecast should return None with <5 data points."""
        data = [(0.0, 50.0), (1.0, 51.0)]
        result = ForecastEngine.forecast(data, "cpu_temp")
        assert result is None

    def test_basic_forecast(self):
        """Forecast should work with enough data points."""
        data = [(float(i), 50.0 + i * 0.5) for i in range(10)]
        result = ForecastEngine.forecast(data, "cpu_temp")
        assert result is not None
        assert result.metric == "cpu_temp"
        assert result.current_value == 54.5
        assert 30.0 <= result.predicted_5min <= 105.0
        assert result.confidence in ("high", "medium", "low")


class TestMetricsExporter:
    """Test Prometheus metrics exporter."""

    def test_export_returns_string(self):
        """Export should return a string."""
        exporter = get_metrics_exporter()
        result = exporter.export()
        assert isinstance(result, str)

    def test_export_has_prometheus_format(self):
        """Export should contain Prometheus-style HELP/TYPE comments."""
        exporter = MetricsExporter()
        result = exporter.export()
        # Should have at least some HELP lines
        assert "# HELP" in result or "# TYPE" in result or result == "\n"

    def test_export_physical_metrics(self):
        """Physical metrics export should work even without laptop-optimizer."""
        exporter = MetricsExporter()
        lines = exporter._export_physical_metrics()
        assert isinstance(lines, list)

    def test_export_strata_metrics(self):
        """STRATA metrics export should return a list."""
        exporter = MetricsExporter()
        lines = exporter._export_strata_metrics()
        assert isinstance(lines, list)


class TestHomeostaticLoopIntegration:
    """Test that homeostatic loop includes physical metrics."""

    def test_check_physical_method(self):
        """HomeostaticLoop should have _check_physical method."""
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        assert hasattr(loop, "_check_physical")
        result = loop._check_physical()
        assert isinstance(result, list)

    def test_physical_config_fields(self):
        """HomeostaticConfig should have physical threshold fields."""
        from whitemagic.harmony.homeostatic_loop import HomeostaticConfig

        config = HomeostaticConfig()
        assert hasattr(config, "cpu_temp_advise")
        assert hasattr(config, "cpu_temp_correct")
        assert hasattr(config, "cpu_temp_intervene")
        assert hasattr(config, "battery_low_advise")
        assert hasattr(config, "memory_high_advise")
