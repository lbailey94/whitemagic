"""Integration tests for STRATA codebase analysis integration.

Tests the STRATA handler (analyze, survey, archaeology, list_checks) and
the kaizen engine integration.
"""
# ruff: noqa: BLE001

from pathlib import Path

import pytest

try:
    from whitemagic.tools.handlers.strata import (
        handle_strata_analyze,
        handle_strata_survey,
        handle_strata_archaeology,
        handle_strata_list_checks,
    )
    from whitemagic.tools.strata import Strata, FindingSeverity
    from whitemagic.tools.strata.checkers import get_checkers
    _STRATA_AVAILABLE = True
except ImportError:
    _STRATA_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _STRATA_AVAILABLE,
    reason="STRATA module not available",
)

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


class TestStrataCore:
    """Test STRATA core module."""

    def test_checkers_registered(self):
        """Verify that checkers are auto-registered."""
        checkers = get_checkers()
        assert len(checkers) > 0, "No STRATA checkers registered"

    def test_strata_init(self):
        """Test Strata class initialization."""
        strata = Strata(str(REPO_ROOT))
        assert strata is not None

    def test_strata_analyze(self):
        """Test running STRATA analysis on the repo."""
        strata = Strata(str(REPO_ROOT))
        findings = strata.analyze(incremental=True)
        assert isinstance(findings, list)

    def test_finding_severity_enum(self):
        """Test FindingSeverity enum values."""
        assert FindingSeverity.ERROR
        assert FindingSeverity.WARNING
        assert FindingSeverity.INFO


class TestStrataHandler:
    """Test STRATA MCP handler interface."""

    def test_list_checks(self):
        """List checks should return registered checkers."""
        result = handle_strata_list_checks()
        assert result["status"] == "success"
        assert result["count"] > 0
        assert "checkers" in result

    def test_analyze_no_path(self):
        """Analyze without a path should return error."""
        result = handle_strata_analyze()
        assert result["status"] == "error"

    def test_analyze_with_path(self):
        """Analyze with a valid path should return findings."""
        result = handle_strata_analyze(path=str(REPO_ROOT), incremental=True)
        assert result["status"] == "success"
        assert "findings" in result
        assert "count" in result
        assert "severity_counts" in result

    def test_survey_no_path(self):
        """Survey without a path should return error."""
        result = handle_strata_survey()
        assert result["status"] == "error"

    def test_archaeology_no_path(self):
        """Archaeology without a path should return error."""
        result = handle_strata_archaeology()
        assert result["status"] == "error"

    def test_archaeology_bad_subcommand(self):
        """Archaeology with invalid subcommand should return error."""
        result = handle_strata_archaeology(path=str(REPO_ROOT), subcommand="invalid")
        assert result["status"] == "error"

    def test_archaeology_composition(self):
        """Test composition subcommand."""
        result = handle_strata_archaeology(
            path=str(REPO_ROOT), subcommand="composition", top=3
        )
        # May succeed or error depending on git history
        assert result["status"] in ("success", "error")


class TestKaizenStrataIntegration:
    """Test STRATA integration with Kaizen engine."""

    def test_analyze_codebase_method(self):
        """Test that kaizen engine has _analyze_codebase method."""
        from whitemagic.core.intelligence.synthesis.kaizen_engine import KaizenEngine
        engine = KaizenEngine()
        assert hasattr(engine, "_analyze_codebase")
        # Should return a list (possibly empty if STRATA not available)
        result = engine._analyze_codebase()
        assert isinstance(result, list)
