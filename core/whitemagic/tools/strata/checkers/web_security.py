"""Web vulnerability checkers — XSS, IDOR, CSRF, SSRF, open redirect detection."""
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_xss(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect XSS vulnerabilities — unescaped user input in HTML output."""
    for ext_file in file_index.files_by_extension(".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".vue", ".svelte"):
        try:
            content = file_index.read_text(ext_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(ext_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", "/*", "*")):
                continue
            if re.search(r"\binnerHTML\s*=", line) and re.search(r"request\.|input|query|param|\.search|location\.", line, re.IGNORECASE):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="web_xss_innerhtml",
                        file=rel,
                        line=i,
                        message="User input assigned to innerHTML — XSS vulnerability.",
                        suggestion="Use textContent or sanitize HTML with DOMPurify before assignment.",
                    )
                )
            if re.search(r"\bdangerouslySetInnerHTML\b", line):
                context = " ".join(lines[max(0, i - 3) : i + 1])
                if re.search(r"request\.|input|query|param|props\.|state\.", context, re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="web_xss_react",
                            file=rel,
                            line=i,
                            message="dangerouslySetInnerHTML with potentially user-controlled data — XSS risk.",
                            suggestion="Avoid dangerouslySetInnerHTML. Use a sanitization library like DOMPurify.",
                        )
                    )
            if re.search(r"\|safe\b", line) and "django" in content.lower():
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="web_xss_django_safe",
                        file=rel,
                        line=i,
                        message="Django |safe filter used — may render unescaped user input.",
                        suggestion="Remove |safe filter or ensure data is sanitized before rendering.",
                    )
                )
            if re.search(r"<%-.*%>", line) and re.search(r"req\.|params|query|body", " ".join(lines[max(0, i - 2) : i + 1])):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="web_xss_ejs",
                        file=rel,
                        line=i,
                        message="EJS unescaped output (<%-) with user input — XSS vulnerability.",
                        suggestion="Use <%= %> for escaped output, or sanitize input.",
                    )
                )


@register
def check_open_redirect(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect open redirect — user-controlled redirect URLs."""
    for ext_file in file_index.files_by_extension(".py", ".js", ".ts", ".tsx", ".jsx"):
        try:
            content = file_index.read_text(ext_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(ext_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//")):
                continue
            redirect_patterns = [
                r"\bredirect\s*\(",
                r"\bres\.redirect\s*\(",
                r"\bresponse\.redirect\s*\(",
                r"\bHttpResponseRedirect\s*\(",
                r"\bredirect_to\s*\(",
                r"\bnavigate\s*\(",
                r"\bwindow\.location\s*=",
                r"\blocation\.href\s*=",
            ]
            for pattern in redirect_patterns:
                if re.search(pattern, line):
                    if re.search(r"request\.(GET|POST|args|form|query|params|body)|req\.(query|params|body)|input\s*\(", line):
                        if not re.search(r"validate|sanitize|whitelist|allowed|safe_url|url_has_allowed_host", line, re.IGNORECASE):
                            findings.append(
                                Finding(
                                    severity=FindingSeverity.WARNING,
                                    category="web_open_redirect",
                                    file=rel,
                                    line=i,
                                    message="User input in redirect URL — open redirect vulnerability.",
                                    suggestion="Validate redirect URLs against an allowlist of trusted domains.",
                                )
                            )
                            break


@register
def check_csrf(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect missing CSRF protection on state-changing routes."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        if "django" not in content.lower() and "flask" not in content.lower() and "fastapi" not in content.lower():
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"@(app|router|bp)\.(post|put|delete|patch)\s*\(", line) or re.search(
                r"\b@require_(POST|http_methods)", line
            ):
                context = " ".join(lines[max(0, i - 3) : min(len(lines), i + 5)])
                if not re.search(r"csrf|CSRF|CsrfProtect|@ensure_csrf|csrf_protect|X-CSRFToken|csrf_token", context):
                    if "django" in content.lower() and not re.search(r"@csrf_exempt", context):
                        findings.append(
                            Finding(
                                severity=FindingSeverity.INFO,
                                category="web_csrf_missing",
                                file=rel,
                                line=i,
                                message="State-changing route without visible CSRF protection.",
                                suggestion="Add @csrf_protect decorator or ensure CSRF middleware is active.",
                            )
                        )


@register
def check_idor(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect IDOR — object access without ownership checks."""
    for py_file in file_index.files_by_extension(".py", ".js", ".ts"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//")):
                continue
            if re.search(r"\.objects\.get\s*\(|\.filter\s*\(|\.find\s*\(|\.findById\s*\(|\.findOne\s*\(", line):
                if re.search(r"request\.(GET|POST|args|form|query|params)|req\.(params|query|body)", line):
                    context = " ".join(lines[max(0, i - 1) : min(len(lines), i + 5)])
                    if not re.search(r"owner|user|author|created_by|user_id|request\.user|req\.user|currentUser|isOwner", context):
                        findings.append(
                            Finding(
                                severity=FindingSeverity.WARNING,
                                category="web_idor",
                                file=rel,
                                line=i,
                                message="Object lookup by user-supplied ID without ownership check — IDOR risk.",
                                suggestion="Verify the requesting user owns the object before returning/modifying it.",
                            )
                        )
