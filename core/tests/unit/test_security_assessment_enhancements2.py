"""Tests for P3/P4 Security Enhancements — Part 2.

Covers:
  - FormalVerifier.generate_spec_from_findings() (G15)
  - EchidnaBridge.generate_config_from_findings() (G16)
  - SecuritySwarm.verify_consensus() (WasmVerifier → Swarm)
  - CapabilityMatcher for bounty automation
"""

import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_enh2_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── FormalVerifier Auto-Spec from STRATA Findings (G15) ─────────────────


class TestFormalVerifierAutoSpec:
    """Test auto-generation of formal specs from STRATA findings."""

    def test_generate_spec_from_findings_with_reentrancy(self):
        from whitemagic.tools.security.formal_verifier import FormalVerifier
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        fv = FormalVerifier()
        findings = [
            Finding(
                severity=FindingSeverity.ERROR,
                category="reentrancy",
                file="Vault.sol",
                line=42,
                message="Potential reentrancy in withdraw()",
            ),
            Finding(
                severity=FindingSeverity.WARNING,
                category="access_control",
                file="Admin.sol",
                line=10,
                message="Missing onlyOwner modifier",
            ),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_formal_spec_")
        spec_path = fv.generate_spec_from_findings(findings, "Vault", output_dir)

        assert spec_path.endswith("Vault.spec")
        content = Path(spec_path).read_text()
        assert "no_reentrancy_state_change" in content
        assert "only_authorized_callers" in content

    def test_generate_spec_from_findings_empty(self):
        from whitemagic.tools.security.formal_verifier import FormalVerifier
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        fv = FormalVerifier()
        findings = [
            Finding(
                severity=FindingSeverity.INFO,
                category="style",
                file="Test.sol",
                line=1,
                message="Style issue",
            ),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_formal_empty_")
        spec_path = fv.generate_spec_from_findings(findings, "Empty", output_dir)

        content = Path(spec_path).read_text()
        assert "basic_safety" in content

    def test_generate_spec_from_findings_deduplicates(self):
        from whitemagic.tools.security.formal_verifier import FormalVerifier
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        fv = FormalVerifier()
        findings = [
            Finding(FindingSeverity.ERROR, "reentrancy", "A.sol", 1, "msg1"),
            Finding(FindingSeverity.ERROR, "reentrancy", "B.sol", 2, "msg2"),
            Finding(FindingSeverity.ERROR, "reentrancy", "C.sol", 3, "msg3"),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_formal_dedup_")
        spec_path = fv.generate_spec_from_findings(findings, "Dedup", output_dir)

        content = Path(spec_path).read_text()
        # Should only have one rule for reentrancy (deduplicated by category)
        rule_count = content.count("rule no_reentrancy_state_change")
        assert rule_count == 1

    def test_generate_spec_from_findings_dict_input(self):
        """Test that dict-based findings (from JSON) also work."""
        from whitemagic.tools.security.formal_verifier import FormalVerifier

        fv = FormalVerifier()
        findings = [
            {"category": "integer_overflow", "severity": "error", "file": "Math.sol", "line": 5},
            {"category": "tx_origin", "severity": "warning", "file": "Auth.sol", "line": 10},
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_formal_dict_")
        spec_path = fv.generate_spec_from_findings(findings, "Math", output_dir)

        content = Path(spec_path).read_text()
        assert "no_arithmetic_overflow" in content
        assert "no_tx_origin_auth" in content


# ─── EchidnaBridge Risk-Scored Config (G16) ──────────────────────────────


class TestEchidnaRiskScoredConfig:
    """Test risk-scored Echidna config generation from findings."""

    def test_generate_config_from_findings_high_severity(self):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        bridge = EchidnaBridge()
        findings = [
            Finding(FindingSeverity.ERROR, "reentrancy", "Vault.sol", 42, "Reentrancy"),
            Finding(FindingSeverity.WARNING, "access_control", "Admin.sol", 10, "Missing auth"),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_echidna_high_")
        config_path = bridge.generate_config_from_findings(findings, output_dir)

        content = Path(config_path).read_text()
        assert "testMode: exploration" in content
        assert "seqLen: 100" in content

    def test_generate_config_from_findings_low_severity(self):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        bridge = EchidnaBridge()
        findings = [
            Finding(FindingSeverity.INFO, "style", "Test.sol", 1, "Style issue"),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_echidna_low_")
        config_path = bridge.generate_config_from_findings(findings, output_dir)

        content = Path(config_path).read_text()
        assert "seqLen: 20" in content
        assert "testMode: property" in content

    def test_generate_config_from_findings_medium_severity(self):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        bridge = EchidnaBridge()
        findings = [
            Finding(FindingSeverity.WARNING, "access_control", "Admin.sol", 10, "Missing auth"),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_echidna_med_")
        config_path = bridge.generate_config_from_findings(findings, output_dir)

        content = Path(config_path).read_text()
        assert "seqLen: 50" in content

    def test_generate_config_from_findings_empty(self):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge

        bridge = EchidnaBridge()
        output_dir = tempfile.mkdtemp(prefix="wm_echidna_empty_")
        config_path = bridge.generate_config_from_findings([], output_dir)

        content = Path(config_path).read_text()
        assert "testMode: property" in content
        assert "seqLen: 20" in content

    def test_generate_config_from_findings_dos_uses_exploration(self):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge
        from whitemagic.tools.strata.models import Finding, FindingSeverity

        bridge = EchidnaBridge()
        findings = [
            Finding(FindingSeverity.ERROR, "dos", "Auction.sol", 100, "DoS via gas limit"),
        ]

        output_dir = tempfile.mkdtemp(prefix="wm_echidna_dos_")
        config_path = bridge.generate_config_from_findings(findings, output_dir)

        content = Path(config_path).read_text()
        assert "exploration" in content


# ─── WasmVerifier → Swarm Consensus (P4) ─────────────────────────────────


class TestSwarmConsensusVerification:
    """Test that SecuritySwarm.verify_consensus works."""

    def test_verify_consensus_method_exists(self):
        from whitemagic.tools.security.multi_agent import SecuritySwarm

        swarm = SecuritySwarm()
        assert hasattr(swarm, "verify_consensus")

    def test_verify_consensus_empty_findings(self):
        from whitemagic.tools.security.multi_agent import SecuritySwarm

        swarm = SecuritySwarm()
        result = swarm.verify_consensus([])
        assert result["verified_count"] == 0
        assert result["unverified_count"] == 0
        assert result["total"] == 0

    def test_verify_consensus_with_findings(self):
        from whitemagic.tools.security.multi_agent import SecuritySwarm

        swarm = SecuritySwarm()
        findings = [
            {"category": "reentrancy", "file": "Vault.sol", "line": 42, "message": "Reentrancy", "agents": ["a1", "a2"]},
        ]
        result = swarm.verify_consensus(findings)
        assert result["total"] == 1
        # Should be in verified or unverified depending on WASM availability
        assert result["verified_count"] + result["unverified_count"] == 1

    def test_verify_consensus_sets_status(self):
        from whitemagic.tools.security.multi_agent import SecuritySwarm

        swarm = SecuritySwarm()
        findings = [
            {"category": "reentrancy", "file": "Vault.sol", "line": 42, "message": "Reentrancy", "agents": ["a1", "a2"]},
        ]
        result = swarm.verify_consensus(findings)
        all_findings = result["verified"] + result["unverified"]
        for f in all_findings:
            assert "verification_status" in f


# ─── CapabilityMatcher (P3) ──────────────────────────────────────────────


class TestCapabilityMatcher:
    """Test the CapabilityMatcher for bounty automation."""

    def test_match_solidity_bounty(self):
        from whitemagic.tools.security.capability_matcher import (
            BountyRequirement,
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        reqs = [
            BountyRequirement(skill="solidity", weight=1.0),
            BountyRequirement(skill="smart_contract_audit", weight=0.8),
            BountyRequirement(skill="fuzzing", weight=0.5),
        ]

        result = matcher.match("bounty-001", reqs)
        assert result.bounty_id == "bounty-001"
        assert "strata_analyze" in result.matched_tools
        assert "echidna_fuzz" in result.matched_tools
        assert result.coverage == 1.0
        assert result.recommended is True

    def test_match_with_gap(self):
        from whitemagic.tools.security.capability_matcher import (
            BountyRequirement,
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        reqs = [
            BountyRequirement(skill="solidity", weight=1.0),
            BountyRequirement(skill="underwater_welding", weight=0.5),
        ]

        result = matcher.match("bounty-002", reqs)
        assert result.coverage < 1.0
        assert len(result.gaps) > 0
        assert any("underwater" in g for g in result.gaps)

    def test_match_no_requirements(self):
        from whitemagic.tools.security.capability_matcher import (
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        result = matcher.match("bounty-empty", [])

        assert result.coverage == 0.0
        assert result.matched_tools == []

    def test_match_reentrancy_specific(self):
        from whitemagic.tools.security.capability_matcher import (
            BountyRequirement,
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        reqs = [BountyRequirement(skill="reentrancy", weight=1.0)]

        result = matcher.match("bounty-reentrancy", reqs)
        assert "echidna_fuzz" in result.matched_tools
        assert "formal_verify" in result.matched_tools

    def test_match_defi_bounty(self):
        from whitemagic.tools.security.capability_matcher import (
            BountyRequirement,
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        reqs = [
            BountyRequirement(skill="defi", weight=1.0),
            BountyRequirement(skill="flash_loan", weight=0.8),
            BountyRequirement(skill="access_control", weight=0.6),
        ]

        result = matcher.match("bounty-defi", reqs)
        assert result.coverage == 1.0
        assert result.recommended is True
        assert "poc_verify" in result.matched_tools

    def test_list_capabilities(self):
        from whitemagic.tools.security.capability_matcher import CapabilityMatcher

        matcher = CapabilityMatcher()
        caps = matcher.list_capabilities()
        assert "solidity" in caps["skills"]
        assert "web" in caps["skills"]
        assert caps["total_tool_mappings"] > 0

    def test_match_web_bounty(self):
        from whitemagic.tools.security.capability_matcher import (
            BountyRequirement,
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        reqs = [
            BountyRequirement(skill="web", weight=1.0),
            BountyRequirement(skill="xss", weight=0.7),
            BountyRequirement(skill="sql_injection", weight=0.8),
        ]

        result = matcher.match("bounty-web", reqs)
        assert "web_security" in result.matched_tools
        assert "http_probe_get" in result.matched_tools
        assert result.coverage == 1.0

    def test_match_low_score_not_recommended(self):
        from whitemagic.tools.security.capability_matcher import (
            BountyRequirement,
            CapabilityMatcher,
        )

        matcher = CapabilityMatcher()
        reqs = [
            BountyRequirement(skill="underwater_welding", weight=1.0),
            BountyRequirement(skill="hardware_attestation", weight=1.0),
            BountyRequirement(skill="tee_attestation", weight=1.0),
        ]

        result = matcher.match("bounty-unsupported", reqs)
        assert result.coverage == 0.0
        assert result.recommended is False

    def test_singleton(self):
        from whitemagic.tools.security.capability_matcher import (
            get_capability_matcher,
        )
        from whitemagic.tools.security.capability_matcher import (
            get_capability_matcher as gcm2,
        )

        m1 = get_capability_matcher()
        m2 = gcm2()
        assert m1 is m2
