"""Tests for gap-filling security work — PoC templates, integer overflow checker,
memory-augmented checker, HTTP probe, Echidna, fix generator, report scraper,
PoC pipeline, MCP wiring, contest pipeline platforms."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch


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
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        from whitemagic.tools.strata.checkers.solidity_security import (
            check_solidity_integer_overflow,
        )
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
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        from whitemagic.tools.strata.checkers.solidity_security import (
            check_solidity_integer_overflow,
        )
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
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        from whitemagic.tools.strata.checkers.solidity_security import (
            check_solidity_integer_overflow,
        )
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
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        from whitemagic.tools.strata.checkers.solidity_security import (
            check_solidity_integer_overflow,
        )
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
        from whitemagic.tools.strata.checkers.solidity import (
            FileIndex,
            Finding,
            FindingSeverity,
        )
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


class TestFixContestIntegration:
    """G10: Test FixGenerator → ContestPipeline integration."""

    def test_finding_default_fix_status_none(self):
        from whitemagic.tools.security.contest_pipeline import ContestFinding
        f = ContestFinding("T", "high", "xss", "a.js", 1, "d", "i", "p", "m")
        assert f.fix_status == "none"

    def test_link_fix_updates_status(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        from whitemagic.tools.security.fix_generator import FixSuggestion
        pipeline = ContestPipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        finding = pipeline.add_finding("T", "high", "xss", "a.js", 1, "d", "i", "p", "m")
        assert finding is not None
        fix = FixSuggestion("a.js", 1, "old", "new", "xss", "desc")
        ok = pipeline.link_fix(finding.finding_id, fix)
        assert ok
        assert finding.fix_status == "applied"

    def test_link_fix_unknown_finding(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        from whitemagic.tools.security.fix_generator import FixSuggestion
        pipeline = ContestPipeline()
        fix = FixSuggestion("a.js", 1, "old", "new", "xss", "desc")
        assert pipeline.link_fix("WM-9999", fix) is False

    def test_link_pr_updates_status(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        pipeline = ContestPipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        finding = pipeline.add_finding("T", "high", "xss", "a.js", 1, "d", "i", "p", "m")
        assert finding is not None
        ok = pipeline.link_pr(finding.finding_id, "https://github.com/repo/pull/1")
        assert ok
        assert finding.fix_status == "pr_created"

    def test_link_pr_unknown_finding(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        pipeline = ContestPipeline()
        assert pipeline.link_pr("WM-9999", "https://github.com/repo/pull/1") is False

    def test_fix_coverage_report_empty(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        pipeline = ContestPipeline()
        report = pipeline.fix_coverage_report()
        assert report["total_findings"] == 0
        assert report["coverage_pct"] == 0.0

    def test_fix_coverage_report_mixed(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        from whitemagic.tools.security.fix_generator import FixSuggestion
        pipeline = ContestPipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        f1 = pipeline.add_finding("T1", "high", "xss", "a.js", 1, "d", "i", "p", "m")
        f2 = pipeline.add_finding("T2", "medium", "sqli", "b.py", 2, "d", "i", "p", "m")
        f3 = pipeline.add_finding("T3", "low", "xss", "c.js", 3, "d", "i", "p", "m")
        fix = FixSuggestion("a.js", 1, "old", "new", "xss", "desc")
        pipeline.link_fix(f1.finding_id, fix)
        pipeline.link_pr(f2.finding_id, "https://github.com/repo/pull/1")
        report = pipeline.fix_coverage_report()
        assert report["total_findings"] == 3
        assert report["fixed_or_in_progress"] == 2
        assert report["unfixed"] == 1
        assert report["by_fix_status"]["applied"] == 1
        assert report["by_fix_status"]["pr_created"] == 1
        assert report["by_fix_status"]["none"] == 1
        assert len(report["unfixed_findings"]) == 1
        assert report["unfixed_findings"][0]["finding_id"] == f3.finding_id
        assert round(report["coverage_pct"]) == 67

    def test_status_includes_fix_coverage(self):
        from whitemagic.tools.security.contest_pipeline import ContestPipeline
        pipeline = ContestPipeline()
        status = pipeline.status()
        assert "fix_coverage" in status
        assert status["fix_coverage"]["total_findings"] == 0

    def test_handle_fix_apply_links_to_contest(self, tmp_path):
        from whitemagic.tools.handlers.security_tools import handle_fix_apply
        from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
        pipeline = get_contest_pipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        finding = pipeline.add_finding("T", "high", "xss", "a.js", 1, "d", "i", "p", "m")
        f = tmp_path / "a.js"
        f.write_text("old\nnew\n")
        result = handle_fix_apply(
            file=str(f),
            line=1,
            original="old",
            fixed="new",
            fix_type="xss",
            description="desc",
            dry_run=True,
            finding_id=finding.finding_id,
        )
        assert result["success"]
        assert finding.fix_status == "applied"

    def test_handle_pr_create_links_to_contest(self):
        from whitemagic.tools.handlers.security_tools import handle_pr_create
        from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
        pipeline = get_contest_pipeline()
        pipeline._findings = []
        pipeline._seen_hashes = set()
        finding = pipeline.add_finding("T", "high", "xss", "a.js", 1, "d", "i", "p", "m")
        with patch("subprocess.run") as mock_run:
            push_ok = MagicMock()
            push_ok.returncode = 0
            push_ok.stderr = ""
            pr_ok = MagicMock()
            pr_ok.returncode = 0
            pr_ok.stdout = "https://github.com/repo/pull/1"
            mock_run.side_effect = [push_ok, push_ok, push_ok, push_ok, pr_ok]
            result = handle_pr_create(
                repo_dir="/tmp",
                branch_name="fix",
                title="Fix",
                body="",
                finding_id=finding.finding_id,
            )
        assert result["success"]
        assert finding.fix_status == "pr_created"


class TestReportScraperPoliteness:
    """G11: Test rate limiting, robots.txt, caching, and batch scraping."""

    def test_rate_limiter_basic(self):
        from whitemagic.tools.security.report_scraper import RateLimiter
        rl = RateLimiter(interval=0.05)
        rl.wait()
        rl.wait()
        assert rl._last_request > 0

    def test_rate_limiter_per_domain(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01)
        rl1 = scraper._get_rate_limiter("code4rena.com")
        rl2 = scraper._get_rate_limiter("code4rena.com")
        assert rl1 is rl2
        rl3 = scraper._get_rate_limiter("sherlock.xyz")
        assert rl3 is not rl1

    def test_cache_hit_skips_fetch(self, tmp_path):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(cache_ttl=3600)
        url = "https://code4rena.com/reports/test-contest"
        scraper._set_cached(url, "## [H] Test Finding\n\nDescription here")
        report = scraper.scrape_url(url, "code4rena")
        assert report is not None
        assert report.contest_name is not None
        assert len(report.findings) >= 1

    def test_cache_miss_fetches(self, tmp_path):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01, cache_ttl=3600)
        url = "https://example.com/reports/test"
        cache_file = scraper._cache_path(url)
        if cache_file.exists():
            cache_file.unlink()
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "## [H] Cached Finding\n\nDesc"
            mock_get.return_value = mock_resp
            report = scraper.scrape_url(url, "code4rena")
        assert report is not None
        assert len(report.findings) >= 1
        assert scraper._total_scraped == 1

    def test_robots_txt_disallows(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01)
        with patch("requests.get") as mock_get:
            robots_resp = MagicMock()
            robots_resp.status_code = 200
            robots_resp.text = "User-agent: *\nDisallow: /private/"
            mock_get.return_value = robots_resp
            allowed = scraper._check_robots("https://code4rena.com/private/secret")
        assert allowed is False

    def test_robots_txt_allows(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01)
        with patch("requests.get") as mock_get:
            robots_resp = MagicMock()
            robots_resp.status_code = 200
            robots_resp.text = "User-agent: *\nDisallow: /private/"
            mock_get.return_value = robots_resp
            allowed = scraper._check_robots("https://code4rena.com/reports/public")
        assert allowed is True

    def test_robots_txt_unavailable_allows(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01)
        with patch("requests.get") as mock_get:
            robots_resp = MagicMock()
            robots_resp.status_code = 404
            mock_get.return_value = robots_resp
            allowed = scraper._check_robots("https://code4rena.com/reports/test")
        assert allowed is True

    def test_robots_txt_cached(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01)
        with patch("requests.get") as mock_get:
            robots_resp = MagicMock()
            robots_resp.status_code = 200
            robots_resp.text = "User-agent: *\nDisallow: /private/"
            mock_get.return_value = robots_resp
            scraper._check_robots("https://code4rena.com/reports/public")
            call_count = mock_get.call_count
            scraper._check_robots("https://code4rena.com/reports/other")
            assert mock_get.call_count == call_count

    def test_backoff_on_429(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01, cache_ttl=3600)
        url = "https://example.com/reports/test-429"
        cache_file = scraper._cache_path(url)
        if cache_file.exists():
            cache_file.unlink()
        with patch("requests.get") as mock_get:
            resp_429 = MagicMock()
            resp_429.status_code = 429
            resp_200 = MagicMock()
            resp_200.status_code = 200
            resp_200.text = "## [H] Backoff Finding\n\nDesc"
            mock_get.side_effect = [resp_429, resp_200]
            with patch("time.sleep"):
                report = scraper.scrape_url(url, "code4rena")
        assert report is not None
        assert len(report.findings) >= 1

    def test_scrape_batch(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=0.01, cache_ttl=3600)
        urls = ["https://a.com/r1", "https://a.com/r2"]
        for u in urls:
            scraper._set_cached(u, "## [H] Batch Finding\n\nDesc")
        results = scraper.scrape_batch(urls, "code4rena")
        assert len(results) == 2

    def test_status_includes_rate_info(self):
        from whitemagic.tools.security.report_scraper import ReportScraper
        scraper = ReportScraper(rate_interval=3.0, cache_ttl=7200)
        status = scraper.status()
        assert status["rate_interval"] == 3.0
        assert status["cache_ttl"] == 7200


class TestExpandedSecretsScanning:
    """G12: Test expanded STRATA secrets scanning checker."""

    def _run_checker(self, tmp_path, filename, content):
        from whitemagic.tools.strata.checkers.python_security import (
            check_hardcoded_secrets,
        )
        from whitemagic.tools.strata.checkers.solidity import FileIndex
        f = tmp_path / filename
        f.write_text(content)
        fi = FileIndex(tmp_path)
        findings = []
        check_hardcoded_secrets(tmp_path, fi, findings)
        return findings

    def test_rename_alias_exists(self):
        from whitemagic.tools.strata.checkers.python_security import (
            check_hardcoded_secrets,
            check_python_secrets,
        )
        assert check_hardcoded_secrets is check_python_secrets

    def test_stripe_key_detected(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'STRIPE_KEY = "sk_live_' + 'abcdefghijklmnopqrstuvwxyz0123456789"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_twilio_key_detected(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'TWILIO = "SK' + '1234567890abcdef1234567890abcdef"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_sendgrid_key_detected(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'SG_KEY = "SG.abcdefghijklmnopqrstuv.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcde"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_bearer_token_detected(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'AUTH = "Bearer abcdefghijklmnopqrstuvwxyz1234567890"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_cloudflare_key_detected(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'CF_KEY = "v1.0-abcdefghijklmnopqrstuvwxyz1234567890ABCDE"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_unquoted_secret_in_env_file(self, tmp_path):
        findings = self._run_checker(tmp_path, "config.env", "API_KEY=abcdefghijklmnopqrstuvwxyz1234567890")
        assert any(f.category == "hardcoded_secret" and "unquoted" in f.message.lower() for f in findings)

    def test_unquoted_secret_in_shell_file(self, tmp_path):
        findings = self._run_checker(tmp_path, "setup.sh", "export SECRET_KEY=abcdefghijklmnopqrstuvwxyz1234567890")
        assert any(f.category == "hardcoded_secret" and "unquoted" in f.message.lower() for f in findings)

    def test_unquoted_secret_skips_examples(self, tmp_path):
        findings = self._run_checker(tmp_path, "config.env", "API_KEY=your_api_key_here_replace_me")
        assert not any("unquoted" in f.message.lower() for f in findings)

    def test_properties_file_scanned(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.properties", 'api.key = "abcdefghijklmnopqrstuvwxyz1234567890"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_xml_file_scanned(self, tmp_path):
        findings = self._run_checker(tmp_path, "config.xml", '<value>sk_live_' + 'abcdefghijklmnopqrstuvwxyz0123456789</value>')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_bash_file_scanned(self, tmp_path):
        findings = self._run_checker(tmp_path, "deploy.bash", 'TOKEN="abcdefghijklmnopqrstuvwxyz1234567890"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_zsh_file_scanned(self, tmp_path):
        findings = self._run_checker(tmp_path, "env.zsh", 'SECRET="abcdefghijklmnopqrstuvwxyz1234567890"')
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_getenv_not_flagged(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'key = os.getenv("API_KEY")')
        assert not any(f.category == "hardcoded_secret" for f in findings)

    def test_example_not_flagged(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'api_key = "example_placeholder_key_for_testing"')
        assert not any(f.category == "hardcoded_secret" for f in findings)

    def test_category_renamed(self, tmp_path):
        findings = self._run_checker(tmp_path, "app.py", 'sk = "sk_live_' + 'abcdefghijklmnopqrstuvwxyz0123456789"')
        assert all(f.category == "hardcoded_secret" for f in findings)
        assert not any(f.category == "py_hardcoded_secret" for f in findings)
