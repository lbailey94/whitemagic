"""Tests for gap-filling security work — PoC templates, integer overflow checker,
memory-augmented checker, HTTP probe, Echidna, fix generator, report scraper,
PoC pipeline, MCP wiring, contest pipeline platforms."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestNewPoCTemplates:
    """Test 7 new PoC templates."""

    def test_flash_loan_template_registered(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        t = get_codegenome_engine().get_template("poc_flash_loan")
        assert t is not None
        assert "security" in t.tags

    def test_flash_loan_render_default(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_flash_loan", price_function="getPrice", exploit_function="swap")
        assert "FlashLoanPoC" in code
        assert "getPrice" in code
        assert "swap" in code

    def test_flash_loan_render_xianfeng(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_flash_loan", tier="xianfeng", exploit_function="swap")
        assert "FlashLoanPoC" in code
        assert "swap" in code

    def test_flash_loan_render_huben(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_flash_loan", tier="huben", price_function="getPrice", exploit_function="swap")
        assert "Test" in code
        assert "assertNotEq" in code

    def test_oracle_manipulation_template(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_oracle_manipulation", trade_function="swap")
        assert "OracleManipulationPoC" in code
        assert "swap" in code

    def test_storage_collision_template(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_storage_collision", admin_function="setAdmin")
        assert "StorageCollisionPoC" in code
        assert "setAdmin" in code

    def test_signature_replay_template(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_signature_replay", verify_function="execute")
        assert "SignatureReplayPoC" in code
        assert "execute" in code

    def test_sqli_template(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_sqli", target_url="http://example.com/search", param_name="q")
        assert "requests" in code
        assert "example.com" in code

    def test_xss_template(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_xss", target_url="http://example.com/page", param_name="input")
        assert "requests" in code
        assert "alert" in code

    def test_idor_template(self):
        from whitemagic.codegenome.engine import get_codegenome_engine
        code = get_codegenome_engine().render("poc_idor", base_url="http://example.com", resource_path="api/users")
        assert "requests" in code
        assert "example.com" in code

    def test_all_new_vibeparser_aliases(self):
        from whitemagic.codegenome.vibe_parser import get_vibe_parser
        p = get_vibe_parser()
        for kw, expected in [
            ("flash loan poc", "poc_flash_loan"),
            ("oracle manipulation", "poc_oracle_manipulation"),
            ("storage collision", "poc_storage_collision"),
            ("signature replay", "poc_signature_replay"),
            ("sqli poc", "poc_sqli"),
            ("xss poc", "poc_xss"),
            ("idor poc", "poc_idor"),
        ]:
            r = p.parse(kw)
            assert r["status"] == "matched", f"{kw} not matched"
            assert r["template_name"] == expected, f"{kw} -> {r.get('template_name')} != {expected}"


class TestIntegerOverflowChecker:
    """Test the integer overflow Solidity checker."""

    def test_pre_08_without_safemath(self, tmp_path):
        from whitemagic.tools.strata.checkers.solidity_security import check_solidity_integer_overflow
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        sol = tmp_path / "Vuln.sol"
        sol.write_text(
            "pragma solidity ^0.7.0;\n"
            "contract Vuln {\n"
            "    mapping(address => uint256) public balances;\n"
            "    function add(address a, uint256 amount) public {\n"
            "        balances[a] += amount;\n"
            "    }\n"
            "}\n"
        )
        fi = FileIndex(tmp_path)
        findings = []
        check_solidity_integer_overflow(tmp_path, fi, findings)
        assert any(f.category == "sol_integer_overflow_pre08" for f in findings)

    def test_pre_08_with_safemath_no_finding(self, tmp_path):
        from whitemagic.tools.strata.checkers.solidity_security import check_solidity_integer_overflow
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        sol = tmp_path / "Safe.sol"
        sol.write_text(
            "pragma solidity ^0.7.0;\n"
            "import '@openzeppelin/utils/math/SafeMath.sol';\n"
            "using SafeMath for uint256;\n"
            "contract Safe {\n"
            "    mapping(address => uint256) public balances;\n"
            "    function add(address a, uint256 amount) public {\n"
            "        balances[a] = balances[a].add(amount);\n"
            "    }\n"
            "}\n"
        )
        fi = FileIndex(tmp_path)
        findings = []
        check_solidity_integer_overflow(tmp_path, fi, findings)
        assert not any(f.category == "sol_integer_overflow_pre08" for f in findings)

    def test_unchecked_block(self, tmp_path):
        from whitemagic.tools.strata.checkers.solidity_security import check_solidity_integer_overflow
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        sol = tmp_path / "Unchecked.sol"
        sol.write_text(
            "pragma solidity ^0.8.0;\n"
            "contract Unchecked {\n"
            "    mapping(address => uint256) public balances;\n"
            "    function sub(address a, uint256 amount) public {\n"
            "        unchecked {\n"
            "            balances[a] -= amount;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        fi = FileIndex(tmp_path)
        findings = []
        check_solidity_integer_overflow(tmp_path, fi, findings)
        assert any(f.category == "sol_unchecked_block" for f in findings)

    def test_08_with_auto_checks_no_finding(self, tmp_path):
        from whitemagic.tools.strata.checkers.solidity_security import check_solidity_integer_overflow
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        sol = tmp_path / "Safe08.sol"
        sol.write_text(
            "pragma solidity ^0.8.20;\n"
            "contract Safe08 {\n"
            "    mapping(address => uint256) public balances;\n"
            "    function add(address a, uint256 amount) public {\n"
            "        balances[a] += amount;\n"
            "    }\n"
            "}\n"
        )
        fi = FileIndex(tmp_path)
        findings = []
        check_solidity_integer_overflow(tmp_path, fi, findings)
        assert not any(f.category == "sol_integer_overflow_pre08" for f in findings)


class TestMCPWiring:
    """Test that all security tools are wired into dispatch table and PRAT."""

    def test_all_security_tools_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        tools = [
            "foundry.build", "foundry.test", "foundry.test_json",
            "abi.parse", "abi.summarize", "abi.decode_calldata",
            "vuln.search", "vuln.status", "vuln.ingest_report",
            "contest.add_finding", "contest.format", "contest.status",
            "oss.scan_repo", "oss.scan_org", "security.status",
            "poc.generate", "poc.verify", "contest.prepare",
            "http_probe.get", "http_probe.post", "http_probe.xss",
            "http_probe.sqli", "http_probe.idor", "http_probe.ssrf",
            "api.state_machine", "echidna.fuzz", "echidna.status",
            "fix.generate", "fix.apply", "pr.create", "bounty.track",
            "report.scrape", "report.ingest",
        ]
        for t in tools:
            assert t in DISPATCH_TABLE, f"{t} not in DISPATCH_TABLE"

    def test_all_security_tools_in_prat(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        tools = [
            "foundry.build", "foundry.test", "foundry.test_json",
            "abi.parse", "abi.summarize", "abi.decode_calldata",
            "vuln.search", "vuln.status", "vuln.ingest_report",
            "contest.add_finding", "contest.format", "contest.status",
            "oss.scan_repo", "oss.scan_org", "security.status",
            "poc.generate", "poc.verify", "contest.prepare",
            "http_probe.get", "http_probe.post", "http_probe.xss",
            "http_probe.sqli", "http_probe.idor", "http_probe.ssrf",
            "api.state_machine", "echidna.fuzz", "echidna.status",
            "fix.generate", "fix.apply", "pr.create", "bounty.track",
            "report.scrape", "report.ingest",
        ]
        for t in tools:
            assert t in TOOL_TO_GANA, f"{t} not in TOOL_TO_GANA"

    def test_registry_defs_collected(self):
        from whitemagic.tools.registry_defs import collect
        tools = collect()
        sec_names = {t.name for t in tools if t.category.value == "security"}
        assert "foundry.build" in sec_names
        assert "poc.verify" in sec_names
        assert "http_probe.xss" in sec_names
        assert "echidna.fuzz" in sec_names
        assert "fix.generate" in sec_names
        assert "report.scrape" in sec_names


class TestMemoryAugmentedChecker:
    """Test memory-augmented STRATA checker and Dream Cycle integration."""

    def test_check_memory_patterns_escalates(self, tmp_path):
        from whitemagic.tools.security.memory_checker import check_memory_patterns
        from whitemagic.tools.strata.checkers.solidity import FileIndex, Finding, FindingSeverity
        fi = FileIndex(tmp_path)
        # Use a finding with keywords that match built-in WM-REENTRANCY-001 pattern
        findings = [Finding(
            severity=FindingSeverity.INFO,
            category="sol_reentrancy",
            file="test.sol",
            line=10,
            message="External call before state update — call transfer withdraw balances",
            suggestion="",
        )]
        check_memory_patterns(tmp_path, fi, findings)
        assert findings[0].severity == FindingSeverity.WARNING
        assert "Pattern:" in findings[0].message

    def test_dream_cycle_consolidation(self):
        from whitemagic.tools.security.memory_checker import dream_cycle_consolidation
        findings = [
            {"category": "sol_reentrancy", "file": "a.sol", "severity": "warning"},
            {"category": "sol_reentrancy", "file": "b.sol", "severity": "warning"},
            {"category": "sol_reentrancy", "file": "c.sol", "severity": "warning"},
            {"category": "sqli_fstring", "file": "app.py", "severity": "error"},
        ]
        result = dream_cycle_consolidation(findings)
        assert result["total_findings"] == 4
        assert result["categories"] == 2
        assert len(result["recurring_patterns"]) == 1

    def test_dream_cycle_serendipity(self):
        from whitemagic.tools.security.memory_checker import dream_cycle_serendipity
        findings = [
            {"category": "sol_access_control", "file": "contract.sol", "message": "Missing access control"},
            {"category": "sqli_fstring", "file": "app.py", "message": "SQL injection via f-string"},
        ]
        connections = dream_cycle_serendipity(findings)
        assert isinstance(connections, list)

    def test_dream_cycle_prediction(self):
        from whitemagic.tools.security.memory_checker import dream_cycle_prediction
        findings = [{"category": "sol_reentrancy", "file": "test.sol", "severity": "warning"}]
        predictions = dream_cycle_prediction(findings)
        assert isinstance(predictions, list)


class TestHTTPProbe:
    """Test HTTP probe tool."""

    def test_http_probe_init(self):
        from whitemagic.tools.security.http_probe import HTTPProbe
        probe = HTTPProbe(timeout=5)
        assert probe._timeout == 5
        assert probe.history == []

    def test_http_probe_clear_history(self):
        from whitemagic.tools.security.http_probe import HTTPProbe
        probe = HTTPProbe()
        probe._history.append({"test": True})
        probe.clear_history()
        assert probe.history == []

    def test_http_probe_get_mocked(self):
        from whitemagic.tools.security.http_probe import HTTPProbe
        probe = HTTPProbe()
        with patch("requests.request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"Content-Type": "text/html"}
            mock_resp.text = "<html>OK</html>"
            mock_req.return_value = mock_resp
            r = probe.get("http://example.com")
            assert r.status_code == 200
            assert "OK" in r.body
            assert len(probe.history) == 1


class TestEchidnaBridge:
    """Test Echidna bridge."""

    def test_echidna_status(self):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge
        bridge = EchidnaBridge()
        status = bridge.status()
        assert "available" in status
        assert "timeout" in status

    def test_echidna_generate_config(self, tmp_path):
        from whitemagic.tools.security.echidna_bridge import EchidnaBridge
        bridge = EchidnaBridge()
        config_path = bridge.generate_config(str(tmp_path), test_mode="property", seq_len=20)
        assert Path(config_path).exists()
        content = Path(config_path).read_text()
        assert "property" in content
        assert "seqLen: 20" in content


class TestFixGenerator:
    """Test fix template generation."""

    def test_generate_fix_tx_origin(self):
        from whitemagic.tools.security.fix_generator import generate_fix
        fix = generate_fix("test.sol", 5, "sol_tx_origin_auth", "require(tx.origin == owner);")
        assert fix is not None
        assert "msg.sender" in fix.fixed
        assert fix.fix_type == "access_control"

    def test_generate_fix_innerhtml(self):
        from whitemagic.tools.security.fix_generator import generate_fix
        fix = generate_fix("app.js", 10, "xss_innerhtml", "element.innerHTML = userInput;")
        assert fix is not None
        assert "textContent" in fix.fixed

    def test_generate_fix_unknown_category(self):
        from whitemagic.tools.security.fix_generator import generate_fix
        fix = generate_fix("test.sol", 1, "unknown_category", "some code")
        assert fix is None

    def test_apply_fix_dry_run(self, tmp_path):
        from whitemagic.tools.security.fix_generator import FixSuggestion, apply_fix
        f = tmp_path / "test.sol"
        f.write_text("line1\nrequire(tx.origin == owner);\nline3\n")
        fix = FixSuggestion(str(f), 2, "require(tx.origin == owner);", "require(msg.sender == owner);", "access_control", "test")
        result = apply_fix(fix, dry_run=True)
        assert result["success"]
        assert result["dry_run"]
        assert "msg.sender" in result["fixed"]

    def test_track_bounty_earnings(self):
        from whitemagic.tools.security.fix_generator import track_bounty_earnings
        record = track_bounty_earnings("algora", "$500", "https://github.com/repo/issues/1", "pending")
        assert record["type"] == "bounty_earnings"
        assert record["source"] == "algora"
        assert record["amount"] == "$500"
        assert record["status"] == "pending"


class TestReportScraper:
    """Test public report scraper."""

    def test_scraper_init(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper()
        assert "code4rena" in scraper.PLATFORMS
        assert "sherlock" in scraper.PLATFORMS
        assert "codehawks" in scraper.PLATFORMS

    def test_scraper_parse_findings(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper()
        text = "## [H] Reentrancy in withdraw function\n\nThis allows an attacker to drain funds.\n\n## [M] Missing input validation\n\nUser input not validated."
        findings = scraper._parse_findings(text, "code4rena")
        assert len(findings) >= 1
        assert findings[0]["severity"] == "high"
        assert "Reentrancy" in findings[0]["title"]

    def test_scraper_extract_contest_name(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper()
        name = scraper._extract_contest_name("https://code4rena.com/reports/protocol-xyz", "")
        assert "Protocol" in name or "protocol" in name


class TestPoCPipeline:
    """Test PoC verification pipeline."""

    def test_generate_poc(self):
        from whitemagic.tools.security.poc_pipeline import generate_poc
        code = generate_poc("poc_reentrancy", {"target_address": "0x1234", "withdraw_function": "withdraw"})
        assert "ReentrancyPoC" in code or "reentrancy" in code.lower()

    def test_governance_check_approved(self):
        from whitemagic.tools.security.poc_pipeline import _check_governance
        os.environ["WM_POC_APPROVED"] = "0xabc,0xdef"
        assert _check_governance("0xabc") is True
        del os.environ["WM_POC_APPROVED"]

    def test_governance_check_permissive(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.security.poc_pipeline import _check_governance
        os.environ.pop("WM_POC_APPROVED", None)
        os.environ.pop("WM_POC_AUTO_APPROVE", None)
        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            assert _check_governance("unknown") is True
        finally:
            engine.set_profile(original)


class TestContestPipelinePlatforms:
    """Test HackerOne and Bugcrowd platform support."""

    def test_hackerone_platform_exists(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        assert "hackerone" in ContestPipeline.PLATFORMS

    def test_bugcrowd_platform_exists(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        assert "bugcrowd" in ContestPipeline.PLATFORMS

    def test_bugcrowd_severity_map(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        sm = ContestPipeline.PLATFORMS["bugcrowd"]["severity_map"]
        assert sm["critical"] == "P1"
        assert sm["high"] == "P2"
        assert sm["medium"] == "P3"

    def test_hackerone_severity_map(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        sm = ContestPipeline.PLATFORMS["hackerone"]["severity_map"]
        assert sm["critical"] == "Critical"
        assert sm["info"] == "Informational"

    def test_format_for_hackerone(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        pipeline = ContestPipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        pipeline.add_finding("Test XSS", "high", "xss", "app.js", 10, "XSS found", "User data exposed", "alert(1)", "Escape output")
        result = pipeline.format_for_platform("hackerone")
        assert "High" in result
        assert "Test XSS" in result

    def test_format_for_bugcrowd(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        pipeline = ContestPipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        pipeline.add_finding("Test SQLi", "critical", "sqli", "app.py", 5, "SQLi found", "Data leak", "' OR 1=1", "Parameterize")
        result = pipeline.format_for_platform("bugcrowd")
        assert "Test SQLi" in result
        assert "critical" in result.lower() or "P1" in result
