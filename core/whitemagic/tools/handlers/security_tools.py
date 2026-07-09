"""MCP handler for security tools — foundry, abi, vuln knowledge, contest, oss."""
import logging
from typing import Any

from whitemagic.tools.security.foundry_bridge import get_foundry_bridge
from whitemagic.tools.security.abi_decoder import parse_abi, decode_calldata, summarize_abi, extract_events
from whitemagic.tools.security.vuln_knowledge import get_vuln_knowledge_base
from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
from whitemagic.tools.security.oss_scanner import get_oss_scanner

logger = logging.getLogger(__name__)


def handle_foundry_build(params: dict[str, Any]) -> dict[str, Any]:
    bridge = get_foundry_bridge(params.get("project_dir"))
    result = bridge.build(silent=params.get("silent", True))
    return {"success": result.success, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:], "returncode": result.returncode}


def handle_foundry_test(params: dict[str, Any]) -> dict[str, Any]:
    bridge = get_foundry_bridge(params.get("project_dir"))
    result = bridge.test(match=params.get("match"), gas_report=params.get("gas_report", False))
    return {"success": result.success, "stdout": result.stdout[-2000:], "stderr": result.stderr[-500:], "returncode": result.returncode}


def handle_foundry_test_json(params: dict[str, Any]) -> dict[str, Any]:
    bridge = get_foundry_bridge(params.get("project_dir"))
    result = bridge.test_json(match=params.get("match"))
    return {"success": result.success, "data": result.data, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}


def handle_abi_parse(params: dict[str, Any]) -> dict[str, Any]:
    sigs = parse_abi(params.get("abi_json", ""))
    return {"signatures": [s.signature for s in sigs], "functions": [{"name": s.name, "inputs": s.inputs, "state_mutability": s.state_mutability} for s in sigs]}


def handle_abi_summarize(params: dict[str, Any]) -> dict[str, Any]:
    return summarize_abi(params.get("abi_json", ""))


def handle_abi_decode_calldata(params: dict[str, Any]) -> dict[str, Any]:
    decoded = decode_calldata(params.get("calldata", ""), params.get("abi_json"))
    return {"selector": decoded.selector, "function_name": decoded.function_name, "parameters": decoded.parameters}


def handle_vuln_search(params: dict[str, Any]) -> dict[str, Any]:
    kb = get_vuln_knowledge_base()
    query = params.get("query", "")
    if query:
        results = kb.search_by_keyword(query)
    else:
        results = list(kb._patterns.values())
    return {"results": [{"pattern_id": p.pattern_id, "name": p.name, "category": p.category, "severity": p.severity, "description": p.description, "mitigation": p.mitigation} for p in results], "count": len(results)}


def handle_vuln_status(params: dict[str, Any]) -> dict[str, Any]:
    return get_vuln_knowledge_base().status()


def handle_vuln_ingest_report(params: dict[str, Any]) -> dict[str, Any]:
    kb = get_vuln_knowledge_base()
    count = kb.ingest_audit_report(params.get("report_text", ""), params.get("source", "audit_report"))
    return {"patterns_extracted": count, "total_patterns": len(kb._patterns)}


def handle_contest_add_finding(params: dict[str, Any]) -> dict[str, Any]:
    pipeline = get_contest_pipeline()
    finding = pipeline.add_finding(
        title=params.get("title", ""),
        severity=params.get("severity", "low"),
        category=params.get("category", ""),
        file=params.get("file", ""),
        line=params.get("line"),
        description=params.get("description", ""),
        impact=params.get("impact", ""),
        proof_of_concept=params.get("proof_of_concept", ""),
        mitigation=params.get("mitigation", ""),
    )
    if finding:
        return {"status": "added", "finding_id": finding.finding_id, "dedup_hash": finding.dedup_hash}
    return {"status": "duplicate", "finding_id": None}


def handle_contest_format(params: dict[str, Any]) -> dict[str, Any]:
    pipeline = get_contest_pipeline()
    platform = params.get("platform", "code4rena")
    report = pipeline.format_for_platform(platform)
    return {"report": report, "platform": platform, "finding_count": len(pipeline.findings)}


def handle_contest_status(params: dict[str, Any]) -> dict[str, Any]:
    return get_contest_pipeline().status()


def handle_oss_scan_repo(params: dict[str, Any]) -> dict[str, Any]:
    scanner = get_oss_scanner()
    bounties = scanner.scan_repo(params.get("repo", ""))
    return {"bounties": [{"repo": b.repo, "issue": b.issue_number, "title": b.title, "url": b.url, "amount": b.bounty_amount, "platform": b.bounty_platform} for b in bounties], "count": len(bounties)}


def handle_oss_scan_org(params: dict[str, Any]) -> dict[str, Any]:
    scanner = get_oss_scanner()
    bounties = scanner.scan_org(params.get("org", ""))
    return {"bounties": [{"repo": b.repo, "issue": b.issue_number, "title": b.title, "url": b.url, "amount": b.bounty_amount, "platform": b.bounty_platform} for b in bounties], "count": len(bounties)}


def handle_security_status(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "foundry": get_foundry_bridge().status(),
        "vuln_kb": get_vuln_knowledge_base().status(),
        "contest": get_contest_pipeline().status(),
        "oss_scanner": get_oss_scanner().status(),
    }


# ── PoC Pipeline handlers ──
def handle_poc_generate(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.poc_pipeline import generate_poc
    try:
        code = generate_poc(params.get("template_name", ""), params.get("variables", {}), tier=params.get("tier"))
        return {"success": True, "code": code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_poc_verify(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.poc_pipeline import verify_poc
    result = verify_poc(
        params.get("template_name", ""),
        params.get("variables", {}),
        params.get("project_dir", "."),
        tier=params.get("tier", "huben"),
        target=params.get("target", ""),
    )
    return {
        "success": result.success,
        "compiled": result.compiled,
        "test_passed": result.test_passed,
        "governance_approved": result.governance_approved,
        "output": result.output,
        "error": result.error,
        "elapsed_s": result.elapsed_s,
    }


def handle_contest_prepare(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.poc_pipeline import contest_prepare
    return contest_prepare(
        params.get("repo_url", ""),
        params.get("project_dir", "."),
        checkers=params.get("checkers"),
    )


# ── HTTP Probe handlers ──
def handle_http_probe_get(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    r = get_http_probe().get(params.get("url", ""), params.get("params"), params.get("headers"))
    return {"status_code": r.status_code, "body": r.body[:2000], "elapsed_ms": r.elapsed_ms, "headers": dict(list(r.headers.items())[:10])}


def handle_http_probe_post(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    r = get_http_probe().post(params.get("url", ""), json_data=params.get("json"), data=params.get("data"), headers=params.get("headers"))
    return {"status_code": r.status_code, "body": r.body[:2000], "elapsed_ms": r.elapsed_ms}


def handle_http_probe_xss(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_xss(params.get("url", ""), params.get("param", ""))


def handle_http_probe_sqli(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_sqli(params.get("url", ""), params.get("param", ""))


def handle_http_probe_idor(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_idor(params.get("base_url", ""), params.get("resource_path", ""), params.get("max_id", 20))


def handle_http_probe_ssrf(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_ssrf(params.get("url", ""), params.get("param", ""))


def handle_api_state_machine(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().api_state_machine(params.get("base_url", ""), params.get("sequences", []))


# ── Echidna handlers ──
def handle_echidna_fuzz(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.echidna_bridge import EchidnaBridge
    bridge = EchidnaBridge()
    result = bridge.fuzz(
        params.get("contract_file", ""),
        params.get("contract_name", ""),
        config_file=params.get("config_file"),
        workdir=params.get("workdir"),
    )
    return {
        "success": result.success,
        "tests_passed": result.tests_passed,
        "tests_failed": result.tests_failed,
        "failures": result.failures,
        "stdout": result.stdout[-1000:],
        "elapsed_s": result.elapsed_s,
    }


def handle_echidna_status(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.echidna_bridge import EchidnaBridge
    return EchidnaBridge().status()


# ── Fix Generator handlers ──
def handle_fix_generate(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import generate_fixes_from_findings
    fixes = generate_fixes_from_findings(params.get("findings", []), params.get("project_path", "."))
    return {"fixes": [{"file": f.file, "line": f.line, "original": f.original, "fixed": f.fixed, "description": f.description} for f in fixes], "count": len(fixes)}


def handle_fix_apply(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import FixSuggestion, apply_fix
    fix = FixSuggestion(
        file=params.get("file", ""),
        line=params.get("line", 0),
        original=params.get("original", ""),
        fixed=params.get("fixed", ""),
        fix_type=params.get("fix_type", ""),
        description=params.get("description", ""),
    )
    return apply_fix(fix, dry_run=params.get("dry_run", True))


def handle_pr_create(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import create_pr
    return create_pr(
        params.get("repo_dir", ""),
        params.get("branch_name", "security-fix"),
        params.get("title", "Security fix"),
        params.get("body", ""),
        labels=params.get("labels"),
        bounty_ref=params.get("bounty_ref"),
    )


def handle_bounty_track(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import track_bounty_earnings
    return track_bounty_earnings(
        params.get("source", ""),
        params.get("amount", ""),
        params.get("issue_url", ""),
        status=params.get("status", "pending"),
    )


# ── Report Scraper handlers ──
def handle_report_scrape(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.report_scraper import ReportScraper
    scraper = ReportScraper()
    report = scraper.scrape_url(params.get("url", ""), params.get("platform", "code4rena"))
    if report:
        return {"success": True, "platform": report.platform, "contest_name": report.contest_name, "findings": report.findings, "finding_count": len(report.findings)}
    return {"success": False, "error": "Scrape failed"}


def handle_report_ingest(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.report_scraper import ReportScraper
    scraper = ReportScraper()
    count = scraper.scrape_to_knowledge_base(params.get("url", ""), params.get("platform", "code4rena"))
    return {"success": count > 0, "patterns_ingested": count}


# ── Phase 7: Advanced Tools ──
def handle_vuln_graph_status(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.vuln_graph import get_vuln_graph
    return get_vuln_graph().status()


def handle_vuln_graph_chains(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.vuln_graph import get_vuln_graph
    return get_vuln_graph().find_exploit_chains(params.get("start_vuln", ""), max_depth=params.get("max_depth", 5))


def handle_vuln_graph_cross_chain(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.vuln_graph import get_vuln_graph
    return get_vuln_graph().cross_chain_analysis(params.get("chains", []))


def handle_formal_verify(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.formal_verifier import FormalVerifier
    fv = FormalVerifier()
    results = fv.verify_halmos(params.get("project_dir", "."), match=params.get("match", ".*"))
    return {"results": [{"property": r.property_name, "verified": r.verified, "counterexample": r.counterexample, "elapsed_s": r.elapsed_s} for r in results]}


def handle_formal_verify_status(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.formal_verifier import FormalVerifier
    return FormalVerifier().status()


def handle_swarm_analyze(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.multi_agent import get_security_swarm
    return get_security_swarm().run_analysis(params.get("project_path", "."))


def handle_swarm_status(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.multi_agent import get_security_swarm
    return get_security_swarm().status()


def handle_predictive_score(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.predictive_scoring import get_predictive_scorer
    result = get_predictive_scorer().score_contract(
        params.get("contract_file", ""),
        params.get("contract_name", ""),
        params.get("content", ""),
    )
    return {
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "factors": result.factors,
        "predicted_vulnerabilities": result.predicted_vulnerabilities,
    }


def handle_predictive_batch(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.predictive_scoring import get_predictive_scorer
    results = get_predictive_scorer().batch_score(params.get("contracts", []))
    return {"results": [{"contract": r.contract_name, "risk_score": r.risk_score, "predicted": r.predicted_vulnerabilities} for r in results]}


def handle_audit_report(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.audit_report import get_audit_report_generator
    report = get_audit_report_generator().generate(
        params.get("project_name", ""),
        params.get("findings", []),
        format_type=params.get("format", "standard"),
        coverage=params.get("coverage"),
    )
    return {"title": report.title, "date": report.date, "executive_summary": report.executive_summary, "markdown": report.raw_markdown}


def handle_monitor_status(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.monitor import get_security_monitor
    return get_security_monitor().status()


def handle_monitor_alerts(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.monitor import get_security_monitor
    alerts = get_security_monitor().get_alerts(severity=params.get("severity"), limit=params.get("limit", 100))
    return {"alerts": [{"id": a.alert_id, "severity": a.severity, "source": a.source, "message": a.message, "timestamp": a.timestamp} for a in alerts]}


def handle_monitor_contract(params: dict[str, Any]) -> dict[str, Any]:
    from whitemagic.tools.security.monitor import get_security_monitor
    return get_security_monitor().monitor_contract(params.get("address", ""), params.get("chain_id", 1))


# ── Slither Integration ──
def handle_slither_scan(params: dict[str, Any]) -> dict[str, Any]:
    """Run Slither static analysis on a Solidity project directly."""
    import json as _json
    import shutil as _shutil
    import subprocess as _sp
    project_dir = params.get("project_dir", ".")
    slither_bin = _shutil.which("slither")
    if not slither_bin:
        return {"status": "error", "error": "Slither not installed", "findings": []}
    cmd = [slither_bin, project_dir, "--json", "-"]
    try:
        result = _sp.run(cmd, capture_output=True, text=True, timeout=120, cwd=project_dir)
    except _sp.TimeoutExpired:
        return {"status": "error", "error": "Slither timed out", "findings": []}
    except Exception as e:
        return {"status": "error", "error": str(e), "findings": []}
    if result.returncode not in (0, 1):
        return {"status": "error", "error": f"Slither exited with code {result.returncode}", "findings": []}
    try:
        data = _json.loads(result.stdout)
    except (_json.JSONDecodeError, ValueError):
        return {"status": "error", "error": "Slither output not valid JSON", "findings": []}
    detectors = data.get("results", {}).get("detectors", [])
    findings = []
    for d in detectors:
        elements = d.get("elements", [])
        rel_file = "?"
        line_num = None
        if elements:
            src = elements[0].get("source_mapping", {})
            rel_file = src.get("filename_relative", "?")
            line_num = src.get("lines", [None])[0] if src.get("lines") else None
        findings.append({
            "severity": d.get("impact", "informational"),
            "category": f"slither_{d.get('check_id', 'unknown')}",
            "file": rel_file,
            "line": line_num,
            "message": d.get("description", d.get("check_id", "")),
            "confidence": d.get("confidence", "Medium"),
            "suggestion": d.get("markdown", d.get("description", ""))[:500],
        })
    severity_counts = {"high": 0, "medium": 0, "low": 0, "informational": 0, "optimization": 0}
    for f in findings:
        sev = f["severity"].lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    return {
        "status": "success",
        "findings": findings,
        "count": len(findings),
        "severity_counts": severity_counts,
    }


def handle_slither_status(params: dict[str, Any]) -> dict[str, Any]:
    """Check Slither availability and version."""
    import shutil as _shutil
    import subprocess as _sp
    slither_bin = _shutil.which("slither")
    if not slither_bin:
        return {"available": False, "path": None, "version": None}
    try:
        result = _sp.run([slither_bin, "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() or result.stderr.strip()
    except Exception:
        version = "unknown"
    return {"available": True, "path": slither_bin, "version": version}
