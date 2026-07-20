"""Dynamic testing wrappers — nmap, sqlmap, hydra, nikto, dirb, ffuf.

Wraps common offensive security CLI tools as MCP-callable handlers.
Each tool:
  1. Checks engagement token (defense-in-depth via _check_offensive_token)
  2. Runs the underlying CLI tool via subprocess with timeout
  3. Parses output into structured findings
  4. Auto-maps findings to MITRE ATT&CK TTPs via strata_mitre_map

All tools are designed to run inside violet shelter compartments.
The middleware (mw_engagement_token) is the primary gate; handler-level
checks provide defense-in-depth.

Tools wrapped:
  - nmap: port scanning, service detection, OS fingerprinting
  - sqlmap: SQL injection detection and exploitation
  - hydra: brute-force authentication testing
  - nikto: web server vulnerability scanning
  - ffuf: web fuzzing (directories, vhosts, parameters)
  - nuclei: template-based vulnerability scanning

If a tool is not installed, handlers return a clear error with install instructions.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default timeout for all dynamic testing tools (seconds)
_DEFAULT_TIMEOUT = 120


@dataclass
class DynamicFinding:
    """A finding from a dynamic testing tool."""
    tool: str
    severity: str  # critical, high, medium, low, info
    category: str  # maps to STRATA category for MITRE ATT&CK mapping
    title: str
    detail: str
    target: str = ""
    evidence: str = ""
    mitre_ttp_ids: list[str] = field(default_factory=list)


def _check_tool_available(tool_name: str) -> str | None:
    """Check if a CLI tool is installed. Returns path or None."""
    return shutil.which(tool_name)


def _run_tool(
    tool: str,
    args: list[str],
    timeout: int = _DEFAULT_TIMEOUT,
    stdin_data: str | None = None,
) -> tuple[int, str, str]:
    """Run a CLI tool and return (returncode, stdout, stderr).

    Raises subprocess.TimeoutExpired if the tool exceeds timeout.
    """
    cmd = [tool] + args
    logger.debug("Running dynamic test: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        input=stdin_data,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _tool_not_installed(tool: str, install_cmd: str) -> dict[str, Any]:
    """Return a standard 'tool not installed' error response."""
    return {
        "status": "error",
        "error_code": "tool_not_installed",
        "error": f"{tool} is not installed. Install with: {install_cmd}",
        "tool": tool,
    }


# ═══════════════════════════════════════════════════════════════════════════
# nmap — Network scanning
# ═══════════════════════════════════════════════════════════════════════════

def run_nmap(
    target: str,
    scan_type: str = "service",
    ports: str = "",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run nmap against a target.

    Args:
        target: IP address, hostname, or CIDR range.
        scan_type: One of: quick, service, os, full, udp, script.
        ports: Specific ports (e.g., "80,443,8080"). Empty = default.
        timeout: Maximum runtime in seconds.
    """
    if not _check_tool_available("nmap"):
        return _tool_not_installed("nmap", "sudo apt install nmap")

    scan_args = {
        "quick": ["-T4", "-F"],
        "service": ["-sV", "-sC", "-T4"],
        "os": ["-O", "-sV", "-T4"],
        "full": ["-p-", "-sV", "-sC", "-T4"],
        "udp": ["-sU", "-T4"],
        "script": ["-sC", "-sV", "-T4"],
    }
    args = scan_args.get(scan_type, scan_args["service"])
    if ports:
        args = ["-p", ports] + args

    try:
        rc, stdout, stderr = _run_tool("nmap", args + [target], timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "nmap", "target": target, "timeout": timeout}
    except Exception as e:
        return {"status": "error", "tool": "nmap", "error": str(e)}

    # Parse nmap output
    findings = _parse_nmap_output(stdout, target)

    return {
        "status": "success" if rc == 0 else "error",
        "tool": "nmap",
        "target": target,
        "scan_type": scan_type,
        "returncode": rc,
        "findings": [f.__dict__ for f in findings],
        "finding_count": len(findings),
        "raw_output": stdout[:5000],
        "stderr": stderr[:500] if stderr else "",
    }


def _parse_nmap_output(output: str, target: str) -> list[DynamicFinding]:
    """Parse nmap output into structured findings."""
    findings = []

    for line in output.splitlines():
        # Match open/closed/filtered ports
        port_match = re.match(
            r"(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)(?:\s+(.*))?", line
        )
        if port_match:
            port_num, proto, state, service, version = port_match.groups()
            if state == "open":
                severity = "medium"
                if service in {"http", "https"} and port_num in {"80", "443"}:
                    severity = "info"
                elif service in {"ftp", "telnet", "rsh", "rlogin"}:
                    severity = "high"
                elif port_num in {"22", "3389"}:
                    severity = "low"

                findings.append(DynamicFinding(
                    tool="nmap",
                    severity=severity,
                    category="py_ssrf" if service in {"http", "https"} else "hardcoded_url",
                    title=f"Open port {port_num}/{proto} — {service}",
                    detail=f"Port {port_num}/{proto} is {state} running {service}{' ' + (version or '')}".strip(),
                    target=f"{target}:{port_num}",
                    evidence=line,
                    mitre_ttp_ids=["T1046"],  # Network Service Discovery
                ))

    return findings


# ═══════════════════════════════════════════════════════════════════════════
# sqlmap — SQL injection
# ═══════════════════════════════════════════════════════════════════════════

def run_sqlmap(
    url: str,
    method: str = "GET",
    data: str = "",
    param: str = "",
    cookie: str = "",
    level: int = 1,
    risk: int = 1,
    timeout: int = 180,
) -> dict[str, Any]:
    """Run sqlmap against a URL to test for SQL injection.

    Args:
        url: Target URL with parameters.
        method: HTTP method (GET or POST).
        data: POST data if method is POST.
        param: Specific parameter to test. Empty = test all.
        cookie: Cookie header for authenticated testing.
        level: sqlmap level (1-5). Higher = more tests.
        risk: sqlmap risk (1-3). Higher = more aggressive.
        timeout: Maximum runtime in seconds.
    """
    if not _check_tool_available("sqlmap"):
        return _tool_not_installed("sqlmap", "sudo apt install sqlmap")

    args = ["-u", url, "--batch", f"--level={level}", f"--risk={risk}"]
    if method.upper() == "POST" and data:
        args.extend(["--method=POST", f"--data={data}"])
    if param:
        args.extend(["-p", param])
    if cookie:
        args.extend(["--cookie", cookie])

    try:
        rc, stdout, stderr = _run_tool("sqlmap", args, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "sqlmap", "url": url, "timeout": timeout}
    except Exception as e:
        return {"status": "error", "tool": "sqlmap", "error": str(e)}

    findings = _parse_sqlmap_output(stdout, url)

    return {
        "status": "success" if rc == 0 else "error",
        "tool": "sqlmap",
        "url": url,
        "returncode": rc,
        "findings": [f.__dict__ for f in findings],
        "finding_count": len(findings),
        "raw_output": stdout[:5000],
        "stderr": stderr[:500] if stderr else "",
    }


def _parse_sqlmap_output(output: str, url: str) -> list[DynamicFinding]:
    """Parse sqlmap output for injection findings."""
    findings = []
    for line in output.splitlines():
        line_lower = line.lower()
        # Skip negative results
        if "do not appear to be injectable" in line_lower or "not vulnerable" in line_lower:
            continue
        if "is vulnerable" in line_lower or "injectable" in line_lower:
            findings.append(DynamicFinding(
                tool="sqlmap",
                severity="critical",
                category="py_sql_injection",
                title="SQL injection vulnerability confirmed",
                detail=line.strip(),
                target=url,
                evidence=line,
                mitre_ttp_ids=["T1190", "T1213"],
            ))
        elif "sqlmap identified the following injection point" in line.lower():
            findings.append(DynamicFinding(
                tool="sqlmap",
                severity="critical",
                category="py_sql_injection",
                title="SQL injection point identified",
                detail=line.strip(),
                target=url,
                evidence=line,
                mitre_ttp_ids=["T1190", "T1213"],
            ))
        elif "parameter:" in line.lower() and "type:" in line.lower():
            findings.append(DynamicFinding(
                tool="sqlmap",
                severity="high",
                category="py_sql_injection",
                title=f"Injectable parameter detected: {line.strip()}",
                detail=line.strip(),
                target=url,
                evidence=line,
                mitre_ttp_ids=["T1190"],
            ))
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# hydra — Brute-force authentication
# ═══════════════════════════════════════════════════════════════════════════

def run_hydra(
    target: str,
    service: str,
    userlist: str = "",
    passlist: str = "",
    user: str = "",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run hydra for brute-force authentication testing.

    Args:
        target: Target host or IP.
        service: Service to attack (ssh, ftp, http-get, etc.).
        userlist: Path to username list file.
        passlist: Path to password list file.
        user: Single username (alternative to userlist).
        timeout: Maximum runtime in seconds.
    """
    if not _check_tool_available("hydra"):
        return _tool_not_installed("hydra", "sudo apt install hydra")

    args = ["-f", "-q"]  # -f: stop on first match, -q: quiet
    if user:
        args.extend(["-l", user])
    elif userlist:
        args.extend(["-L", userlist])
    else:
        return {"status": "error", "error": "Either user or userlist required"}

    if passlist:
        args.extend(["-P", passlist])
    else:
        return {"status": "error", "error": "passlist required"}

    args.extend([target, service])

    try:
        rc, stdout, stderr = _run_tool("hydra", args, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "hydra", "target": target, "timeout": timeout}
    except Exception as e:
        return {"status": "error", "tool": "hydra", "error": str(e)}

    findings = _parse_hydra_output(stdout, target, service)

    return {
        "status": "success" if rc == 0 else "error",
        "tool": "hydra",
        "target": target,
        "service": service,
        "returncode": rc,
        "findings": [f.__dict__ for f in findings],
        "finding_count": len(findings),
        "raw_output": stdout[:5000],
        "stderr": stderr[:500] if stderr else "",
    }


def _parse_hydra_output(output: str, target: str, service: str) -> list[DynamicFinding]:
    """Parse hydra output for successful credentials."""
    findings = []
    for line in output.splitlines():
        if "login:" in line.lower() and "password:" in line.lower():
            findings.append(DynamicFinding(
                tool="hydra",
                severity="critical",
                category="hardcoded_secret",
                title=f"Valid credentials found for {service}",
                detail=line.strip(),
                target=f"{target} ({service})",
                evidence=line,
                mitre_ttp_ids=["T1552", "T1110"],  # Unsecured Credentials + Brute Force
            ))
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# nikto — Web server scanner
# ═══════════════════════════════════════════════════════════════════════════

def run_nikto(
    target: str,
    port: int = 80,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run nikto web server scanner against a target.

    Args:
        target: Target URL or hostname.
        port: Target port.
        timeout: Maximum runtime in seconds.
    """
    if not _check_tool_available("nikto"):
        return _tool_not_installed("nikto", "sudo apt install nikto")

    args = ["-h", target, "-p", str(port), "-Format", "json"]

    try:
        rc, stdout, stderr = _run_tool("nikto", args, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "nikto", "target": target, "timeout": timeout}
    except Exception as e:
        return {"status": "error", "tool": "nikto", "error": str(e)}

    findings = _parse_nikto_output(stdout, target)

    return {
        "status": "success" if rc == 0 else "error",
        "tool": "nikto",
        "target": target,
        "port": port,
        "returncode": rc,
        "findings": [f.__dict__ for f in findings],
        "finding_count": len(findings),
        "raw_output": stdout[:5000],
        "stderr": stderr[:500] if stderr else "",
    }


def _parse_nikto_output(output: str, target: str) -> list[DynamicFinding]:
    """Parse nikto JSON output for vulnerabilities."""
    findings = []
    try:
        data = json.loads(output)
        vulns = data.get("vulnerabilities", [])
        for v in vulns:
            sev = "medium"
            msg = v.get("msg", "")
            if "osvdb" in msg.lower() or "xss" in msg.lower():
                sev = "high"
            elif "outdated" in msg.lower():
                sev = "low"

            category = "web_xss_innerhtml" if "xss" in msg.lower() else "hardcoded_url"

            findings.append(DynamicFinding(
                tool="nikto",
                severity=sev,
                category=category,
                title=msg[:100],
                detail=v.get("msg", ""),
                target=target,
                evidence=json.dumps(v),
                mitre_ttp_ids=["T1190"] if sev in ("high", "critical") else [],
            ))
    except (json.JSONDecodeError, KeyError):
        # Fallback: parse text output
        for line in output.splitlines():
            if line.strip().startswith("+") and "OSVDB" in line:
                findings.append(DynamicFinding(
                    tool="nikto",
                    severity="high",
                    category="hardcoded_url",
                    title=line.strip()[:100],
                    detail=line.strip(),
                    target=target,
                    evidence=line,
                    mitre_ttp_ids=["T1190"],
                ))
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# ffuf — Web fuzzing
# ═══════════════════════════════════════════════════════════════════════════

def run_ffuf(
    url: str,
    wordlist: str = "",
    mode: str = "dir",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run ffuf for web content fuzzing.

    Args:
        url: Target URL with FUZZ keyword (e.g., http://target/FUZZ).
        wordlist: Path to wordlist file.
        mode: Fuzzing mode: dir, vhost, or param.
        timeout: Maximum runtime in seconds.
    """
    if not _check_tool_available("ffuf"):
        return _tool_not_installed("ffuf", "go install github.com/ffuf/ffuf/v2@latest")

    if not wordlist:
        return {"status": "error", "error": "wordlist path required"}

    if "FUZZ" not in url:
        url = url.rstrip("/") + "/FUZZ"

    args = ["-u", url, "-w", wordlist, "-s", "-o", "/dev/stdout", "-of", "json"]

    try:
        rc, stdout, stderr = _run_tool("ffuf", args, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "ffuf", "url": url, "timeout": timeout}
    except Exception as e:
        return {"status": "error", "tool": "ffuf", "error": str(e)}

    findings = _parse_ffuf_output(stdout, url)

    return {
        "status": "success" if rc == 0 else "error",
        "tool": "ffuf",
        "url": url,
        "mode": mode,
        "returncode": rc,
        "findings": [f.__dict__ for f in findings],
        "finding_count": len(findings),
        "raw_output": stdout[:5000],
        "stderr": stderr[:500] if stderr else "",
    }


def _parse_ffuf_output(output: str, url: str) -> list[DynamicFinding]:
    """Parse ffuf JSON output for discovered paths."""
    findings = []
    try:
        data = json.loads(output)
        results = data.get("results", [])
        for r in results:
            status = r.get("status", 0)
            sev = "info"
            if status == 200:
                sev = "low"
            elif status in (301, 302):
                sev = "info"
            elif status == 403:
                sev = "medium"

            findings.append(DynamicFinding(
                tool="ffuf",
                severity=sev,
                category="web_idor",
                title=f"Discovered path: {r.get('input', {}).get('FUZZ', '')} (HTTP {status})",
                detail=f"Path {r.get('input', {}).get('FUZZ', '')} returned status {status}, size {r.get('length', 0)}",
                target=url.replace("FUZZ", r.get("input", {}).get("FUZZ", "")),
                evidence=json.dumps(r),
                mitre_ttp_ids=["T1083"] if status == 200 else [],  # File and Directory Discovery
            ))
    except (json.JSONDecodeError, KeyError):
        pass
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# nuclei — Template-based vulnerability scanner
# ═══════════════════════════════════════════════════════════════════════════

def run_nuclei(
    target: str,
    templates: str = "",
    severity: str = "",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run nuclei template-based vulnerability scanner.

    Args:
        target: Target URL.
        templates: Path to templates directory or specific template.
        severity: Filter by severity (low, medium, high, critical).
        timeout: Maximum runtime in seconds.
    """
    if not _check_tool_available("nuclei"):
        return _tool_not_installed("nuclei", "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest")

    args = ["-u", target, "-json", "-silent"]
    if templates:
        args.extend(["-t", templates])
    if severity:
        args.extend(["-severity", severity])

    try:
        rc, stdout, stderr = _run_tool("nuclei", args, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": "nuclei", "target": target, "timeout": timeout}
    except Exception as e:
        return {"status": "error", "tool": "nuclei", "error": str(e)}

    findings = _parse_nuclei_output(stdout, target)

    return {
        "status": "success" if rc == 0 else "error",
        "tool": "nuclei",
        "target": target,
        "returncode": rc,
        "findings": [f.__dict__ for f in findings],
        "finding_count": len(findings),
        "raw_output": stdout[:5000],
        "stderr": stderr[:500] if stderr else "",
    }


def _parse_nuclei_output(output: str, target: str) -> list[DynamicFinding]:
    """Parse nuclei JSON output for vulnerabilities."""
    findings = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            sev = data.get("info", {}).get("severity", "info").lower()
            template_id = data.get("template-id", data.get("templateID", ""))
            matched = data.get("matched-at", data.get("matched", ""))

            # Map to STRATA categories
            category = "hardcoded_url"
            ttp_ids = []
            if "xss" in template_id.lower():
                category = "web_xss_innerhtml"
                ttp_ids = ["T1059.007"]
            elif "sqli" in template_id.lower() or "sql" in template_id.lower():
                category = "py_sql_injection"
                ttp_ids = ["T1190", "T1213"]
            elif "ssrf" in template_id.lower():
                category = "py_ssrf"
                ttp_ids = ["T1046"]
            elif "rce" in template_id.lower() or "exec" in template_id.lower():
                category = "py_command_injection"
                ttp_ids = ["T1059"]
            elif "redirect" in template_id.lower():
                category = "web_open_redirect"
                ttp_ids = ["T1566.002"]
            elif "csrf" in template_id.lower():
                category = "web_csrf_missing"
                ttp_ids = ["T1185"]
            elif "exposure" in template_id.lower() or "config" in template_id.lower():
                category = "hardcoded_secret"
                ttp_ids = ["T1552"]

            findings.append(DynamicFinding(
                tool="nuclei",
                severity=sev,
                category=category,
                title=f"{data.get('info', {}).get('name', template_id)} — {matched}",
                detail=data.get("info", {}).get("description", template_id),
                target=matched or target,
                evidence=line,
                mitre_ttp_ids=ttp_ids,
            ))
        except json.JSONDecodeError:
            continue
    return findings
