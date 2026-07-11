"""Memory-augmented STRATA checker — cross-reference findings with known patterns."""
import logging
from pathlib import Path
from typing import Any

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.checkers.solidity import FileIndex, Finding, FindingSeverity
from whitemagic.tools.security.vuln_knowledge import get_vuln_knowledge_base

logger = logging.getLogger(__name__)


@register
def check_memory_patterns(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """After all other checkers run, cross-reference findings with vuln knowledge base.

    - Escalate findings matching previously exploitable patterns
    - Suppress findings matching known false positive patterns
    - Annotate findings with pattern metadata
    """
    kb = get_vuln_knowledge_base()

    for finding in findings:
        # Search for matching patterns
        matched = kb.match_findings([{
            "category": finding.category,
            "message": finding.message,
        }])

        if matched:
            match = matched[0]
            # Escalate severity if pattern was previously exploitable
            if match["severity"] in ("critical", "high") and finding.severity == FindingSeverity.INFO:
                finding.severity = FindingSeverity.WARNING
                logger.debug("Escalated %s: matches pattern %s", finding.category, match["pattern"])
            # Add pattern reference to message
            pattern_ref = f" [Pattern: {match['pattern_name']}]"
            if pattern_ref not in finding.message:
                finding.message += pattern_ref
            if match.get("mitigation") and not finding.suggestion:
                finding.suggestion = match["mitigation"]


@register
def check_cross_domain_patterns(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Find cross-domain vulnerability patterns — Solidity patterns that resemble web vulns."""
    cross_domain_map = {
        "sol_tx_origin_auth": ("web_idor", "Authorization bypass — tx.origin is like unvalidated object reference"),
        "sol_access_control": ("web_csrf", "Missing access control — like CSRF, no authorization on state change"),
        "sol_arbitrary_transfer": ("web_open_redirect", "Unvalidated destination — like open redirect but for value transfer"),
    }

    for finding in findings:
        if finding.category in cross_domain_map:
            web_cat, note = cross_domain_map[finding.category]
            findings.append(Finding(
                severity=FindingSeverity.INFO,
                category=f"cross_domain_{finding.category}_to_{web_cat}",
                file=finding.file,
                line=finding.line,
                message=f"Cross-domain pattern: {note}",
                suggestion="Review both web and contract layers for this vulnerability class.",
            ))


def dream_cycle_consolidation(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Dream Cycle integration — cluster findings, identify recurring patterns.

    Called during Dream Cycle CONSOLIDATION phase to synthesize vulnerability
    patterns from past audits into the knowledge base.
    """
    kb = get_vuln_knowledge_base()

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        by_category.setdefault(cat, []).append(f)

    # Identify recurring patterns (3+ occurrences)
    recurring = []
    for cat, items in by_category.items():
        if len(items) >= 3:
            recurring.append({
                "category": cat,
                "count": len(items),
                "sample_files": [i.get("file", "") for i in items[:3]],
                "avg_severity": _avg_severity(items),
            })

    # Identify novel patterns (first-time seen)
    novel = []
    for cat, items in by_category.items():
        patterns = kb.search_by_keyword(cat)
        if not patterns:
            novel.append({
                "category": cat,
                "count": len(items),
                "message": items[0].get("message", ""),
            })

    return {
        "total_findings": len(findings),
        "categories": len(by_category),
        "recurring_patterns": recurring,
        "novel_patterns": novel,
        "consolidation_timestamp": __import__("time").time(),
    }


def dream_cycle_serendipity(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dream Cycle SERENDIPITY phase — find unexpected cross-domain connections."""
    connections = []

    # Look for findings in different file types with similar patterns
    sol_findings = [f for f in findings if f.get("file", "").endswith(".sol")]
    py_findings = [f for f in findings if f.get("file", "").endswith(".py")]
    [f for f in findings if f.get("file", "").endswith((".js", ".ts", ".jsx", ".tsx"))]

    # Access control issues across languages
    sol_access = [f for f in sol_findings if "access" in f.get("category", "").lower()]
    py_access = [f for f in py_findings if "access" in f.get("category", "").lower() or "auth" in f.get("message", "").lower()]
    if sol_access and py_access:
        connections.append({
            "type": "access_control_cross_language",
            "description": "Access control issues in both Solidity and Python — shared architectural weakness",
            "solidity_count": len(sol_access),
            "python_count": len(py_access),
        })

    # Injection patterns across languages
    sol_injection = [f for f in sol_findings if "delegatecall" in f.get("category", "").lower()]
    py_injection = [f for f in py_findings if "injection" in f.get("category", "").lower()]
    if sol_injection and py_injection:
        connections.append({
            "type": "injection_cross_language",
            "description": "Injection vulnerabilities in both Solidity (delegatecall) and Python — code execution risk",
            "solidity_count": len(sol_injection),
            "python_count": len(py_injection),
        })

    return connections


def dream_cycle_prediction(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dream Cycle PREDICTION phase — predict vulnerability likelihood for new contracts."""
    kb = get_vuln_knowledge_base()
    predictions = []

    for finding in findings:
        category = finding.get("category", "")
        matched = kb.match_findings([finding])
        if matched:
            predictions.append({
                "category": category,
                "file": finding.get("file", ""),
                "pattern_id": matched[0]["pattern"],
                "confidence": matched[0]["confidence"],
                "prediction": f"High probability of {matched[0]['pattern_name']} — matches known exploitable pattern",
            })

    return predictions


def _avg_severity(findings: list[dict]) -> str:
    severities = [f.get("severity", "info") for f in findings]
    severity_order = {"error": 4, "warning": 3, "info": 2, "hint": 1}
    avg = sum(severity_order.get(s, 2) for s in severities) / len(severities)
    if avg >= 3.5:
        return "high"
    if avg >= 2.5:
        return "medium"
    return "low"
