# ruff: noqa: BLE001
"""Tests for real bounty platform adapters and PoC generator."""
import time
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.agents.bounty_connector import ExternalBounty, get_bounty_connector
from whitemagic.agents.bounty_platforms import (
    CantinaPlatform,
    Code4renaPlatform,
    CodeHawksPlatform,
    HackenProofPlatform,
    ImmunefiPlatform,
    SherlockPlatform,
    _parse_iso_date,
    get_all_platforms,
    scan_all_platforms,
)
from whitemagic.tools.security.poc_generator import (
    ExploitPoC,
    generate_bounty_report,
    generate_exploit_poc,
    generate_poc_from_finding,
    list_vuln_types,
)


# ── Platform Adapter Tests ────────────────────────────────────────────


class TestImmunefiPlatform:
    """Tests for the Immunefi adapter."""

    def test_platform_name(self):
        p = ImmunefiPlatform()
        assert p.platform_name == "immunefi"

    def test_scan_bounties_mocked(self):
        """Test scan with mocked HTTP response."""
        mock_data = [
            {
                "project": "TestProtocol",
                "slug": "testprotocol",
                "maxBounty": 50000,
                "rewardsToken": "USDC",
                "endDate": "2099-12-31T23:59:59Z",
                "inviteOnly": False,
                "description": "A test protocol",
                "language": ["Solidity"],
                "ecosystem": ["Ethereum"],
                "assets": [{"url": "https://github.com/test/repo"}],
                "kyc": True,
                "programType": ["bug-bounty"],
            },
            {
                "project": "EndedProtocol",
                "slug": "ended",
                "maxBounty": 100000,
                "endDate": "2020-01-01T00:00:00Z",
                "inviteOnly": False,
            },
            {
                "project": "InviteOnly",
                "slug": "invite",
                "maxBounty": 200000,
                "inviteOnly": True,
            },
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data

        with patch("httpx.get", return_value=mock_resp):
            # Clear cache
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = ImmunefiPlatform()
            bounties = p.scan_bounties(limit=10)

        assert len(bounties) == 1  # Only the active, non-invite-only one
        assert bounties[0].title == "TestProtocol"
        assert bounties[0].reward == 50000
        assert bounties[0].currency == "USDC"
        assert bounties[0].url == "https://immunefi.com/bounty/testprotocol/"

    def test_scan_bounties_api_error(self):
        """Test scan handles API errors gracefully."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("httpx.get", return_value=mock_resp):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = ImmunefiPlatform()
            bounties = p.scan_bounties()

        assert bounties == []

    def test_scan_bounties_network_error(self):
        """Test scan handles network errors gracefully."""
        with patch("httpx.get", side_effect=Exception("Network error")):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = ImmunefiPlatform()
            bounties = p.scan_bounties()

        assert bounties == []

    def test_claim_bounty_not_supported(self):
        p = ImmunefiPlatform()
        assert p.claim_bounty("test", "agent1") is False

    def test_submit_result_not_supported(self):
        p = ImmunefiPlatform()
        assert p.submit_result("test", {}) is False


class TestCodeHawksPlatform:
    """Tests for the CodeHawks adapter."""

    def test_platform_name(self):
        p = CodeHawksPlatform()
        assert p.platform_name == "codehawks"

    def test_scan_fallback(self):
        """Test scan falls back to known competitions when API unavailable."""
        with patch("httpx.get", side_effect=Exception("No API")):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = CodeHawksPlatform()
            bounties = p.scan_bounties()

        assert len(bounties) >= 1
        assert any("BattleChain" in b.title for b in bounties)

    def test_claim_not_supported(self):
        p = CodeHawksPlatform()
        assert p.claim_bounty("test", "agent1") is False


class TestSherlockPlatform:
    """Tests for the Sherlock adapter."""

    def test_platform_name(self):
        p = SherlockPlatform()
        assert p.platform_name == "sherlock"

    def test_scan_fallback(self):
        """Test scan falls back to known contests when API unavailable."""
        with patch("httpx.get", side_effect=Exception("No API")):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = SherlockPlatform()
            bounties = p.scan_bounties()

        assert len(bounties) >= 1
        assert any("Metric" in b.title for b in bounties)


class TestCode4renaPlatform:
    """Tests for the Code4rena adapter."""

    def test_platform_name(self):
        p = Code4renaPlatform()
        assert p.platform_name == "code4rena"

    def test_scan_fallback(self):
        """Test scan returns placeholder when API unavailable."""
        with patch("httpx.get", side_effect=Exception("No API")):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = Code4renaPlatform()
            bounties = p.scan_bounties()

        assert len(bounties) >= 1
        assert "code4rena.com" in bounties[0].url


class TestHackenProofPlatform:
    """Tests for the HackenProof adapter."""

    def test_platform_name(self):
        p = HackenProofPlatform()
        assert p.platform_name == "hackenproof"

    def test_scan_fallback(self):
        """Test scan falls back to known programs when API unavailable."""
        with patch("httpx.get", side_effect=Exception("No API")):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = HackenProofPlatform()
            bounties = p.scan_bounties()

        assert len(bounties) >= 10  # 17 known programs
        assert any("Telcoin" in b.title for b in bounties)
        assert any("Citrea" in b.title for b in bounties)


class TestCantinaPlatform:
    """Tests for the Cantina adapter."""

    def test_platform_name(self):
        p = CantinaPlatform()
        assert p.platform_name == "cantina"

    def test_scan_fallback(self):
        """Test scan returns placeholder when API unavailable."""
        with patch("httpx.get", side_effect=Exception("No API")):
            from whitemagic.agents import bounty_platforms
            bounty_platforms._cache = bounty_platforms._PlatformCache()

            p = CantinaPlatform()
            bounties = p.scan_bounties()

        assert len(bounties) >= 1
        assert "cantina.xyz" in bounties[0].url


# ── Aggregation Tests ─────────────────────────────────────────────────


class TestScanAllPlatforms:
    """Tests for the scan_all_platforms aggregator."""

    def test_get_all_platforms(self):
        platforms = get_all_platforms()
        assert len(platforms) == 10
        names = {p.platform_name for p in platforms}
        assert names == {"immunefi", "codehawks", "sherlock", "code4rena", "hackenproof", "cantina", "opire", "algora", "huntr", "taskbounty"}

    def test_scan_all_platforms(self):
        """Test scanning all platforms with mocked failures (should use fallbacks)."""
        from whitemagic.agents import bounty_platforms
        bounty_platforms._cache = bounty_platforms._PlatformCache()

        with patch("httpx.get", side_effect=Exception("No network")):
            results = scan_all_platforms(limit_per_platform=5)

        assert len(results) == 10
        # At least some platforms should have fallback data
        total = sum(len(v) for v in results.values())
        assert total > 0


# ── Auto-Registration Tests ───────────────────────────────────────────


class TestAutoRegistration:
    """Test that platforms are auto-registered with the connector."""

    def test_connector_has_real_platforms(self):
        """Verify the connector singleton has real platforms registered."""
        # Reset singleton to test auto-registration
        import whitemagic.agents.bounty_connector as bc
        bc._connector = None

        connector = get_bounty_connector()
        status = connector.get_status()
        platform_names = status["platforms"]

        assert "immunefi" in platform_names
        assert "codehawks" in platform_names
        assert "sherlock" in platform_names
        assert "code4rena" in platform_names
        assert "hackenproof" in platform_names
        assert "cantina" in platform_names

        # Cleanup
        bc._connector = None


# ── Helper Tests ──────────────────────────────────────────────────────


class TestParseIsoDate:
    """Tests for the _parse_iso_date helper."""

    def test_valid_iso_date(self):
        ts = _parse_iso_date("2026-07-16T23:59:59Z")
        assert ts is not None
        assert ts > 1_700_000_000  # After 2023

    def test_date_only(self):
        ts = _parse_iso_date("2026-07-16")
        assert ts is not None

    def test_invalid_date(self):
        assert _parse_iso_date("not a date") is None

    def test_empty_string(self):
        assert _parse_iso_date("") is None

    def test_none_input(self):
        assert _parse_iso_date(None) is None  # type: ignore[arg-type]


# ── PoC Generator Tests ───────────────────────────────────────────────


class TestPoCGenerator:
    """Tests for the Foundry PoC generator."""

    def test_generate_reentrancy_poc(self):
        result = generate_exploit_poc(
            vuln_type="reentrancy",
            contract_name="VulnerableVault",
            function_name="withdraw",
            description="The withdraw function sends ETH before updating balance",
        )
        assert result.success
        assert result.vuln_type == "reentrancy"
        assert result.contract_name == "VulnerableVault"
        assert "VulnerableVault" in result.test_code
        assert "withdraw" in result.test_code
        assert "AttackerContract" in result.test_code
        assert "test_reentrancy_exploit" in result.test_code

    def test_generate_access_control_poc(self):
        result = generate_exploit_poc(
            vuln_type="access_control",
            contract_name="AdminPanel",
            function_name="setAdmin",
        )
        assert result.success
        assert "AdminPanel" in result.test_code
        assert "setAdmin" in result.test_code
        assert "test_access_control_bypass" in result.test_code

    def test_generate_integer_overflow_poc(self):
        result = generate_exploit_poc(
            vuln_type="integer_overflow",
            contract_name="Token",
            function_name="transfer",
        )
        assert result.success
        assert "Token" in result.test_code
        assert "test_integer_overflow" in result.test_code

    def test_generate_tx_origin_poc(self):
        result = generate_exploit_poc(
            vuln_type="tx_origin",
            contract_name="Wallet",
            function_name="withdraw",
        )
        assert result.success
        assert "PhishingContract" in result.test_code
        assert "test_tx_origin_phishing" in result.test_code

    def test_generate_selfdestruct_poc(self):
        result = generate_exploit_poc(
            vuln_type="selfdestruct",
            contract_name="DangerousContract",
            function_name="destroy",
        )
        assert result.success
        assert "test_self_destruct" in result.test_code

    def test_generate_front_running_poc(self):
        result = generate_exploit_poc(
            vuln_type="front_running",
            contract_name="DEX",
            function_name="swap",
        )
        assert result.success
        assert "test_front_running" in result.test_code

    def test_generate_generic_poc(self):
        result = generate_exploit_poc(
            vuln_type="unknown_vuln",
            contract_name="Custom",
            function_name="doStuff",
        )
        assert result.success
        assert "Custom" in result.test_code
        assert "test_exploit" in result.test_code

    def test_generate_poc_with_project_dir(self, tmp_path):
        """Test that PoC is written to a file when project_dir is provided."""
        project = tmp_path / "foundry_project"
        project.mkdir()
        (project / "foundry.toml").write_text("[profile.default]\n")

        result = generate_exploit_poc(
            vuln_type="reentrancy",
            contract_name="Vault",
            function_name="withdraw",
            project_dir=str(project),
        )
        assert result.success
        assert result.test_file != ""
        assert "PoC_reentrancy_" in result.test_file
        assert (project / "test").exists()

    def test_list_vuln_types(self):
        types = list_vuln_types()
        assert "reentrancy" in types
        assert "access_control" in types
        assert "integer_overflow" in types
        assert "tx_origin" in types
        assert "selfdestruct" in types
        assert "front_running" in types
        assert "generic" in types

    def test_generate_poc_from_finding(self):
        """Test generating PoC from a Slither-style finding dict."""
        finding = {
            "title": "Vault.withdraw() - Reentrancy",
            "severity": "high",
            "category": "reentrancy-eth",
            "file": "src/Vault.sol",
            "line": 42,
            "description": "The withdraw function sends ETH before updating balance",
            "message": "Reentrancy in Vault.withdraw()",
        }
        result = generate_poc_from_finding(finding)
        assert result.success
        assert result.vuln_type == "reentrancy"
        assert result.contract_name == "Vault"
        assert "withdraw" in result.test_code

    def test_generate_poc_from_finding_unknown_category(self):
        """Test that unknown categories fall back to generic."""
        finding = {
            "title": "SomeContract.someFunc() - Unknown bug",
            "category": "custom-bug-type",
            "file": "src/SomeContract.sol",
            "description": "Some unknown vulnerability",
        }
        result = generate_poc_from_finding(finding)
        assert result.success
        assert result.vuln_type == "generic"


# ── Bounty Report Generator Tests ─────────────────────────────────────


class TestBountyReportGenerator:
    """Tests for the bounty submission report generator."""

    def test_immunefi_report_format(self):
        report = generate_bounty_report(
            title="Reentrancy in Vault.withdraw()",
            severity="high",
            description="The withdraw function sends ETH before updating balance",
            impact="An attacker can drain all funds from the vault",
            proof_of_concept="// PoC code here",
            mitigation="Update state before external calls (CEI pattern)",
            platform="immunefi",
        )
        assert "Reentrancy in Vault.withdraw()" in report
        assert "HIGH" in report
        assert "Vulnerability Detail" in report
        assert "Proof of Concept" in report
        assert "Recommendation" in report

    def test_code4rena_report_format(self):
        report = generate_bounty_report(
            title="Access control bypass",
            severity="medium",
            description="Missing onlyOwner modifier",
            impact="Unauthorized users can call admin functions",
            proof_of_concept="// PoC",
            mitigation="Add onlyOwner modifier",
            platform="code4rena",
        )
        assert "# Access control bypass" in report
        assert "## Impact" in report
        assert "## Proof of Concept" in report
        assert "## Recommended Mitigation Steps" in report

    def test_sherlock_report_format(self):
        report = generate_bounty_report(
            title="Integer overflow",
            severity="low",
            description="Unchecked arithmetic",
            impact="Potential state corruption",
            proof_of_concept="// PoC",
            mitigation="Use SafeMath",
            platform="sherlock",
        )
        assert "## Integer overflow" in report
        assert "### Severity" in report
        assert "### Vulnerability Detail" in report

    def test_generic_report_format(self):
        report = generate_bounty_report(
            title="Test finding",
            severity="info",
            description="Test description",
            impact="Test impact",
            proof_of_concept="Test PoC",
            mitigation="Test mitigation",
            platform="unknown",
        )
        assert "Test finding" in report
        assert "Test description" in report

    def test_default_severity_impact(self):
        """Test that severity-based impact is used when impact is empty."""
        report = generate_bounty_report(
            title="Test",
            severity="critical",
            description="Test",
            impact="",
            proof_of_concept="",
            mitigation="",
        )
        assert "Funds can be stolen directly" in report
