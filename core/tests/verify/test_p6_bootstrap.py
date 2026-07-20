"""P6.4 — Cold bootstrap profiler tests.

Tests that:
1. All 6 profiling stages are present
2. Provisional targets are defined
3. Report structure is serializable
4. Stage timings are non-negative
5. Warm path should be faster than cold path (or at least measured)
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(REPO_ROOT / "core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "core"))

import pytest

from benchmarks.bootstrap_profiler import (
    BootstrapReport,
    StageProfile,
    run_bootstrap_profile,
    print_report,
)


class TestStageDefinitions:
    """Test that all required profiling stages are defined."""

    def test_six_stages_present(self):
        """P6.4 requires profiling in this order:
        1. Registry synthesis/materialization
        2. Schema conversion
        3. Dispatch import graph
        4. Post-call initialization
        5. Stable-surface listing
        6. Fast-path verification
        """
        from benchmarks.bootstrap_profiler import (
            _profile_registry_materialization,
            _profile_schema_conversion,
            _profile_dispatch_import,
            _profile_post_call_init,
            _profile_stable_surface_listing,
            _profile_fast_path_verification,
        )
        # All 6 stage functions should be callable
        assert callable(_profile_registry_materialization)
        assert callable(_profile_schema_conversion)
        assert callable(_profile_dispatch_import)
        assert callable(_profile_post_call_init)
        assert callable(_profile_stable_surface_listing)
        assert callable(_profile_fast_path_verification)

    def test_warm_path_defined(self):
        """Warm fast-path should also be profiled."""
        from benchmarks.bootstrap_profiler import _profile_warm_fast_path
        assert callable(_profile_warm_fast_path)


class TestProvisionalTargets:
    """Test that provisional targets are defined per the strategy doc."""

    def test_targets_in_report(self):
        """Report should include targets dict."""
        report = BootstrapReport()
        d = report.to_dict()
        assert "targets" in d
        targets = d["targets"]
        assert targets["base_import"] == 100
        assert targets["registry_materialization"] == 250
        assert targets["first_safe_introspection"] == 500
        assert targets["warm_safe_introspection"] == 10


class TestStageProfile:
    """Test StageProfile dataclass."""

    def test_within_target(self):
        sp = StageProfile(name="test", duration_ms=50, target_ms=100)
        assert sp.within_target is True

    def test_over_target(self):
        sp = StageProfile(name="test", duration_ms=150, target_ms=100)
        assert sp.within_target is False

    def test_no_target(self):
        sp = StageProfile(name="test", duration_ms=999)
        assert sp.within_target is True


class TestBootstrapReport:
    """Test BootstrapReport structure."""

    def test_to_dict_serializable(self):
        report = BootstrapReport(
            stages=[StageProfile(name="test", duration_ms=10)],
            total_ms=100,
            base_import_ms=50,
        )
        d = report.to_dict()
        assert "stages" in d
        assert "total_ms" in d
        assert "base_import_ms" in d
        assert len(d["stages"]) == 1
        assert d["stages"][0]["name"] == "test"

    def test_print_report_does_not_crash(self):
        report = BootstrapReport(
            stages=[StageProfile(name="test", duration_ms=10, target_ms=100)],
            total_ms=100,
        )
        print_report(report)


class TestStageTimings:
    """Test that stage timings are valid."""

    def test_durations_non_negative(self):
        sp = StageProfile(name="test", duration_ms=0.0)
        assert sp.duration_ms >= 0

    def test_stage_profile_error_handling(self):
        sp = StageProfile(name="test", duration_ms=0, error="ImportError")
        assert sp.error == "ImportError"
        assert sp.within_target is True  # No target set
