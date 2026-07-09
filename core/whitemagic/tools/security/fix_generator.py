"""Fix template generation — generate PR-ready fixes for known vulnerabilities."""
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FixSuggestion:
    file: str
    line: int
    original: str
    fixed: str
    fix_type: str
    description: str


# Fix templates for common vulnerability patterns
FIX_TEMPLATES: dict[str, dict[str, str]] = {
    "sol_tx_origin_auth": {
        "pattern": r"tx\.origin",
        "replacement": "msg.sender",
        "description": "Replace tx.origin with msg.sender for authorization",
        "fix_type": "access_control",
    },
    "sol_unchecked_call": {
        "pattern": r"(\w+\.call\([^)]+\))",
        "replacement": r"(bool success,) = \1; require(success, \"Call failed\")",
        "description": "Add return value check for external call",
        "fix_type": "error_handling",
    },
    "sol_unprotected_selfdestruct": {
        "pattern": r"selfdestruct\s*\(",
        "replacement": "require(msg.sender == owner, \"Not owner\"); selfdestruct(",
        "description": "Add access control before selfdestruct",
        "fix_type": "access_control",
    },
    "sqli_fstring": {
        "pattern": r"execute\s*\(\s*f[\"']",
        "replacement": "execute(?  # Use parameterized query instead",
        "description": "Replace f-string SQL with parameterized query",
        "fix_type": "injection",
    },
    "xss_innerhtml": {
        "pattern": r"\.innerHTML\s*=",
        "replacement": ".textContent =",
        "description": "Replace innerHTML with textContent to prevent XSS",
        "fix_type": "xss",
    },
    "cmd_injection": {
        "pattern": r"shell\s*=\s*True",
        "replacement": "shell=False",
        "description": "Set shell=False to prevent command injection",
        "fix_type": "injection",
    },
}


def generate_fix(file_path: str, line_num: int, category: str, original_line: str) -> FixSuggestion | None:
    """Generate a fix suggestion for a specific finding."""
    if category not in FIX_TEMPLATES:
        return None

    template = FIX_TEMPLATES[category]
    try:
        fixed = re.sub(template["pattern"], template["replacement"], original_line, count=1)
        if fixed == original_line:
            return None
        return FixSuggestion(
            file=file_path,
            line=line_num,
            original=original_line,
            fixed=fixed,
            fix_type=template["fix_type"],
            description=template["description"],
        )
    except re.error:
        return None


def generate_fixes_from_findings(findings: list[dict[str, Any]], project_path: str) -> list[FixSuggestion]:
    """Generate fix suggestions for a list of STRATA findings."""
    fixes = []
    project = Path(project_path)

    for finding in findings:
        category = finding.get("category", "")
        file_str = finding.get("file", "")
        line_num = finding.get("line", 0)
        if not file_str or not line_num:
            continue

        file_path = project / file_str
        if not file_path.exists():
            continue

        try:
            lines = file_path.read_text().splitlines()
            if line_num <= len(lines):
                original = lines[line_num - 1]
                fix = generate_fix(str(file_path), line_num, category, original)
                if fix:
                    fixes.append(fix)
        except (OSError, IndexError):
            continue

    return fixes


def apply_fix(fix: FixSuggestion, dry_run: bool = True) -> dict[str, Any]:
    """Apply a fix to a file (or just preview if dry_run)."""
    file_path = Path(fix.file)
    if not file_path.exists():
        return {"success": False, "error": "File not found"}

    try:
        content = file_path.read_text()
        lines = content.splitlines()
        if fix.line <= len(lines):
            old_line = lines[fix.line - 1]
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "file": fix.file,
                    "line": fix.line,
                    "original": old_line,
                    "fixed": fix.fixed,
                    "description": fix.description,
                }
            else:
                lines[fix.line - 1] = fix.fixed
                file_path.write_text("\n".join(lines) + "\n")
                return {"success": True, "dry_run": False, "file": fix.file, "line": fix.line}
    except OSError as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "error": "Line out of range"}


def create_pr(
    repo_dir: str,
    branch_name: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
    bounty_ref: str | None = None,
) -> dict[str, Any]:
    """Create a GitHub PR with the fix."""
    pr_body = body
    if bounty_ref:
        pr_body += f"\n\n**Bounty reference**: {bounty_ref}\n**Generated by**: WhiteMagic Security Pipeline"

    try:
        # Create branch
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_dir, capture_output=True, text=True)
        # Commit changes
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", title], cwd=repo_dir, capture_output=True, text=True)
        # Push
        push_result = subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=repo_dir, capture_output=True, text=True, timeout=30,
        )
        if push_result.returncode != 0:
            return {"success": False, "error": f"Push failed: {push_result.stderr}"}

        # Create PR via gh CLI
        gh_cmd = ["gh", "pr", "create", "--title", title, "--body", pr_body]
        if labels:
            for label in labels:
                gh_cmd.extend(["--label", label])
        pr_result = subprocess.run(
            gh_cmd, cwd=repo_dir, capture_output=True, text=True, timeout=30,
        )
        if pr_result.returncode == 0:
            return {"success": True, "pr_url": pr_result.stdout.strip()}
        return {"success": False, "error": f"PR creation failed: {pr_result.stderr}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def track_bounty_earnings(
    source: str,
    amount: str,
    issue_url: str,
    status: str = "pending",
) -> dict[str, Any]:
    """Track bounty earnings as a structured record for memory ingestion."""
    import time
    return {
        "type": "bounty_earnings",
        "source": source,
        "amount": amount,
        "issue_url": issue_url,
        "status": status,
        "timestamp": time.time(),
        "description": f"Bounty {status} from {source}: {amount} for {issue_url}",
    }
