"""Tests for dynamic testing wrappers (Gap 2)."""
import json
import pytest
from unittest.mock import patch, MagicMock

from whitemagic.tools.security.dynamic_testers import (
    DynamicFinding,
    _check_tool_available,
    _run_tool,
    _tool_not_installed,
    run_nmap,
    run_sqlmap,
    run_hydra,
    run_nikto,
    run_ffuf,
    run_nuclei,
    _parse_nmap_output,
    _parse_sqlmap_output,
    _parse_hydra_output,
    _parse_nuclei_output,
)


class TestToolAvailability:
    """Test tool availability checking."""

    def test_check_tool_available_returns_path(self):
        """_check_tool_available should return path for installed tools."""
        with patch("shutil.which", return_value="/usr/bin/python3"):
            result = _check_tool_available("python3")
            assert result == "/usr/bin/python3"

    def test_check_tool_available_returns_none(self):
        """_check_tool_available should return None for missing tools."""
        with patch("shutil.which", return_value=None):
            result = _check_tool_available("nonexistent_tool_xyz")
            assert result is None

    def test_tool_not_installed_error(self):
        """_tool_not_installed should return structured error."""
        result = _tool_not_installed("nmap", "sudo apt install nmap")
        assert result["status"] == "error"
        assert result["error_code"] == "tool_not_installed"
        assert "nmap" in result["error"]
        assert result["tool"] == "nmap"


class TestNmapParsing:
    """Test nmap output parsing."""

    def test_parse_open_port(self):
        """Parser should detect open ports."""
        output = """
Nmap scan report for example.com (93.184.216.34)
Host is up (0.05s latency).
PORT     STATE SERVICE  VERSION
80/tcp   open  http    Apache httpd 2.4.41
22/tcp   open  ssh     OpenSSH 8.2p1
443/tcp  open  https   Apache httpd 2.4.41
"""
        findings = _parse_nmap_output(output, "example.com")
        assert len(findings) == 3
        assert findings[0].tool == "nmap"
        assert "80" in findings[0].title
        assert findings[0].mitre_ttp_ids == ["T1046"]

    def test_parse_no_open_ports(self):
        """Parser should return empty when no open ports."""
        output = """
Nmap scan report for example.com
PORT     STATE    SERVICE
80/tcp   closed   http
22/tcp   filtered ssh
"""
        findings = _parse_nmap_output(output, "example.com")
        assert len(findings) == 0

    def test_parse_telnet_is_high_severity(self):
        """Telnet should be flagged as high severity."""
        output = "23/tcp   open  telnet  Linux telnetd"
        findings = _parse_nmap_output(output, "target")
        assert len(findings) == 1
        assert findings[0].severity == "high"


class TestSqlmapParsing:
    """Test sqlmap output parsing."""

    def test_parse_vulnerable(self):
        """Parser should detect 'is vulnerable' message."""
        output = """
[*] starting @ 12:00:00 /2026/

[INFO] testing connection to the target URL
[INFO] testing if the target URL content is stable
[INFO] the GET parameter 'id' is vulnerable
"""
        findings = _parse_sqlmap_output(output, "http://example.com/page?id=1")
        assert len(findings) >= 1
        assert findings[0].severity == "critical"
        assert findings[0].category == "py_sql_injection"
        assert "T1190" in findings[0].mitre_ttp_ids

    def test_parse_injection_point(self):
        """Parser should detect injection point."""
        output = "sqlmap identified the following injection point with a GET request"
        findings = _parse_sqlmap_output(output, "http://example.com")
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_parse_no_injection(self):
        """Parser should return empty when no injection found."""
        output = "[INFO] all tested parameters do not appear to be injectable"
        findings = _parse_sqlmap_output(output, "http://example.com")
        assert len(findings) == 0


class TestHydraParsing:
    """Test hydra output parsing."""

    def test_parse_valid_credentials(self):
        """Parser should detect valid credentials."""
        output = "[22][ssh] host: 192.168.1.1 login: root password: toor"
        findings = _parse_hydra_output(output, "192.168.1.1", "ssh")
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].category == "hardcoded_secret"
        assert "T1552" in findings[0].mitre_ttp_ids
        assert "T1110" in findings[0].mitre_ttp_ids

    def test_parse_no_credentials(self):
        """Parser should return empty when no credentials found."""
        output = "[ERROR] could not connect to target"
        findings = _parse_hydra_output(output, "target", "ssh")
        assert len(findings) == 0


class TestNucleiParsing:
    """Test nuclei output parsing."""

    def test_parse_xss_finding(self):
        """Parser should detect XSS findings and map correctly."""
        output = json.dumps({
            "template-id": "xss-reflection",
            "info": {"name": "XSS Reflection", "severity": "high", "description": "Reflected XSS found"},
            "matched-at": "http://example.com/search?q=test",
        })
        findings = _parse_nuclei_output(output, "http://example.com")
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert findings[0].category == "web_xss_innerhtml"
        assert "T1059.007" in findings[0].mitre_ttp_ids

    def test_parse_sqli_finding(self):
        """Parser should detect SQLi findings and map correctly."""
        output = json.dumps({
            "template-id": "sqli-error-based",
            "info": {"name": "SQL Injection", "severity": "critical"},
            "matched-at": "http://example.com/page?id=1",
        })
        findings = _parse_nuclei_output(output, "http://example.com")
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].category == "py_sql_injection"
        assert "T1190" in findings[0].mitre_ttp_ids

    def test_parse_empty_output(self):
        """Parser should return empty for no output."""
        assert _parse_nuclei_output("", "http://example.com") == []

    def test_parse_invalid_json(self):
        """Parser should skip invalid JSON lines."""
        output = "not json\n{invalid}\n"
        findings = _parse_nuclei_output(output, "http://example.com")
        assert len(findings) == 0


class TestRunNmap:
    """Test run_nmap with mocked subprocess."""

    def test_run_nmap_not_installed(self):
        """run_nmap should return tool_not_installed when nmap is missing."""
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value=None):
            result = run_nmap("127.0.0.1")
            assert result["status"] == "error"
            assert result["error_code"] == "tool_not_installed"

    def test_run_nmap_success(self):
        """run_nmap should parse findings on success."""
        nmap_output = """
Nmap scan report for 127.0.0.1
PORT     STATE SERVICE  VERSION
80/tcp   open  http    Apache
"""
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/nmap"), \
             patch("whitemagic.tools.security.dynamic_testers._run_tool", return_value=(0, nmap_output, "")):
            result = run_nmap("127.0.0.1", scan_type="quick")
            assert result["status"] == "success"
            assert result["tool"] == "nmap"
            assert result["finding_count"] == 1
            assert result["findings"][0]["severity"] == "info"  # port 80 http

    def test_run_nmap_timeout(self):
        """run_nmap should handle timeout."""
        import subprocess
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/nmap"), \
             patch("whitemagic.tools.security.dynamic_testers._run_tool", side_effect=subprocess.TimeoutExpired("nmap", 120)):
            result = run_nmap("127.0.0.1")
            assert result["status"] == "timeout"


class TestRunSqlmap:
    """Test run_sqlmap with mocked subprocess."""

    def test_run_sqlmap_not_installed(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value=None):
            result = run_sqlmap("http://example.com")
            assert result["status"] == "error"
            assert result["error_code"] == "tool_not_installed"

    def test_run_sqlmap_finds_injection(self):
        output = "the GET parameter 'id' is vulnerable"
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/sqlmap"), \
             patch("whitemagic.tools.security.dynamic_testers._run_tool", return_value=(0, output, "")):
            result = run_sqlmap("http://example.com?id=1")
            assert result["status"] == "success"
            assert result["finding_count"] == 1
            assert result["findings"][0]["severity"] == "critical"


class TestRunHydra:
    """Test run_hydra with mocked subprocess."""

    def test_run_hydra_not_installed(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value=None):
            result = run_hydra("target", "ssh", passlist="/tmp/words.txt")
            assert result["status"] == "error"
            assert result["error_code"] == "tool_not_installed"

    def test_run_hydra_missing_passlist(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/hydra"):
            result = run_hydra("target", "ssh", user="admin")
            assert result["status"] == "error"
            assert "passlist" in result["error"]

    def test_run_hydra_finds_credentials(self):
        output = "[22][ssh] host: target login: admin password: admin123"
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/hydra"), \
             patch("whitemagic.tools.security.dynamic_testers._run_tool", return_value=(0, output, "")):
            result = run_hydra("target", "ssh", user="admin", passlist="/tmp/words.txt")
            assert result["status"] == "success"
            assert result["finding_count"] == 1
            assert result["findings"][0]["severity"] == "critical"


class TestRunNikto:
    """Test run_nikto with mocked subprocess."""

    def test_run_nikto_not_installed(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value=None):
            result = run_nikto("target")
            assert result["status"] == "error"
            assert result["error_code"] == "tool_not_installed"


class TestRunFfuf:
    """Test run_ffuf with mocked subprocess."""

    def test_run_ffuf_not_installed(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value=None):
            result = run_ffuf("http://target/FUZZ", wordlist="/tmp/words.txt")
            assert result["status"] == "error"
            assert result["error_code"] == "tool_not_installed"

    def test_run_ffuf_missing_wordlist(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/ffuf"):
            result = run_ffuf("http://target/FUZZ")
            assert result["status"] == "error"
            assert "wordlist" in result["error"]


class TestRunNuclei:
    """Test run_nuclei with mocked subprocess."""

    def test_run_nuclei_not_installed(self):
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value=None):
            result = run_nuclei("http://target")
            assert result["status"] == "error"
            assert result["error_code"] == "tool_not_installed"

    def test_run_nuclei_success(self):
        output = json.dumps({
            "template-id": "xss-reflection",
            "info": {"name": "XSS", "severity": "high"},
            "matched-at": "http://target/search?q=test",
        })
        with patch("whitemagic.tools.security.dynamic_testers._check_tool_available", return_value="/usr/bin/nuclei"), \
             patch("whitemagic.tools.security.dynamic_testers._run_tool", return_value=(0, output, "")):
            result = run_nuclei("http://target")
            assert result["status"] == "success"
            assert result["finding_count"] == 1
            assert result["findings"][0]["category"] == "web_xss_innerhtml"


class TestDynamicFindingDataclass:
    """Test DynamicFinding dataclass."""

    def test_dynamic_finding_defaults(self):
        f = DynamicFinding(
            tool="nmap",
            severity="medium",
            category="py_ssrf",
            title="Open port",
            detail="Port 80 open",
        )
        assert f.target == ""
        assert f.evidence == ""
        assert f.mitre_ttp_ids == []

    def test_dynamic_finding_with_ttps(self):
        f = DynamicFinding(
            tool="sqlmap",
            severity="critical",
            category="py_sql_injection",
            title="SQLi",
            detail="Found SQLi",
            target="http://example.com",
            evidence="proof",
            mitre_ttp_ids=["T1190", "T1213"],
        )
        assert f.mitre_ttp_ids == ["T1190", "T1213"]
