"""Tests for Decepticon / autonomous red-teaming bridge (Gap 1)."""
import pytest
from unittest.mock import patch, MagicMock

from whitemagic.tools.security.decepticon_bridge import (
    AttackStep,
    AttackSession,
    _check_decepticon,
    _check_ollama,
    run_decepticon_directly,
    run_autonomous_redteam,
    decepticon_status,
    _is_ip_or_hostname,
    _extract_decepticon_findings,
)


class TestDecepticonAvailability:
    """Test availability checking."""

    def test_check_decepticon_found(self):
        with patch("shutil.which", return_value="/usr/bin/decepticon"):
            assert _check_decepticon() == "/usr/bin/decepticon"

    def test_check_decepticon_not_found(self):
        with patch("shutil.which", return_value=None):
            assert _check_decepticon() is None

    def test_check_ollama_found(self):
        with patch("shutil.which", return_value="/usr/bin/ollama"):
            assert _check_ollama() == "/usr/bin/ollama"

    def test_check_ollama_not_found(self):
        with patch("shutil.which", return_value=None):
            assert _check_ollama() is None

    def test_decepticon_status_all_available(self):
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value="/usr/bin/decepticon"), \
             patch("whitemagic.tools.security.decepticon_bridge._check_ollama", return_value="/usr/bin/ollama"):
            status = decepticon_status()
            assert status["decepticon_available"] is True
            assert status["ollama_available"] is True
            assert "recon" in status["supported_phases"]

    def test_decepticon_status_none_available(self):
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value=None), \
             patch("whitemagic.tools.security.decepticon_bridge._check_ollama", return_value=None):
            status = decepticon_status()
            assert status["decepticon_available"] is False
            assert status["ollama_available"] is False
            assert status["fallback_pipeline"] is True


class TestRunDecepticonDirectly:
    """Test direct Decepticon execution."""

    def test_decepticon_not_installed(self):
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value=None):
            result = run_decepticon_directly("http://target.com")
            assert result["status"] == "error"
            assert result["error_code"] == "decepticon_not_installed"
            assert result["fallback_available"] is True

    def test_ollama_not_installed(self):
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value="/usr/bin/decepticon"), \
             patch("whitemagic.tools.security.decepticon_bridge._check_ollama", return_value=None):
            result = run_decepticon_directly("http://target.com")
            assert result["status"] == "error"
            assert result["error_code"] == "ollama_not_installed"


class TestRunAutonomousRedteam:
    """Test the fallback autonomous red-teaming pipeline."""

    def test_fallback_pipeline_runs(self):
        """Fallback pipeline should run when Decepticon is not installed."""
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value=None):
            # Mock the recon phase to avoid actual nmap calls
            with patch("whitemagic.tools.security.decepticon_bridge._run_recon_phase") as mock_recon, \
                 patch("whitemagic.tools.security.decepticon_bridge._run_scan_phase") as mock_scan, \
                 patch("whitemagic.tools.security.decepticon_bridge._run_exploit_phase") as mock_exploit, \
                 patch("whitemagic.tools.security.decepticon_bridge._run_report_phase") as mock_report:

                mock_recon.return_value = AttackStep(
                    step_id="recon-1", phase="recon", tool="nmap", target="127.0.0.1",
                    action="scan", status="success", result={"findings": []}
                )
                mock_scan.return_value = AttackStep(
                    step_id="scan-1", phase="scan", tool="nuclei", target="127.0.0.1",
                    action="scan", status="success", result={"findings": []}
                )
                mock_exploit.return_value = AttackStep(
                    step_id="exploit-1", phase="exploit", tool="sqlmap", target="127.0.0.1",
                    action="exploit", status="completed", result={"findings": []}
                )
                mock_report.return_value = AttackStep(
                    step_id="report-1", phase="report", tool="contest_pipeline", target="127.0.0.1",
                    action="report", status="success", result={}
                )

                result = run_autonomous_redteam("127.0.0.1", scope="recon,scan,exploit,report")
                assert result["session"]["status"] == "completed"
                assert result["fallback_used"] is True
                assert len(result["steps"]) == 4

    def test_fallback_pipeline_recon_only(self):
        """Pipeline should respect scope parameter."""
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value=None), \
             patch("whitemagic.tools.security.decepticon_bridge._run_recon_phase") as mock_recon:
            mock_recon.return_value = AttackStep(
                step_id="recon-1", phase="recon", tool="nmap", target="127.0.0.1",
                action="scan", status="success", result={"findings": [{"severity": "medium", "title": "Open port 80"}]}
            )
            result = run_autonomous_redteam("127.0.0.1", scope="recon")
            assert result["session"]["status"] == "completed"
            assert len(result["steps"]) == 1
            assert result["finding_count"] == 1

    def test_decepticon_available_delegates(self):
        """When Decepticon is available, should delegate to it."""
        mock_result = {"status": "success", "output": "[]", "returncode": 0}
        with patch("whitemagic.tools.security.decepticon_bridge._check_decepticon", return_value="/usr/bin/decepticon"), \
             patch("whitemagic.tools.security.decepticon_bridge.run_decepticon_directly", return_value=mock_result):
            result = run_autonomous_redteam("http://target.com")
            assert "decepticon_result" in result
            assert result["session"]["decepticon_available"] is True


class TestTargetClassification:
    """Test target type classification."""

    def test_ip_address(self):
        assert _is_ip_or_hostname("192.168.1.1") is True

    def test_hostname(self):
        assert _is_ip_or_hostname("example.com") is True

    def test_localhost(self):
        assert _is_ip_or_hostname("localhost") is True

    def test_file_path(self):
        assert _is_ip_or_hostname("/home/user/project") is False

    def test_url_not_matched(self):
        # URLs starting with http are handled separately
        assert _is_ip_or_hostname("http://example.com") is False  # has /


class TestExtractFindings:
    """Test Decepticon findings extraction."""

    def test_extract_from_json_list(self):
        output = '[{"severity": "high", "title": "SQLi", "category": "sqli", "description": "Found SQLi", "target": "http://example.com"}]'
        result = run_decepticon_directly.__wrapped__ if hasattr(run_decepticon_directly, "__wrapped__") else None
        findings = _extract_decepticon_findings({"output": output})
        assert len(findings) == 1
        assert findings[0]["severity"] == "high"
        assert findings[0]["tool"] == "decepticon"

    def test_extract_from_invalid_json(self):
        findings = _extract_decepticon_findings({"output": "not json"})
        assert len(findings) == 0

    def test_extract_from_empty_output(self):
        findings = _extract_decepticon_findings({"output": ""})
        assert len(findings) == 0


class TestAttackSessionDataclass:
    """Test AttackSession and AttackStep dataclasses."""

    def test_attack_step_defaults(self):
        step = AttackStep(
            step_id="test", phase="recon", tool="nmap",
            target="127.0.0.1", action="scan"
        )
        assert step.status == "pending"
        assert step.result == {}
        assert step.timestamp == 0.0

    def test_attack_session_defaults(self):
        session = AttackSession(
            session_id="RT-1", target="127.0.0.1", scope="recon"
        )
        assert session.status == "initialized"
        assert session.steps == []
        assert session.findings == []
        assert session.decepticon_available is False

    def test_attack_session_summary(self):
        session = AttackSession(
            session_id="RT-1", target="127.0.0.1", scope="recon",
            started_at=1000.0, completed_at=1005.0, status="completed"
        )
        summary = session.summary()
        assert summary["session_id"] == "RT-1"
        assert summary["status"] == "completed"
        assert summary["duration_seconds"] == 5.0
