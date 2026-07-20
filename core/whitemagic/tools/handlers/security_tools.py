"""MCP handler for security tools — foundry, abi, vuln knowledge, contest, oss."""
import logging
from typing import Any

from whitemagic.tools.security.abi_decoder import (
    decode_calldata,
    parse_abi,
    summarize_abi,
)
from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
from whitemagic.tools.security.foundry_bridge import get_foundry_bridge
from whitemagic.tools.security.oss_scanner import get_oss_scanner
from whitemagic.tools.security.vuln_knowledge import get_vuln_knowledge_base

logger = logging.getLogger(__name__)


# ── Engagement token defense-in-depth ──────────────────────────────────────

_OFFENSIVE_HANDLER_TOOLS: frozenset[str] = frozenset({
    "foundry_build", "foundry_test", "foundry_test_json",
    "http_probe_get", "http_probe_post", "http_probe_xss",
    "http_probe_sqli", "http_probe_idor", "http_probe_ssrf",
    "api_state_machine",
    "echidna_fuzz", "echidna_status",
    "formal_verify", "formal_verify_status",
    "poc_generate", "poc_verify",
    "nmap_scan", "sqlmap_scan", "hydra_brute",
    "nikto_scan", "ffuf_fuzz", "nuclei_scan",
    "redteam_autonomous", "agent_redteam_run",
    "attack_cell_execute",
})


def _check_offensive_token(tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any] | None:
    """Defense-in-depth: validate engagement token for offensive tools.

    The middleware (mw_engagement_token) is the primary gate under violet profile.
    This handler-level check provides a second layer: if a token_id is supplied,
    validate it; if violet profile is active and no token is supplied, block.
    Returns None to proceed, or an error dict to short-circuit.
    """
    if tool_name not in _OFFENSIVE_HANDLER_TOOLS:
        return None
    try:
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager

        token_id = kwargs.get("_engagement_token_id", "")
        engine = get_rules_engine()
        is_violet = engine.get_profile() == "violet"

        if not token_id and not is_violet:
            return None  # non-violet, no token needed

        if not token_id and is_violet:
            return {
                "status": "error",
                "error_code": "engagement_token_required",
                "message": f"Tool '{tool_name}' requires a valid engagement token under violet profile.",
            }

        target = ""
        for key in ("target", "host", "ip", "url", "domain", "endpoint", "rpc_url", "base_url", "contract_address", "address"):
            val = kwargs.get(key)
            if isinstance(val, str) and val:
                target = val
                break

        result = get_token_manager().validate(token_id=token_id, tool=tool_name, target=target)
        if not result.get("valid", False):
            return {
                "status": "error",
                "error_code": "engagement_token_invalid",
                "message": f"Engagement token validation failed: {result.get('reason', 'unknown')}",
                "token_id": token_id,
            }
    except ImportError:
        logger.debug("Optional dependency unavailable: ImportError")
    except Exception as e:  # noqa: BLE001
        logger.debug("Handler token check failed for %s: %s", tool_name, e)
    return None


def _execute_in_shelter(
    shelter_id: str,
    tool_name: str,
    kwargs: dict[str, Any],
) -> dict[str, Any] | None:
    """Execute an offensive tool call inside a shelter sandbox.

    Returns None if shelter_id is empty or the shelter is not found (caller
    proceeds normally).  Returns a result dict if the shelter execution
    completes (success or error).
    """
    if not shelter_id:
        return None
    try:
        from whitemagic.shelter.manager import get_shelter_manager

        mgr = get_shelter_manager()
        shelter = mgr._shelters.get(shelter_id)
        if shelter is None:
            return None  # shelter not found, proceed normally

        # Build a Python payload that calls the handler without shelter_id
        # to avoid recursion, and return the result as JSON.
        import json as _json

        clean_kwargs = {k: v for k, v in kwargs.items() if k != "_shelter_id"}
        payload = {
            "type": "python",
            "code": (
                "import json; "
                f"from whitemagic.tools.handlers.security_tools import "
                f"_dispatch_offensive_for_shelter; "
                f"result = _dispatch_offensive_for_shelter({ _json.dumps(tool_name)!r}, "
                f"{ _json.dumps(clean_kwargs)!r}); "
                "print(json.dumps(result))"
            ),
        }
        result = mgr.execute(shelter_id, payload)
        if result.get("status") == "ok":
            try:
                parsed = _json.loads(result.get("output", "{}"))
                return parsed
            except (_json.JSONDecodeError, ValueError):
                return result
        return result
    except ImportError:
        return None
    except Exception as e:  # noqa: BLE001
        logger.debug("Shelter execution failed for %s: %s", tool_name, e)
        return None


def _dispatch_offensive_for_shelter(tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Internal: dispatch an offensive tool call from within a shelter."""
    # Re-invoke the handler function by name, stripping shelter_id to avoid recursion
    import whitemagic.tools.handlers.security_tools as _mod

    handler_func = getattr(_mod, f"handle_{tool_name}", None)
    if handler_func is None:
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}
    # Remove shelter_id to prevent recursion
    kwargs.pop("_shelter_id", None)
    kwargs.pop("shelter_id", None)
    return handler_func(**kwargs)


def handle_foundry_build(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("foundry_build", kwargs)
    if _err:
        return _err
    _shelter = kwargs.get("_shelter_id", "") or kwargs.get("shelter_id", "")
    if _shelter:
        _sresult = _execute_in_shelter(_shelter, "foundry_build", kwargs)
        if _sresult is not None:
            return _sresult
    bridge = get_foundry_bridge(kwargs.get("project_dir"))
    result = bridge.build(silent=kwargs.get("silent", True))
    return {"success": result.success, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:], "returncode": result.returncode}


def handle_foundry_test(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("foundry_test", kwargs)
    if _err:
        return _err
    _shelter = kwargs.get("_shelter_id", "") or kwargs.get("shelter_id", "")
    if _shelter:
        _sresult = _execute_in_shelter(_shelter, "foundry_test", kwargs)
        if _sresult is not None:
            return _sresult
    bridge = get_foundry_bridge(kwargs.get("project_dir"))
    result = bridge.test(match=kwargs.get("match"), gas_report=kwargs.get("gas_report", False))
    return {"success": result.success, "stdout": result.stdout[-2000:], "stderr": result.stderr[-500:], "returncode": result.returncode}


def handle_foundry_test_json(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("foundry_test_json", kwargs)
    if _err:
        return _err
    bridge = get_foundry_bridge(kwargs.get("project_dir"))
    result = bridge.test_json(match=kwargs.get("match"))
    return {"success": result.success, "data": result.data, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}


def handle_abi_parse(**kwargs: Any) -> dict[str, Any]:
    sigs = parse_abi(kwargs.get("abi_json", ""))
    return {"signatures": [s.signature for s in sigs], "functions": [{"name": s.name, "inputs": s.inputs, "state_mutability": s.state_mutability} for s in sigs]}


def handle_abi_summarize(**kwargs: Any) -> dict[str, Any]:
    return summarize_abi(kwargs.get("abi_json", ""))


def handle_abi_decode_calldata(**kwargs: Any) -> dict[str, Any]:
    decoded = decode_calldata(kwargs.get("calldata", ""), kwargs.get("abi_json"))
    return {"selector": decoded.selector, "function_name": decoded.function_name, "parameters": decoded.parameters}


def handle_vuln_search(**kwargs: Any) -> dict[str, Any]:
    kb = get_vuln_knowledge_base()
    query = kwargs.get("query", "")
    if query:
        results = kb.search_by_keyword(query)
    else:
        results = list(kb._patterns.values())
    return {"results": [{"pattern_id": p.pattern_id, "name": p.name, "category": p.category, "severity": p.severity, "description": p.description, "mitigation": p.mitigation} for p in results], "count": len(results)}


def handle_vuln_status(**kwargs: Any) -> dict[str, Any]:
    return get_vuln_knowledge_base().status()


def handle_vuln_ingest_report(**kwargs: Any) -> dict[str, Any]:
    kb = get_vuln_knowledge_base()
    count = kb.ingest_audit_report(kwargs.get("report_text", ""), kwargs.get("source", "audit_report"))
    return {"patterns_extracted": count, "total_patterns": len(kb._patterns)}


def handle_contest_add_finding(**kwargs: Any) -> dict[str, Any]:
    pipeline = get_contest_pipeline()
    finding = pipeline.add_finding(
        title=kwargs.get("title", ""),
        severity=kwargs.get("severity", "low"),
        category=kwargs.get("category", ""),
        file=kwargs.get("file", ""),
        line=kwargs.get("line"),
        description=kwargs.get("description", ""),
        impact=kwargs.get("impact", ""),
        proof_of_concept=kwargs.get("proof_of_concept", ""),
        mitigation=kwargs.get("mitigation", ""),
        mitre_ttp_ids=kwargs.get("mitre_ttp_ids"),
    )
    if finding:
        return {"status": "added", "finding_id": finding.finding_id, "dedup_hash": finding.dedup_hash, "mitre_ttp_ids": finding.mitre_ttp_ids}
    return {"status": "duplicate", "finding_id": None}


def handle_contest_format(**kwargs: Any) -> dict[str, Any]:
    pipeline = get_contest_pipeline()
    platform = kwargs.get("platform", "code4rena")
    report = pipeline.format_for_platform(platform)
    return {"report": report, "platform": platform, "finding_count": len(pipeline.findings)}


def handle_contest_status(**kwargs: Any) -> dict[str, Any]:
    return get_contest_pipeline().status()


def handle_oss_scan_repo(**kwargs: Any) -> dict[str, Any]:
    scanner = get_oss_scanner()
    bounties = scanner.scan_repo(kwargs.get("repo", ""))
    return {"bounties": [{"repo": b.repo, "issue": b.issue_number, "title": b.title, "url": b.url, "amount": b.bounty_amount, "platform": b.bounty_platform} for b in bounties], "count": len(bounties)}


def handle_oss_scan_org(**kwargs: Any) -> dict[str, Any]:
    scanner = get_oss_scanner()
    bounties = scanner.scan_org(kwargs.get("org", ""))
    return {"bounties": [{"repo": b.repo, "issue": b.issue_number, "title": b.title, "url": b.url, "amount": b.bounty_amount, "platform": b.bounty_platform} for b in bounties], "count": len(bounties)}


def handle_security_status(**kwargs: Any) -> dict[str, Any]:
    return {
        "foundry": get_foundry_bridge().status(),
        "vuln_kb": get_vuln_knowledge_base().status(),
        "contest": get_contest_pipeline().status(),
        "oss_scanner": get_oss_scanner().status(),
    }


# ── PoC Pipeline handlers ──
def handle_poc_generate(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("poc_generate", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.poc_pipeline import generate_poc
    try:
        code = generate_poc(kwargs.get("template_name", ""), kwargs.get("variables", {}), tier=kwargs.get("tier"))
        return {"success": True, "code": code}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


def handle_poc_verify(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("poc_verify", kwargs)
    if _err:
        return _err
    _shelter = kwargs.get("_shelter_id", "") or kwargs.get("shelter_id", "")
    if _shelter:
        _sresult = _execute_in_shelter(_shelter, "poc_verify", kwargs)
        if _sresult is not None:
            return _sresult
    from whitemagic.tools.security.poc_pipeline import verify_poc
    result = verify_poc(
        kwargs.get("template_name", ""),
        kwargs.get("variables", {}),
        kwargs.get("project_dir", "."),
        tier=kwargs.get("tier", "huben"),
        target=kwargs.get("target", ""),
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


def handle_contest_prepare(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.poc_pipeline import contest_prepare
    return contest_prepare(
        kwargs.get("repo_url", ""),
        kwargs.get("project_dir", "."),
        checkers=kwargs.get("checkers"),
    )


# ── HTTP Probe handlers ──
def handle_http_probe_get(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("http_probe_get", kwargs)
    if _err:
        return _err
    _shelter = kwargs.get("_shelter_id", "") or kwargs.get("shelter_id", "")
    if _shelter:
        _sresult = _execute_in_shelter(_shelter, "http_probe_get", kwargs)
        if _sresult is not None:
            return _sresult
    from whitemagic.tools.security.http_probe import get_http_probe
    r = get_http_probe().get(kwargs.get("url", ""), kwargs.get("params"), kwargs.get("headers"))
    return {"status_code": r.status_code, "body": r.body[:2000], "elapsed_ms": r.elapsed_ms, "headers": dict(list(r.headers.items())[:10])}


def handle_http_probe_post(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("http_probe_post", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.http_probe import get_http_probe
    r = get_http_probe().post(kwargs.get("url", ""), json_data=kwargs.get("json"), data=kwargs.get("data"), headers=kwargs.get("headers"))
    return {"status_code": r.status_code, "body": r.body[:2000], "elapsed_ms": r.elapsed_ms}


def handle_http_probe_xss(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("http_probe_xss", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_xss(kwargs.get("url", ""), kwargs.get("param", ""))


def handle_http_probe_sqli(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("http_probe_sqli", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_sqli(kwargs.get("url", ""), kwargs.get("param", ""))


def handle_http_probe_idor(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("http_probe_idor", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_idor(kwargs.get("base_url", ""), kwargs.get("resource_path", ""), kwargs.get("max_id", 20))


def handle_http_probe_ssrf(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("http_probe_ssrf", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().probe_ssrf(kwargs.get("url", ""), kwargs.get("param", ""))


def handle_api_state_machine(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("api_state_machine", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.http_probe import get_http_probe
    return get_http_probe().api_state_machine(kwargs.get("base_url", ""), kwargs.get("sequences", []))


# ── Echidna handlers ──
def handle_echidna_fuzz(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("echidna_fuzz", kwargs)
    if _err:
        return _err
    _shelter = kwargs.get("_shelter_id", "") or kwargs.get("shelter_id", "")
    if _shelter:
        _sresult = _execute_in_shelter(_shelter, "echidna_fuzz", kwargs)
        if _sresult is not None:
            return _sresult
    from whitemagic.tools.security.echidna_bridge import EchidnaBridge
    bridge = EchidnaBridge()
    result = bridge.fuzz(
        kwargs.get("contract_file", ""),
        kwargs.get("contract_name", ""),
        config_file=kwargs.get("config_file"),
        workdir=kwargs.get("workdir"),
    )
    return {
        "success": result.success,
        "tests_passed": result.tests_passed,
        "tests_failed": result.tests_failed,
        "failures": result.failures,
        "stdout": result.stdout[-1000:],
        "elapsed_s": result.elapsed_s,
    }


def handle_echidna_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.echidna_bridge import EchidnaBridge
    return EchidnaBridge().status()


# ── Fix Generator handlers ──
def handle_fix_generate(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import generate_fixes_from_findings
    fixes = generate_fixes_from_findings(kwargs.get("findings", []), kwargs.get("project_path", "."))
    return {"fixes": [{"file": f.file, "line": f.line, "original": f.original, "fixed": f.fixed, "description": f.description} for f in fixes], "count": len(fixes)}


def handle_fix_apply(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import FixSuggestion, apply_fix
    fix = FixSuggestion(
        file=kwargs.get("file", ""),
        line=kwargs.get("line", 0),
        original=kwargs.get("original", ""),
        fixed=kwargs.get("fixed", ""),
        fix_type=kwargs.get("fix_type", ""),
        description=kwargs.get("description", ""),
    )
    result = apply_fix(fix, dry_run=kwargs.get("dry_run", True))
    finding_id = kwargs.get("finding_id", "")
    if finding_id and result.get("success"):
        get_contest_pipeline().link_fix(finding_id, fix)
    return result


def handle_pr_create(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import create_pr
    result = create_pr(
        kwargs.get("repo_dir", ""),
        kwargs.get("branch_name", "security-fix"),
        kwargs.get("title", "Security fix"),
        kwargs.get("body", ""),
        labels=kwargs.get("labels"),
        bounty_ref=kwargs.get("bounty_ref"),
    )
    finding_id = kwargs.get("finding_id", "")
    if finding_id and result.get("success") and result.get("pr_url"):
        get_contest_pipeline().link_pr(finding_id, result["pr_url"])
    return result


def handle_bounty_track(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.fix_generator import track_bounty_earnings
    return track_bounty_earnings(
        kwargs.get("source", ""),
        kwargs.get("amount", ""),
        kwargs.get("issue_url", ""),
        status=kwargs.get("status", "pending"),
    )


# ── Report Scraper handlers ──
def handle_report_scrape(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.report_scraper import ReportScraper
    scraper = ReportScraper()
    report = scraper.scrape_url(kwargs.get("url", ""), kwargs.get("platform", "code4rena"))
    if report:
        return {"success": True, "platform": report.platform, "contest_name": report.contest_name, "findings": report.findings, "finding_count": len(report.findings)}
    return {"success": False, "error": "Scrape failed"}


def handle_report_ingest(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.report_scraper import ReportScraper
    scraper = ReportScraper()
    count = scraper.scrape_to_knowledge_base(kwargs.get("url", ""), kwargs.get("platform", "code4rena"))
    return {"success": count > 0, "patterns_ingested": count}


# ── Phase 7: Advanced Tools ──
def handle_vuln_graph_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.vuln_graph import get_vuln_graph
    return get_vuln_graph().status()


def handle_vuln_graph_chains(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.vuln_graph import get_vuln_graph
    return get_vuln_graph().find_exploit_chains(kwargs.get("start_vuln", ""), max_depth=kwargs.get("max_depth", 5))


def handle_vuln_graph_cross_chain(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.vuln_graph import get_vuln_graph
    return get_vuln_graph().cross_chain_analysis(kwargs.get("chains", []))


def handle_formal_verify(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("formal_verify", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.formal_verifier import FormalVerifier
    fv = FormalVerifier()
    results = fv.verify_halmos(kwargs.get("project_dir", "."), match=kwargs.get("match", ".*"))
    return {"results": [{"property": r.property_name, "verified": r.verified, "counterexample": r.counterexample, "elapsed_s": r.elapsed_s} for r in results]}


def handle_formal_verify_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.formal_verifier import FormalVerifier
    return FormalVerifier().status()


def handle_swarm_analyze(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.multi_agent import get_security_swarm
    return get_security_swarm().run_analysis(kwargs.get("project_path", "."))


def handle_swarm_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.multi_agent import get_security_swarm
    return get_security_swarm().status()


def handle_predictive_score(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.predictive_scoring import get_predictive_scorer
    result = get_predictive_scorer().score_contract(
        kwargs.get("contract_file", ""),
        kwargs.get("contract_name", ""),
        kwargs.get("content", ""),
    )
    return {
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "factors": result.factors,
        "predicted_vulnerabilities": result.predicted_vulnerabilities,
    }


def handle_predictive_batch(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.predictive_scoring import get_predictive_scorer
    results = get_predictive_scorer().batch_score(kwargs.get("contracts", []))
    return {"results": [{"contract": r.contract_name, "risk_score": r.risk_score, "predicted": r.predicted_vulnerabilities} for r in results]}


def handle_audit_report(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.audit_report import get_audit_report_generator
    report = get_audit_report_generator().generate(
        kwargs.get("project_name", ""),
        kwargs.get("findings", []),
        format_type=kwargs.get("format", "standard"),
        coverage=kwargs.get("coverage"),
    )
    return {"title": report.title, "date": report.date, "executive_summary": report.executive_summary, "markdown": report.raw_markdown}


def handle_monitor_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.monitor import get_security_monitor
    return get_security_monitor().status()


def handle_monitor_alerts(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.monitor import get_security_monitor
    alerts = get_security_monitor().get_alerts(severity=kwargs.get("severity"), limit=kwargs.get("limit", 100))
    return {"alerts": [{"id": a.alert_id, "severity": a.severity, "source": a.source, "message": a.message, "timestamp": a.timestamp} for a in alerts]}


def handle_monitor_contract(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.monitor import get_security_monitor
    return get_security_monitor().monitor_contract(kwargs.get("address", ""), kwargs.get("chain_id", 1))


# ── Slither Integration ──
def handle_slither_scan(**kwargs: Any) -> dict[str, Any]:
    """Run Slither static analysis on a Solidity project directly."""
    import json as _json
    import shutil as _shutil
    import subprocess as _sp
    project_dir = kwargs.get("project_dir", ".")
    slither_bin = _shutil.which("slither")
    if not slither_bin:
        return {"status": "error", "error": "Slither not installed", "findings": []}
    cmd = [slither_bin, project_dir, "--json", "-"]
    try:
        result = _sp.run(cmd, capture_output=True, text=True, timeout=120, cwd=project_dir)
    except _sp.TimeoutExpired:
        return {"status": "error", "error": "Slither timed out", "findings": []}
    except Exception as e:  # noqa: BLE001
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


def handle_slither_status(**kwargs: Any) -> dict[str, Any]:
    """Check Slither availability and version."""
    import shutil as _shutil
    import subprocess as _sp
    slither_bin = _shutil.which("slither")
    if not slither_bin:
        return {"available": False, "path": None, "version": None}
    try:
        result = _sp.run([slither_bin, "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() or result.stderr.strip()
    except Exception:  # noqa: BLE001
        version = "unknown"
    return {"available": True, "path": slither_bin, "version": version}


# ── Dynamic Testing Tool handlers (Gap 2) ──────────────────────────────────

def handle_nmap_scan(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("nmap_scan", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.dynamic_testers import run_nmap
    return run_nmap(
        target=kwargs.get("target", ""),
        scan_type=kwargs.get("scan_type", "service"),
        ports=kwargs.get("ports", ""),
        timeout=kwargs.get("timeout", 120),
    )


def handle_sqlmap_scan(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("sqlmap_scan", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.dynamic_testers import run_sqlmap
    return run_sqlmap(
        url=kwargs.get("url", ""),
        method=kwargs.get("method", "GET"),
        data=kwargs.get("data", ""),
        param=kwargs.get("param", ""),
        cookie=kwargs.get("cookie", ""),
        level=kwargs.get("level", 1),
        risk=kwargs.get("risk", 1),
        timeout=kwargs.get("timeout", 180),
    )


def handle_hydra_brute(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("hydra_brute", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.dynamic_testers import run_hydra
    return run_hydra(
        target=kwargs.get("target", ""),
        service=kwargs.get("service", "ssh"),
        userlist=kwargs.get("userlist", ""),
        passlist=kwargs.get("passlist", ""),
        user=kwargs.get("user", ""),
        timeout=kwargs.get("timeout", 120),
    )


def handle_nikto_scan(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("nikto_scan", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.dynamic_testers import run_nikto
    return run_nikto(
        target=kwargs.get("target", ""),
        port=kwargs.get("port", 80),
        timeout=kwargs.get("timeout", 120),
    )


def handle_ffuf_fuzz(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("ffuf_fuzz", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.dynamic_testers import run_ffuf
    return run_ffuf(
        url=kwargs.get("url", ""),
        wordlist=kwargs.get("wordlist", ""),
        mode=kwargs.get("mode", "dir"),
        timeout=kwargs.get("timeout", 120),
    )


def handle_nuclei_scan(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("nuclei_scan", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.dynamic_testers import run_nuclei
    return run_nuclei(
        target=kwargs.get("target", ""),
        templates=kwargs.get("templates", ""),
        severity=kwargs.get("severity", ""),
        timeout=kwargs.get("timeout", 120),
    )


# ── Decepticon / Autonomous Red-Teaming handlers (Gap 1) ───────────────────

def handle_redteam_autonomous(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("redteam_autonomous", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.decepticon_bridge import run_autonomous_redteam
    return run_autonomous_redteam(
        target=kwargs.get("target", ""),
        scope=kwargs.get("scope", "recon,scan,exploit,report"),
        engagement_token_id=kwargs.get("_engagement_token_id", ""),
        timeout=kwargs.get("timeout", 300),
    )


def handle_redteam_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.decepticon_bridge import decepticon_status
    return decepticon_status()


# ── AI Agent Red-Teaming handlers (Gap 6) ──────────────────────────────────

def handle_agent_redteam_run(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("agent_redteam_run", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.agent_redteam import run_agent_redteam_suite
    tests = kwargs.get("tests")
    if isinstance(tests, str):
        tests = [t.strip() for t in tests.split(",")]
    return run_agent_redteam_suite(
        agent_handler=None,  # No live agent in handler — returns payloads
        model_loader=None,
        tests=tests,
    )


def handle_agent_redteam_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.agent_redteam import agent_redteam_status
    return agent_redteam_status()


# ── Multi-Agent Attack Orchestration handlers (Gap 3) ──────────────────────

def handle_attack_cell_execute(**kwargs: Any) -> dict[str, Any]:
    _err = _check_offensive_token("attack_cell_execute", kwargs)
    if _err:
        return _err
    from whitemagic.tools.security.attack_cell import AttackCell
    cell = AttackCell(
        target=kwargs.get("target", ""),
        scope=kwargs.get("scope", "recon,web,exploit,report"),
        engagement_token_id=kwargs.get("_engagement_token_id", ""),
    )
    result = cell.execute()
    return result.summary()


def handle_attack_cell_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.security.attack_cell import attack_cell_status
    return attack_cell_status()
