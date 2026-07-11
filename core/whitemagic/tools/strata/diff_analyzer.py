"""Diff-aware code analysis — run STRATA checkers only on changed lines.

Parses unified diff format, maps hunks to file paths and line ranges,
runs only relevant checkers per file type, and suppresses findings on
unchanged lines to reduce noise.

Usage:
    from whitemagic.tools.strata.diff_analyzer import DiffAnalyzer

    analyzer = DiffAnalyzer()
    files = analyzer.parse_diff(diff_text)
    for file_diff in files:
        findings = analyzer.analyze_file(file_diff)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Diff line patterns
_DIFF_FILE_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+?)$")
_DIFF_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_ADDED = re.compile(r"^\+(.*)$")
_DIFF_REMOVED = re.compile(r"^-(.*)$")
_DIFF_CONTEXT = re.compile(r"^ (.*)$")


@dataclass
class FileDiff:
    """Represents a single file's changes in a diff."""
    path: str
    old_path: str = ""
    additions: int = 0
    deletions: int = 0
    hunks: list["HunkDiff"] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    is_rename: bool = False

    @property
    def language(self) -> str:
        """Detect language from file extension."""
        ext = Path(self.path).suffix.lower()
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".kt": "java",
            ".rb": "ruby",
            ".lua": "lua",
            ".swift": "swift",
            ".sol": "solidity",
            ".sh": "shell",
            ".bash": "shell",
            ".zig": "zig",
            ".rs": "rust",
            ".go": "go",
            ".hs": "haskell",
            ".ex": "elixir",
            ".exs": "elixir",
            ".jl": "julia",
        }.get(ext, "unknown")

    @property
    def added_lines(self) -> set[int]:
        """Set of line numbers that were added."""
        lines: set[int] = set()
        for hunk in self.hunks:
            lines.update(hunk.added_line_numbers)
        return lines


@dataclass
class HunkDiff:
    """Represents a single hunk in a file diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list["DiffLine"] = field(default_factory=list)

    @property
    def added_line_numbers(self) -> set[int]:
        """Set of new file line numbers that were added."""
        result: set[int] = set()
        line_num = self.new_start
        for dl in self.lines:
            if dl.type == "added":
                result.add(line_num)
                line_num += 1
            elif dl.type == "context":
                line_num += 1
        return result


@dataclass
class DiffLine:
    """A single line in a diff hunk."""
    type: str  # added, removed, context
    content: str
    new_line_number: int = 0


class DiffAnalyzer:
    """Parse unified diffs and run targeted STRATA analysis on changed lines.

    This reduces noise by only reporting findings on lines that were actually
    changed in the PR, not pre-existing issues.
    """

    def parse_diff(self, diff_text: str) -> list[FileDiff]:
        """Parse a unified diff into per-file diff objects.

        Args:
            diff_text: Raw unified diff text (e.g. from `git diff` or GitHub API).

        Returns:
            List of FileDiff objects, one per changed file.
        """
        files: list[FileDiff] = []
        current_file: FileDiff | None = None
        current_hunk: HunkDiff | None = None
        new_line = 0

        for line in diff_text.splitlines():
            # File header
            file_match = _DIFF_FILE_HEADER.match(line)
            if file_match:
                if current_file:
                    files.append(current_file)
                old_path, new_path = file_match.groups()
                current_file = FileDiff(
                    path=new_path,
                    old_path=old_path,
                    is_new=old_path == "/dev/null",
                    is_deleted=new_path == "/dev/null",
                    is_rename=old_path != new_path and old_path != "/dev/null" and new_path != "/dev/null",
                )
                current_hunk = None
                continue

            # Hunk header
            hunk_match = _DIFF_HUNK_HEADER.match(line)
            if hunk_match and current_file:
                if current_hunk and current_file:
                    current_file.hunks.append(current_hunk)
                old_start, old_count, new_start, new_count = hunk_match.groups()
                current_hunk = HunkDiff(
                    old_start=int(old_start),
                    old_count=int(old_count or 1),
                    new_start=int(new_start),
                    new_count=int(new_count or 1),
                )
                new_line = int(new_start)
                continue

            # Diff lines (only if we're in a hunk)
            if current_hunk and current_file:
                added_match = _DIFF_ADDED.match(line)
                removed_match = _DIFF_REMOVED.match(line)
                context_match = _DIFF_CONTEXT.match(line)

                if added_match:
                    current_hunk.lines.append(DiffLine(type="added", content=added_match.group(1), new_line_number=new_line))
                    current_file.additions += 1
                    new_line += 1
                elif removed_match:
                    current_hunk.lines.append(DiffLine(type="removed", content=removed_match.group(1)))
                    current_file.deletions += 1
                elif context_match:
                    current_hunk.lines.append(DiffLine(type="context", content=context_match.group(1), new_line_number=new_line))
                    new_line += 1

        if current_hunk and current_file:
            current_file.hunks.append(current_hunk)
        if current_file:
            files.append(current_file)

        return files

    def analyze_file(self, file_diff: FileDiff) -> list[dict[str, Any]]:
        """Run STRATA checkers on a single file diff.

        Only reports findings on lines that were added in the diff.
        Findings on unchanged context lines are suppressed.

        Args:
            file_diff: The file diff to analyze.

        Returns:
            List of finding dicts with file, line, severity, message, checker, suggestion.
        """
        if file_diff.is_deleted:
            return []

        if file_diff.language == "unknown":
            logger.debug("Skipping unknown language file: %s", file_diff.path)
            return []

        added_lines = file_diff.added_lines
        if not added_lines:
            return []

        # Collect added line content for analysis
        added_content: dict[int, str] = {}
        for hunk in file_diff.hunks:
            line_num = hunk.new_start
            for dl in hunk.lines:
                if dl.type == "added":
                    added_content[line_num] = dl.content
                    line_num += 1
                elif dl.type == "context":
                    line_num += 1

        findings: list[dict[str, Any]] = []

        # Run language-specific checks on added lines
        checks = self._get_checks(file_diff.language)
        for check_name, check_fn in checks.items():
            for line_num, content in added_content.items():
                for finding in check_fn(content, file_diff.path, line_num):
                    findings.append(finding)

        return findings

    def _get_checks(self, language: str) -> dict[str, Any]:
        """Get applicable checks for a language."""
        checks: dict[str, Any] = {}

        # Universal checks (apply to all languages)
        checks["hardcoded_secrets"] = _check_hardcoded_secrets
        checks["todo_without_context"] = _check_todo_without_context

        # Language-specific checks
        if language == "python":
            checks["mutable_default"] = _check_python_mutable_default
            checks["bare_except"] = _check_python_bare_except
            checks["print_debug"] = _check_python_print_debug
        elif language in ("javascript", "typescript"):
            checks["console_log"] = _check_js_console_log
            checks["var_usage"] = _check_js_var_usage
        elif language == "solidity":
            checks["unchecked_call"] = _check_solidity_unchecked
            checks["tx_origin"] = _check_solidity_tx_origin

        return checks


# ── Universal checks ───────────────────────────────────────────────────────

_SECRET_PATTERNS = [
    ("api_key", re.compile(r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]([A-Za-z0-9]{20,})['\"]", re.I)),
    ("password", re.compile(r"password\s*[=:]\s*['\"]([^'\"]{8,})['\"]", re.I)),
    ("token", re.compile(r"(?:token|secret)\s*[=:]\s*['\"]([A-Za-z0-9]{20,})['\"]", re.I)),
    ("private_key", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----")),
]


def _check_hardcoded_secrets(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for hardcoded secrets/API keys."""
    findings: list[dict[str, Any]] = []
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(content):
            findings.append({
                "file": file_path,
                "line": line_num,
                "severity": "critical",
                "message": f"Possible hardcoded {name} detected. Use environment variables instead.",
                "checker": "hardcoded_secrets",
                "suggestion": None,
            })
    return findings


def _check_todo_without_context(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for TODO/FIXME without context."""
    findings: list[dict[str, Any]] = []
    todo_match = re.search(r"\b(TODO|FIXME|HACK|XXX)\b\s*(?:\(([^)]+)\))?\s*(.*)", content)
    if todo_match:
        tag = todo_match.group(1)
        author = todo_match.group(2)
        desc = todo_match.group(3).strip()
        if not author and len(desc) < 10:
            findings.append({
                "file": file_path,
                "line": line_num,
                "severity": "style",
                "message": f"{tag} without author or sufficient context. Use format: {tag}(author) description",
                "checker": "todo_without_context",
                "suggestion": None,
            })
    return findings


# ── Python checks ──────────────────────────────────────────────────────────

def _check_python_mutable_default(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for mutable default arguments in Python."""
    findings: list[dict[str, Any]] = []
    if re.search(r"def\s+\w+\(.*=\s*(\[\]|\{\}|set\(\))", content):
        findings.append({
            "file": file_path,
            "line": line_num,
            "severity": "warning",
            "message": "Mutable default argument. Use None and initialize inside the function.",
            "checker": "python_mutable_default",
            "suggestion": None,
        })
    return findings


def _check_python_bare_except(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for bare except clauses."""
    findings: list[dict[str, Any]] = []
    if re.search(r"^\s*except\s*:", content):
        findings.append({
            "file": file_path,
            "line": line_num,
            "severity": "warning",
            "message": "Bare except clause. Catch specific exceptions instead.",
            "checker": "python_bare_except",
            "suggestion": content.replace("except:", "except Exception:") if content.strip() else None,
        })
    return findings


def _check_python_print_debug(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for print() statements (likely debug leftovers)."""
    findings: list[dict[str, Any]] = []
    if re.search(r"^\s*print\s*\(", content) and "print(" not in content.split("#")[0].replace("print(", ""):
        # Heuristic: if there's a print without it being in a __main__ block
        if "if __name__" not in content:
            findings.append({
                "file": file_path,
                "line": line_num,
                "severity": "style",
                "message": "print() statement found. Consider using logging for production code.",
                "checker": "python_print_debug",
                "suggestion": None,
            })
    return findings


# ── JavaScript/TypeScript checks ───────────────────────────────────────────

def _check_js_console_log(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for console.log() statements."""
    findings: list[dict[str, Any]] = []
    if re.search(r"console\.(log|debug|info)\s*\(", content):
        findings.append({
            "file": file_path,
            "line": line_num,
            "severity": "style",
            "message": "console.log() found. Remove debug logging for production.",
            "checker": "js_console_log",
            "suggestion": None,
        })
    return findings


def _check_js_var_usage(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for var usage (prefer let/const)."""
    findings: list[dict[str, Any]] = []
    if re.search(r"^\s*var\s+", content):
        findings.append({
            "file": file_path,
            "line": line_num,
            "severity": "style",
            "message": "var usage detected. Use let or const instead for block scoping.",
            "checker": "js_var_usage",
            "suggestion": content.replace("var ", "const ", 1) if "var " in content else None,
        })
    return findings


# ── Solidity checks ────────────────────────────────────────────────────────

def _check_solidity_unchecked(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for unchecked external calls."""
    findings: list[dict[str, Any]] = []
    if re.search(r"\.call\s*\{", content) and "unchecked" not in content:
        findings.append({
            "file": file_path,
            "line": line_num,
            "severity": "warning",
            "message": "External call without return value check. Consider checking the return value.",
            "checker": "solidity_unchecked_call",
            "suggestion": None,
        })
    return findings


def _check_solidity_tx_origin(content: str, file_path: str, line_num: int) -> list[dict[str, Any]]:
    """Check for tx.origin usage (phishing vulnerability)."""
    findings: list[dict[str, Any]] = []
    if re.search(r"\btx\.origin\b", content):
        findings.append({
            "file": file_path,
            "line": line_num,
            "severity": "critical",
            "message": "tx.origin used for authorization. This is vulnerable to phishing attacks. Use msg.sender instead.",
            "checker": "solidity_tx_origin",
            "suggestion": content.replace("tx.origin", "msg.sender") if "tx.origin" in content else None,
        })
    return findings
