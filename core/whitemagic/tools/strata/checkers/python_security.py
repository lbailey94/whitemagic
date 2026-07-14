"""Python security checkers — web vulnerability and secret detection."""
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_SECRET_PATTERNS = [
    (r"(?:api[_\-.]?key|apikey)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})['\"]", "API key"),
    (r"(?:secret|secret[_-]?key)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})['\"]", "Secret key"),
    (r"(?:token|auth[_-]?token)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})['\"]", "Token"),
    (r"(?:access[_-]?key|access[_-]?token)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})['\"]", "Access key"),
    (r"(?:aws[_-]?secret|aws[_-]?access)\s*[=:]\s*['\"]([A-Za-z0-9/+=]{40})['\"]", "AWS credential"),
    (r"(?:private[_-]?key)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{30,})['\"]", "Private key"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private key file"),
    (r"gh[pousr]_[A-Za-z0-9]{36}", "GitHub token"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI API key"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*", "JWT token"),
    (r"sk_live_[A-Za-z0-9]{24}", "Stripe key"),
    (r"SK[0-9a-fA-F]{32}", "Twilio key"),
    (r"SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}", "SendGrid key"),
    (r"Bearer [A-Za-z0-9_\-\.]{20,}", "Bearer token"),
    (r"v1\.0-[A-Za-z0-9_\-]{40,}", "Cloudflare key"),
]

_UNQUOTED_SECRET_PATTERN = re.compile(
    r"^(?:export\s+)?([A-Z_][A-Z0-9_]*)=(?!['\"])([A-Za-z0-9+/=_\-]{20,})$",
    re.MULTILINE,
)
_UNQUOTED_SKIP = re.compile(
    r"getenv|environ|os\.getenv|config\(|\.env|placeholder|example|dummy|fake|test|xxxx|sample|default|your_|REPLACE|INSERT",
    re.IGNORECASE,
)


@register
def check_python_secrets(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect hardcoded secrets, API keys, and credentials across file types."""
    skip_dirs = {".git", "__pycache__", ".venv", "node_modules", ".env"}
    for py_file in file_index.files_by_extension(
        ".py", ".js", ".ts", ".tsx", ".jsx", ".yaml", ".yml", ".env",
        ".json", ".toml", ".cfg", ".ini", ".properties", ".xml", ".sh", ".bash", ".zsh",
    ):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        parts = py_file.relative_to(project_path).parts
        if any(part in skip_dirs for part in parts):
            continue
        rel = "/".join(parts)
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            for pattern, secret_type in _SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    if re.search(r"getenv|environ|os\.getenv|config\(|\.env|placeholder|example|dummy|fake|test|xxxx", line, re.IGNORECASE):
                        continue
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="hardcoded_secret",
                            file=rel,
                            line=i,
                            message=f"Hardcoded {secret_type} detected.",
                            suggestion="Use environment variables or a secrets manager. Never commit credentials.",
                        )
                    )
                    break
            else:
                if _UNQUOTED_SECRET_PATTERN.search(line):
                    if _UNQUOTED_SKIP.search(line):
                        continue
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="hardcoded_secret",
                            file=rel,
                            line=i,
                            message="Hardcoded unquoted secret detected.",
                            suggestion="Use environment variables or a secrets manager. Never commit credentials.",
                        )
                    )


# Backward-compatible alias
check_hardcoded_secrets = check_python_secrets


@register
def check_python_sqli(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect SQL injection vulnerabilities — string-formatted queries."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            sql_context = re.search(r"(?:execute|cursor|query|raw|sql)\s*\(", line, re.IGNORECASE)
            if not sql_context:
                continue
            if re.search(r"f['\"].*(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION)", line, re.IGNORECASE):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="py_sql_injection",
                        file=rel,
                        line=i,
                        message="SQL query with f-string formatting — SQL injection risk.",
                        suggestion="Use parameterized queries: cursor.execute('SELECT * FROM t WHERE id = %s', (id,))",
                    )
                )
            elif re.search(r"\+\s*str\(|%[sd].*(?:SELECT|INSERT|UPDATE|DELETE)", line, re.IGNORECASE) and re.search(
                r"(?:SELECT|INSERT|UPDATE|DELETE|WHERE)", line, re.IGNORECASE
            ):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="py_sql_injection",
                        file=rel,
                        line=i,
                        message="SQL query with string concatenation — SQL injection risk.",
                        suggestion="Use parameterized queries instead of string concatenation.",
                    )
                )


@register
def check_python_path_traversal(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect path traversal vulnerabilities — user input in file paths."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            file_ops = re.search(r"\b(open|Path|read_file|write_file|send_file|send_from_directory)\s*\(", line)
            if not file_ops:
                continue
            if re.search(r"\brequest\.(GET|POST|args|form|data|json|cookies|headers)\b", line) or re.search(
                r"\binput\s*\(|\bargv\b|\bgetenv\b.*(?:open|Path|file)", line
            ):
                if not re.search(r"safe_join|secure_filename|sanitize|validate|whitelist|allowed", line, re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="py_path_traversal",
                            file=rel,
                            line=i,
                            message="User input in file path — path traversal risk.",
                            suggestion="Validate and sanitize paths. Use safe_join or restrict to a base directory.",
                        )
                    )


@register
def check_python_command_injection(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect command injection — user input in subprocess calls."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            cmd_context = re.search(r"\b(os\.system|os\.popen|subprocess\.(call|run|Popen|check_output|check_call)|commands\.getoutput)\s*\(", line)
            if not cmd_context:
                continue
            if re.search(r"shell\s*=\s*True", line):
                if re.search(r"\brequest\.|\binput\s*\(|\bargv\b|\bgetenv\b|f['\"]", line):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="py_command_injection",
                            file=rel,
                            line=i,
                            message="Shell=True with user input — command injection risk.",
                            suggestion="Use shell=False with argument list, or sanitize input with shlex.quote().",
                        )
                    )
            elif re.search(r"f['\"].*\b(os\.system|subprocess)", line) and re.search(r"request\.|input\s*\(|argv", line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="py_command_injection",
                        file=rel,
                        line=i,
                        message="f-string in subprocess call — command injection risk.",
                        suggestion="Pass arguments as a list with shell=False.",
                    )
                )


@register
def check_python_ssrf(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect SSRF — user-controlled URLs in HTTP requests."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            http_context = re.search(r"\b(requests\.(get|post|put|delete|head|patch|Session)|urllib\.request\.urlopen|httpx\.(get|post|Client)|aiohttp\.ClientSession)\s*\(", line)
            if not http_context:
                continue
            if re.search(r"\brequest\.(GET|POST|args|form|data|json|GET\.get|POST\.get|args\.get|form\.get)\b", line):
                if not re.search(r"validate|sanitize|whitelist|allowed_hosts|ssrf|safe_url", line, re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="py_ssrf",
                            file=rel,
                            line=i,
                            message="User-controlled URL in HTTP request — SSRF risk.",
                            suggestion="Validate URLs against an allowlist. Block internal IPs (127.0.0.1, 169.254.x.x, 10.x.x.x, etc.).",
                        )
                    )
