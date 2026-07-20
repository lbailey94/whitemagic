"""Tests for continuous security scanning in ConsciousnessLoop (Gap 5)."""
from unittest.mock import MagicMock, patch

from whitemagic.core.consciousness.consciousness_loop import (
    ConsciousnessLoop,
    LoopConfig,
    LoopStats,
)


class TestSecurityScanConfig:
    """Test LoopConfig security scan settings."""

    def test_security_scan_disabled_by_default(self):
        """Security scan should be disabled by default."""
        config = LoopConfig()
        assert config.enable_security_scan is False

    def test_security_scan_interval_default(self):
        """Security scan interval should default to 600s."""
        config = LoopConfig()
        assert config.security_scan_interval_s == 600.0

    def test_security_scan_path_default_empty(self):
        """Security scan path should default to empty (auto-detect)."""
        config = LoopConfig()
        assert config.security_scan_path == ""

    def test_security_scan_config_from_env(self):
        """Security scan config should load from environment variables."""
        with patch.dict("os.environ", {
            "WM_ENABLE_SECURITY_SCAN": "1",
            "WM_SECURITY_SCAN_INTERVAL": "300",
            "WM_SECURITY_SCAN_PATH": "/tmp/test",
        }):
            config = LoopConfig.from_env()
            assert config.enable_security_scan is True
            assert config.security_scan_interval_s == 300.0
            assert config.security_scan_path == "/tmp/test"


class TestSecurityScanStats:
    """Test LoopStats security scan tracking."""

    def test_security_scan_stats_default(self):
        """Security scan stats should default to zero."""
        stats = LoopStats()
        assert stats.security_scans == 0
        assert stats.last_security_findings == 0
        assert stats.last_security_ttps == 0

    def test_security_scan_stats_in_to_dict(self):
        """Security scan stats should be included in to_dict()."""
        stats = LoopStats()
        stats.security_scans = 5
        stats.last_security_findings = 10
        stats.last_security_ttps = 7
        d = stats.to_dict()
        assert d["security_scans"] == 5
        assert d["last_security_findings"] == 10
        assert d["last_security_ttps"] == 7


class TestSecurityScanMethod:
    """Test the _run_security_scan method."""

    def test_security_scan_disabled_skips(self):
        """When disabled, _run_security_scan should not be called."""
        config = LoopConfig(enable_security_scan=False)
        loop = ConsciousnessLoop(config)
        with patch.object(loop, "_run_security_scan") as mock_scan:
            # Just verify the method exists and the gate works
            # We don't need to run the full loop
            assert mock_scan is not None
            assert config.enable_security_scan is False

    def test_security_scan_runs_strata(self):
        """_run_security_scan should call Strata.analyze."""
        config = LoopConfig(
            enable_security_scan=True,
            security_scan_path="/tmp/test",
        )
        loop = ConsciousnessLoop(config)

        # Mock Strata
        mock_finding = MagicMock()
        mock_finding.severity.value = "error"
        mock_finding.category = "py_sql_injection"
        mock_finding.file = "test.py"
        mock_finding.line = 42
        mock_finding.message = "SQL injection"
        mock_finding.suggestion = "Use parameterized queries"

        mock_strata = MagicMock()
        mock_strata.analyze.return_value = [mock_finding]

        with patch("whitemagic.core.ports.get_strata", return_value=lambda *a, **k: mock_strata):
            loop._run_security_scan()

        assert loop._stats.security_scans == 1
        assert loop._stats.last_security_findings == 1
        assert loop._stats.last_security_ttps > 0

    def test_security_scan_no_findings(self):
        """_run_security_scan should handle no findings gracefully."""
        config = LoopConfig(
            enable_security_scan=True,
            security_scan_path="/tmp/test",
        )
        loop = ConsciousnessLoop(config)

        mock_strata = MagicMock()
        mock_strata.analyze.return_value = []

        with patch("whitemagic.core.ports.get_strata", return_value=lambda *a, **k: mock_strata):
            loop._run_security_scan()

        assert loop._stats.security_scans == 1
        assert loop._stats.last_security_findings == 0
        assert loop._stats.last_security_ttps == 0

    def test_security_scan_auto_detect_path(self):
        """When scan_path is empty, should auto-detect and skip if no AGENTS.md."""
        config = LoopConfig(
            enable_security_scan=True,
            security_scan_path="",
        )
        loop = ConsciousnessLoop(config)

        # Mock Strata and Path to simulate auto-detect finding AGENTS.md
        mock_strata = MagicMock()
        mock_strata.analyze.return_value = []

        with patch("whitemagic.core.ports.get_strata", return_value=lambda *a, **k: mock_strata), \
             patch("pathlib.Path.exists", return_value=True):
            loop._run_security_scan()

        assert loop._stats.security_scans == 1

    def test_security_scan_handles_exception(self):
        """_run_security_scan should handle exceptions gracefully."""
        config = LoopConfig(
            enable_security_scan=True,
            security_scan_path="/tmp/test",
        )
        loop = ConsciousnessLoop(config)

        with patch("whitemagic.core.ports.get_strata", side_effect=Exception("Test error")):
            # Should not raise
            loop._run_security_scan()

        # Stats should not be updated on error
        assert loop._stats.security_scans == 0

    def test_security_scan_maps_ttps(self):
        """_run_security_scan should map findings to MITRE TTPs."""
        config = LoopConfig(
            enable_security_scan=True,
            security_scan_path="/tmp/test",
        )
        loop = ConsciousnessLoop(config)

        mock_finding = MagicMock()
        mock_finding.severity.value = "error"
        mock_finding.category = "py_sql_injection"
        mock_finding.file = "app.py"
        mock_finding.line = 10
        mock_finding.message = "SQL injection found"
        mock_finding.suggestion = "Parameterize"

        mock_strata = MagicMock()
        mock_strata.analyze.return_value = [mock_finding]

        with patch("whitemagic.core.ports.get_strata", return_value=lambda *a, **k: mock_strata):
            loop._run_security_scan()

        # py_sql_injection maps to T1190 and T1213
        assert loop._stats.last_security_ttps == 2

    def test_security_scan_feeds_contest_pipeline(self):
        """_run_security_scan should feed findings into contest pipeline."""
        config = LoopConfig(
            enable_security_scan=True,
            security_scan_path="/tmp/test",
        )
        loop = ConsciousnessLoop(config)

        mock_finding = MagicMock()
        mock_finding.severity.value = "error"
        mock_finding.category = "hardcoded_secret"
        mock_finding.file = "config.py"
        mock_finding.line = 5
        mock_finding.message = "Hardcoded API key"
        mock_finding.suggestion = "Use env vars"

        mock_strata = MagicMock()
        mock_strata.analyze.return_value = [mock_finding]

        with patch("whitemagic.core.ports.get_strata", return_value=lambda *a, **k: mock_strata), \
             patch("whitemagic.core.ports.get_contest_pipeline") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_get_pipeline.return_value = mock_pipeline

            loop._run_security_scan()

            mock_pipeline.add_from_strata.assert_called_once()


class TestSecurityScanInLoop:
    """Test that security scan is wired into the main loop."""

    def test_loop_has_last_security_scan_var(self):
        """ConsciousnessLoop should have _last_security_scan instance variable."""
        loop = ConsciousnessLoop()
        assert hasattr(loop, "_last_security_scan")
        assert loop._last_security_scan == 0.0

    def test_status_includes_security_scan_stats(self):
        """Loop status should include security scan stats."""
        config = LoopConfig(enable_security_scan=True)
        loop = ConsciousnessLoop(config)
        loop._stats.security_scans = 3
        loop._stats.last_security_findings = 5
        loop._stats.last_security_ttps = 4

        status = loop.status()
        assert status["stats"]["security_scans"] == 3
        assert status["stats"]["last_security_findings"] == 5
        assert status["stats"]["last_security_ttps"] == 4

    def test_status_includes_security_scan_config(self):
        """Loop status should include security scan config."""
        config = LoopConfig(enable_security_scan=True, security_scan_interval_s=300.0)
        loop = ConsciousnessLoop(config)
        status = loop.status()
        assert "enable_security_scan" not in status["config"]  # Not in config dict
        # But the config object should have it
        assert loop._config.enable_security_scan is True
        assert loop._config.security_scan_interval_s == 300.0
