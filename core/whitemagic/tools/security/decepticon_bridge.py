"""Decepticon integration — autonomous red-teaming agent wrapper.

Wraps the Decepticon SDK (github.com/0x4m4/decepticon) as MCP-callable tools.
Decepticon provides autonomous red-teaming with LLM-driven attack planning.

If Decepticon is not installed, a fallback pipeline uses WhiteMagic's own
tools (STRATA, nmap, sqlmap, http_probe, nuclei) to provide a similar
autonomous red-teaming workflow:

    recon → plan → exploit → report

All tools route through engagement tokens under violet profile.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 300


@dataclass
class AttackStep:
    """A single step in an autonomous attack plan."""
    step_id: str
    phase: str  # recon, plan, exploit, report
    tool: str
    target: str
    action: str
    status: str = "pending"  # pending, running, success, failed, skipped
    result: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class AttackSession:
    """A full autonomous red-teaming session."""
    session_id: str
    target: str
    scope: str  # engagement scope from token
    steps: list[AttackStep] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    status: str = "initialized"  # initialized, running, completed, failed
    started_at: float = 0.0
    completed_at: float = 0.0
    decepticon_available: bool = False

    def summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "target": self.target,
            "scope": self.scope,
            "status": self.status,
            "step_count": len(self.steps),
            "finding_count": len(self.findings),
            "decepticon_available": self.decepticon_available,
            "duration_seconds": self.completed_at - self.started_at if self.completed_at else 0,
        }


def _check_decepticon() -> str | None:
    """Check if Decepticon is installed. Returns path or None."""
    return shutil.which("decepticon")


def _check_ollama() -> str | None:
    """Check if Ollama is available for local model inference."""
    return shutil.which("ollama")


def run_decepticon_directly(
    target: str,
    scope: str = "recon,scan,exploit",
    model: str = "llama3",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run Decepticon directly if installed.

    Args:
        target: Target URL, IP, or hostname.
        scope: Comma-separated attack phases.
        model: LLM model for attack planning (via Ollama).
        timeout: Maximum runtime in seconds.
    """
    decepticon_bin = _check_decepticon()
    if not decepticon_bin:
        return {
            "status": "error",
            "error_code": "decepticon_not_installed",
            "error": "Decepticon not installed. Install: pip install decepticon-ai",
            "fallback_available": True,
        }

    ollama_bin = _check_ollama()
    if not ollama_bin:
        return {
            "status": "error",
            "error_code": "ollama_not_installed",
            "error": "Ollama not installed. Required for local model inference. Install: curl -fsSL https://ollama.com/install.sh | sh",
        }

    args = ["--target", target, "--scope", scope, "--model", model, "--json"]

    try:
        proc = subprocess.run(
            [decepticon_bin] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "output": proc.stdout[:10000],
            "stderr": proc.stderr[:500] if proc.stderr else "",
            "tool": "decepticon",
            "target": target,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "decepticon", "target": target, "timeout": timeout}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "tool": "decepticon", "error": str(e)}


def run_autonomous_redteam(
    target: str,
    scope: str = "recon,scan,exploit,report",
    engagement_token_id: str = "",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run autonomous red-teaming against a target.

    If Decepticon is installed, delegates to it directly.
    Otherwise, runs a fallback pipeline using WhiteMagic's own tools:
        1. Recon: nmap scan + STRATA analysis (if local path)
        2. Plan: Generate attack plan based on recon findings
        3. Exploit: Run targeted tests (sqlmap, http_probe, nuclei)
        4. Report: Aggregate findings with MITRE ATT&CK mapping

    Args:
        target: Target URL, IP, hostname, or local path.
        scope: Comma-separated phases to run.
        engagement_token_id: Engagement token for governance.
        timeout: Maximum runtime per step in seconds.
    """
    session = AttackSession(
        session_id=f"RT-{int(time.time())}",
        target=target,
        scope=scope,
        started_at=time.time(),
        decepticon_available=_check_decepticon() is not None,
    )

    phases = [p.strip() for p in scope.split(",")]

    # Try Decepticon first
    if session.decepticon_available:
        result = run_decepticon_directly(target, scope, timeout=timeout)
        session.status = result.get("status", "error")
        session.completed_at = time.time()
        session.findings = _extract_decepticon_findings(result)
        return {
            "session": session.summary(),
            "decepticon_result": result,
            "findings": session.findings,
        }

    # Fallback pipeline using WhiteMagic tools
    session.status = "running"

    for phase in phases:
        if phase == "recon":
            step = _run_recon_phase(target, engagement_token_id, timeout)
            session.steps.append(step)
            session.findings.extend(step.result.get("findings", []))

        elif phase == "scan":
            step = _run_scan_phase(target, engagement_token_id, timeout)
            session.steps.append(step)
            session.findings.extend(step.result.get("findings", []))

        elif phase == "exploit":
            step = _run_exploit_phase(target, engagement_token_id, timeout, session.findings)
            session.steps.append(step)
            session.findings.extend(step.result.get("findings", []))

        elif phase == "report":
            step = _run_report_phase(target, session.findings)
            session.steps.append(step)

    session.status = "completed"
    session.completed_at = time.time()

    return {
        "session": session.summary(),
        "steps": [
            {
                "step_id": s.step_id,
                "phase": s.phase,
                "tool": s.tool,
                "status": s.status,
                "finding_count": len(s.result.get("findings", [])),
            }
            for s in session.steps
        ],
        "findings": session.findings,
        "finding_count": len(session.findings),
        "fallback_used": True,
    }


def _run_recon_phase(
    target: str, token_id: str, timeout: int
) -> AttackStep:
    """Recon phase: nmap scan or STRATA analysis."""
    step = AttackStep(
        step_id=f"recon-{int(time.time())}",
        phase="recon",
        tool="nmap+strata",
        target=target,
        action="reconnaissance scan",
        status="running",
        timestamp=time.time(),
    )

    findings = []

    # Check if target is a URL/IP (network) or local path (code analysis)
    if target.startswith("http://") or target.startswith("https://") or _is_ip_or_hostname(target):
        from whitemagic.tools.security.dynamic_testers import run_nmap
        result = run_nmap(
            target=target,
            scan_type="service",
            timeout=timeout,
        )
        findings.extend(result.get("findings", []))
    else:
        # Local path — run STRATA
        try:
            from whitemagic.tools.handlers.strata import handle_strata_analyze
            result = handle_strata_analyze(path=target, format="json")
            strata_findings = result.get("findings", [])
            # Map to MITRE TTPs
            from whitemagic.tools.security.strata_mitre_map import map_findings
            mapped = map_findings(strata_findings)
            for m in mapped:
                findings.append({
                    "tool": "strata",
                    "severity": m["finding"].get("severity", "info"),
                    "category": m["category"],
                    "title": m["finding"].get("message", "")[:100],
                    "detail": m["finding"].get("message", ""),
                    "target": target,
                    "mitre_ttp_ids": m["ttp_ids"],
                })
        except Exception as e:  # noqa: BLE001
            logger.warning("STRATA recon failed: %s", e)

    step.status = "success" if findings else "completed"
    step.result = {"findings": findings, "finding_count": len(findings)}
    return step


def _run_scan_phase(
    target: str, token_id: str, timeout: int
) -> AttackStep:
    """Scan phase: nuclei vulnerability scan."""
    step = AttackStep(
        step_id=f"scan-{int(time.time())}",
        phase="scan",
        tool="nuclei",
        target=target,
        action="vulnerability scan",
        status="running",
        timestamp=time.time(),
    )

    findings = []

    if target.startswith("http://") or target.startswith("https://"):
        from whitemagic.tools.security.dynamic_testers import run_nuclei
        result = run_nuclei(target=target, timeout=timeout)
        findings.extend(result.get("findings", []))
    else:
        step.status = "skipped"
        step.result = {"findings": [], "reason": "nuclei requires HTTP URL"}
        return step

    step.status = "success" if findings else "completed"
    step.result = {"findings": findings, "finding_count": len(findings)}
    return step


def _run_exploit_phase(
    target: str, token_id: str, timeout: int, prior_findings: list[dict[str, Any]]
) -> AttackStep:
    """Exploit phase: targeted testing based on recon findings."""
    step = AttackStep(
        step_id=f"exploit-{int(time.time())}",
        phase="exploit",
        tool="sqlmap+http_probe",
        target=target,
        action="targeted exploitation",
        status="running",
        timestamp=time.time(),
    )

    findings = []

    # Check if any prior findings suggest SQLi
    has_sqli = any(f.get("category") == "py_sql_injection" for f in prior_findings)
    if has_sqli and target.startswith("http"):
        from whitemagic.tools.security.dynamic_testers import run_sqlmap
        result = run_sqlmap(url=target, timeout=timeout)
        findings.extend(result.get("findings", []))

    # Check for XSS
    has_xss = any("xss" in f.get("category", "") for f in prior_findings)
    if has_xss and target.startswith("http"):
        from whitemagic.tools.security.http_probe import get_http_probe
        try:
            probe = get_http_probe()
            xss_result = probe.probe_xss(target, "")
            if xss_result:
                findings.append({
                    "tool": "http_probe",
                    "severity": "high",
                    "category": "web_xss_innerhtml",
                    "title": "XSS confirmed via probe",
                    "detail": str(xss_result),
                    "target": target,
                    "mitre_ttp_ids": ["T1059.007"],
                })
        except Exception as e:  # noqa: BLE001
            logger.warning("XSS probe failed: %s", e)

    step.status = "success" if findings else "completed"
    step.result = {"findings": findings, "finding_count": len(findings)}
    return step


def _run_report_phase(
    target: str, findings: list[dict[str, Any]]
) -> AttackStep:
    """Report phase: aggregate findings with MITRE ATT&CK mapping."""
    step = AttackStep(
        step_id=f"report-{int(time.time())}",
        phase="report",
        tool="contest_pipeline",
        target=target,
        action="generate report",
        status="running",
        timestamp=time.time(),
    )

    # Feed findings into contest pipeline
    try:
        from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
        pipeline = get_contest_pipeline()
        for f in findings:
            pipeline.add_finding(
                title=f.get("title", "Untitled")[:100],
                severity=f.get("severity", "info"),
                category=f.get("category", "unknown"),
                file=f.get("target", target),
                line=None,
                description=f.get("detail", ""),
                impact="",
                proof_of_concept="",
                mitigation="",
                mitre_ttp_ids=f.get("mitre_ttp_ids", []),
            )
        report = pipeline.format_for_platform("mitre")
        step.result = {
            "report_format": "mitre_navigator",
            "report": report[:5000],
            "finding_count": len(findings),
        }
        step.status = "success"
    except Exception as e:  # noqa: BLE001
        step.result = {"error": str(e)}
        step.status = "failed"

    return step


def _extract_decepticon_findings(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract findings from Decepticon output."""
    findings = []
    output = result.get("output", "")
    try:
        data = json.loads(output)
        if isinstance(data, list):
            for item in data:
                findings.append({
                    "tool": "decepticon",
                    "severity": item.get("severity", "info"),
                    "category": item.get("category", "unknown"),
                    "title": item.get("title", item.get("description", "")[:100]),
                    "detail": item.get("description", ""),
                    "target": item.get("target", ""),
                    "mitre_ttp_ids": item.get("mitre_ttp_ids", []),
                })
    except (json.JSONDecodeError, TypeError):
        pass
    return findings


def _is_ip_or_hostname(target: str) -> bool:
    """Check if target looks like an IP or hostname (not a file path)."""
    import re
    if "/" in target and not target.startswith("http"):
        return False  # Likely a path
    # IP address pattern
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
        return True
    # Hostname pattern (no spaces, has dots or is localhost)
    if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$", target):
        return True
    return False


def decepticon_status() -> dict[str, Any]:
    """Check Decepticon and Ollama availability."""
    return {
        "decepticon_available": _check_decepticon() is not None,
        "decepticon_path": _check_decepticon(),
        "ollama_available": _check_ollama() is not None,
        "ollama_path": _check_ollama(),
        "fallback_pipeline": True,
        "supported_phases": ["recon", "scan", "exploit", "report"],
    }
