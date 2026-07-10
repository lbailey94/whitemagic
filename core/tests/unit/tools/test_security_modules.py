"""Tests for Phase 2-6 security modules — Foundry bridge, ABI decoder, vuln KB, contest, OSS."""
import json
import pytest

from whitemagic.tools.security.foundry_bridge import FoundryBridge, FoundryResult
from whitemagic.tools.security.abi_decoder import parse_abi, decode_calldata, summarize_abi, extract_events
from whitemagic.tools.security.vuln_knowledge import get_vuln_knowledge_base, VulnKnowledgeBase, VulnerabilityPattern
from whitemagic.tools.security.contest_pipeline import get_contest_pipeline, ContestPipeline, ContestFinding
from whitemagic.tools.security.oss_scanner import get_oss_scanner, OSSBountyScanner, BountyIssue
from whitemagic.tools.handlers.security_tools import (
    handle_vuln_search, handle_vuln_status, handle_contest_status,
    handle_contest_add_finding, handle_contest_format,
    handle_abi_parse, handle_abi_summarize, handle_abi_decode_calldata,
    handle_security_status,
)


SAMPLE_ABI = json.dumps([
    {"type": "function", "name": "transfer", "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable"},
    {"type": "function", "name": "balanceOf", "inputs": [{"name": "owner", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"type": "event", "name": "Transfer", "inputs": [{"name": "from", "type": "address", "indexed": True}, {"name": "to", "type": "address", "indexed": True}, {"name": "value", "type": "uint256"}], "anonymous": False},
])


class TestFoundryBridge:
    def test_status(self):
        bridge = FoundryBridge()
        status = bridge.status()
        assert "available" in status
        assert "forge" in status
        assert "project_dir" in status

    def test_build_without_forge(self):
        bridge = FoundryBridge("/tmp")
        result = bridge.build()
        # May or may not have forge, but should return a FoundryResult
        assert isinstance(result, FoundryResult)

    def test_test_without_forge(self):
        bridge = FoundryBridge("/tmp")
        result = bridge.test()
        assert isinstance(result, FoundryResult)


class TestABIDecoder:
    def test_parse_abi(self):
        sigs = parse_abi(SAMPLE_ABI)
        assert len(sigs) == 2
        assert sigs[0].name == "transfer"
        assert sigs[1].name == "balanceOf"
        assert sigs[0].state_mutability == "nonpayable"
        assert sigs[1].state_mutability == "view"

    def test_parse_abi_invalid_json(self):
        sigs = parse_abi("not json")
        assert sigs == []

    def test_summarize_abi(self):
        summary = summarize_abi(SAMPLE_ABI)
        assert summary["total_functions"] == 2
        assert summary["total_events"] == 1
        assert "transfer" in summary["function_names"]
        assert "Transfer" in summary["event_names"]

    def test_decode_calldata_no_abi(self):
        decoded = decode_calldata("0xa9059cbb" + "0" * 64 + "0" * 64)
        assert decoded.selector == "0xa9059cbb"
        assert len(decoded.parameters) == 2

    def test_decode_calldata_short(self):
        decoded = decode_calldata("0x1234")
        assert decoded.selector == "0x1234"
        assert decoded.parameters == []

    def test_extract_events(self):
        events = extract_events(SAMPLE_ABI)
        assert len(events) == 1
        assert events[0]["name"] == "Transfer"


class TestVulnKnowledgeBase:
    def test_builtin_patterns(self):
        kb = get_vuln_knowledge_base()
        status = kb.status()
        assert status["total_patterns"] >= 9
        assert "reentrancy" in status["categories"]

    def test_search_by_category(self):
        kb = get_vuln_knowledge_base()
        results = kb.search_by_category("reentrancy")
        assert len(results) >= 1
        assert results[0].name == "Reentrancy in withdrawal function"

    def test_search_by_keyword(self):
        kb = get_vuln_knowledge_base()
        results = kb.search_by_keyword("oracle")
        assert len(results) >= 1

    def test_add_custom_pattern(self):
        kb = VulnKnowledgeBase()
        pattern = VulnerabilityPattern(
            pattern_id="CUSTOM-001",
            name="Custom vuln",
            category="custom",
            severity="medium",
            description="A custom vulnerability",
        )
        kb.add_pattern(pattern)
        assert kb.get_pattern("CUSTOM-001") is not None

    def test_ingest_audit_report(self):
        kb = VulnKnowledgeBase()
        report = """# Audit Report

## High: Reentrancy in withdraw function
The withdraw function has a reentrancy vulnerability.

## Medium: Missing input validation
User input is not validated.

## Low: Gas optimization
Loop can be optimized.
"""
        count = kb.ingest_audit_report(report)
        assert count >= 2

    def test_match_findings(self):
        kb = get_vuln_knowledge_base()
        findings = [
            {"category": "sol_tx_origin_auth", "message": "tx.origin used for authorization"},
            {"category": "sol_cei_violation", "message": "State update after external call reentrancy"},
        ]
        matched = kb.match_findings(findings)
        assert len(matched) >= 1


class TestContestPipeline:
    def test_add_finding(self):
        pipeline = ContestPipeline()
        finding = pipeline.add_finding(
            title="Test reentrancy",
            severity="high",
            category="reentrancy",
            file="Vault.sol",
            line=42,
            description="Reentrancy in withdraw",
            impact="Funds can be drained",
            proof_of_concept="contract PoC { }",
            mitigation="Use ReentrancyGuard",
        )
        assert finding is not None
        assert finding.finding_id.startswith("WM-")

    def test_dedup(self):
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="Test",
            severity="high",
            category="reentrancy",
            file="Vault.sol",
            line=42,
            description="Test",
            impact="Test",
            proof_of_concept="",
            mitigation="Test",
        )
        dup = pipeline.add_finding(
            title="Test",
            severity="high",
            category="reentrancy",
            file="Vault.sol",
            line=42,
            description="Test",
            impact="Test",
            proof_of_concept="",
            mitigation="Test",
        )
        assert dup is None

    def test_format_code4rena(self):
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="Reentrancy",
            severity="high",
            category="reentrancy",
            file="Vault.sol",
            line=10,
            description="Reentrancy bug",
            impact="Funds drained",
            proof_of_concept="contract PoC {}",
            mitigation="Use guard",
        )
        report = pipeline.format_for_platform("code4rena")
        assert "Code4Rena" in report
        assert "Reentrancy" in report
        assert "Vault.sol" in report

    def test_format_unknown_platform(self):
        pipeline = ContestPipeline()
        result = pipeline.format_for_platform("unknown")
        assert "Unknown" in result

    def test_status(self):
        pipeline = ContestPipeline()
        status = pipeline.status()
        assert "total_findings" in status
        assert "platforms" in status


class TestOSSScanner:
    def test_status(self):
        scanner = get_oss_scanner()
        status = scanner.status()
        assert "algora_labels" in status
        assert "opire_labels" in status

    def test_extract_bounty_amount(self):
        scanner = get_oss_scanner()
        assert scanner._extract_bounty_amount("Bounty: $500") == "$500"
        assert scanner._extract_bounty_amount("$1,000 for this") == "$1000"
        assert scanner._extract_bounty_amount("100.00 USD") == "$100.00"
        assert scanner._extract_bounty_amount("No money here") is None

    def test_detect_platform(self):
        scanner = get_oss_scanner()
        assert scanner._detect_platform(["bounty", "algora"]) == "algora"
        assert scanner._detect_platform(["opire"]) == "opire"
        assert scanner._detect_platform(["bug"]) is None


class TestMCPHandlers:
    def test_vuln_search(self):
        result = handle_vuln_search(query="reentrancy")
        assert result["count"] >= 1
        assert any(r["name"] == "Reentrancy in withdrawal function" for r in result["results"])

    def test_vuln_status(self):
        result = handle_vuln_status()
        assert "total_patterns" in result

    def test_contest_status(self):
        result = handle_contest_status()
        assert "total_findings" in result

    def test_contest_add_and_format(self):
        handle_contest_add_finding(
            title="Test vuln",
            severity="high",
            category="reentrancy",
            file="Test.sol",
            line=1,
            description="Test",
            impact="Test",
            proof_of_concept="",
            mitigation="Test",
        )
        result = handle_contest_format(platform="sherlock")
        assert "Sherlock" in result["report"]

    def test_abi_parse_handler(self):
        result = handle_abi_parse(abi_json=SAMPLE_ABI)
        assert len(result["signatures"]) == 2
        assert "transfer(address,uint256)" in result["signatures"]

    def test_abi_summarize_handler(self):
        result = handle_abi_summarize(abi_json=SAMPLE_ABI)
        assert result["total_functions"] == 2

    def test_abi_decode_handler(self):
        result = handle_abi_decode_calldata(calldata="0xa9059cbb" + "00" * 64)
        assert result["selector"] == "0xa9059cbb"

    def test_security_status(self):
        result = handle_security_status()
        assert "foundry" in result
        assert "vuln_kb" in result
        assert "contest" in result
