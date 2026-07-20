"""P8.4 — Coverage by risk configuration tests.

Tests that risk-based coverage targets are defined correctly and
critical packages have appropriate thresholds.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(REPO_ROOT / "core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "core"))

import pytest

from benchmarks.coverage_targets import (
    COVERAGE_TARGETS,
    RiskLevel,
    get_critical_packages,
    get_high_risk_packages,
    get_coverage_config,
    GLOBAL_INFORMATIONAL_THRESHOLD,
)


class TestCoverageTargets:
    """P8.4 — Risk-based coverage targets are defined."""

    def test_targets_non_empty(self):
        assert len(COVERAGE_TARGETS) > 0

    def test_critical_targets_exist(self):
        critical = [t for t in COVERAGE_TARGETS if t.risk == RiskLevel.CRITICAL]
        assert len(critical) >= 2, "Expected at least 2 critical coverage targets"

    def test_critical_thresholds_are_high(self):
        for t in COVERAGE_TARGETS:
            if t.risk == RiskLevel.CRITICAL:
                assert t.branch_threshold >= 75.0
                assert t.line_threshold >= 80.0

    def test_high_risk_thresholds_are_adequate(self):
        for t in COVERAGE_TARGETS:
            if t.risk == RiskLevel.HIGH:
                assert t.branch_threshold >= 65.0
                assert t.line_threshold >= 70.0

    def test_thresholds_decrease_by_risk(self):
        """Lower risk packages should have lower thresholds."""
        for t in COVERAGE_TARGETS:
            if t.risk == RiskLevel.LOW:
                assert t.branch_threshold < 50.0
            elif t.risk == RiskLevel.MEDIUM:
                assert t.branch_threshold < 65.0

    def test_critical_packages_include_safety_and_memory(self):
        critical = get_critical_packages()
        assert any("security" in p for p in critical)
        assert any("memory" in p for p in critical)
        assert any("dharma" in p for p in critical)

    def test_high_risk_packages_include_dispatch(self):
        high = get_high_risk_packages()
        assert any("dispatch" in p for p in high)
        assert any("registry" in p for p in high)

    def test_global_threshold_is_informational(self):
        assert GLOBAL_INFORMATIONAL_THRESHOLD == 25.0

    def test_coverage_config_is_valid(self):
        config = get_coverage_config()
        assert config["global_threshold"] == 25.0
        assert config["critical_package_count"] >= 5
        assert config["high_risk_package_count"] >= 10
        assert len(config["targets"]) == len(COVERAGE_TARGETS)

    def test_every_target_has_packages(self):
        for t in COVERAGE_TARGETS:
            assert len(t.packages) > 0, f"Target {t.description} has no packages"
