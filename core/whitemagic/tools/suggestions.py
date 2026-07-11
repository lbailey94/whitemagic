"""Improvement suggestion system — generate actionable fix suggestions for findings.

Takes findings from STRATA/diff analysis and generates:
    - GitHub-formatted suggestion blocks (```suggestion ... ```)
    - Explanation of why the change is recommended
    - Severity ranking and filtering
    - Auto-resolve tracking (suppress suggestions when fix is pushed)

Usage:
    from whitemagic.tools.suggestions import SuggestionEngine

    engine = SuggestionEngine()
    suggestions = engine.generate(finding)
    formatted = engine.format_for_github(suggestions)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"critical": 0, "warning": 1, "style": 2, "nitpick": 3}


@dataclass
class Suggestion:
    """A code improvement suggestion."""
    file: str
    line: int
    severity: str
    title: str
    explanation: str
    suggested_code: str | None = None
    checker: str = ""
    auto_fixable: bool = False
    confidence: float = 0.8


class SuggestionEngine:
    """Generate actionable improvement suggestions from code findings.

    The engine maps checker names to suggestion generators that produce
    human-readable explanations and, where possible, automated fix code
    formatted as GitHub suggestion blocks.
    """

    def __init__(self) -> None:
        self._generators: dict[str, Any] = {
            "hardcoded_secrets": _suggest_env_var,
            "todo_without_context": _suggest_todo_format,
            "python_mutable_default": _suggest_mutable_default_fix,
            "python_bare_except": _suggest_specific_except,
            "python_print_debug": _suggest_logging,
            "js_console_log": _suggest_remove_console,
            "js_var_usage": _suggest_let_const,
            "solidity_unchecked_call": _suggest_check_return,
            "solidity_tx_origin": _suggest_msg_sender,
        }
        self._resolved: set[str] = set()

    def generate(self, finding: dict[str, Any]) -> Suggestion:
        """Generate a suggestion for a single finding.

        Args:
            finding: Finding dict with file, line, severity, message, checker, suggestion.

        Returns:
            Suggestion with explanation and suggested code.
        """
        checker = finding.get("checker", "")
        gen = self._generators.get(checker, _generic_suggestion)
        return gen(finding)

    def generate_batch(self, findings: list[dict[str, Any]]) -> list[Suggestion]:
        """Generate suggestions for multiple findings, sorted by severity."""
        suggestions = [self.generate(f) for f in findings]
        suggestions.sort(key=lambda s: SEVERITY_RANK.get(s.severity, 3))
        return suggestions

    def format_for_github(self, suggestions: list[Suggestion]) -> str:
        """Format suggestions as a GitHub review comment body.

        Produces markdown with suggestion blocks that GitHub renders as
        "Apply suggestion" buttons.
        """
        if not suggestions:
            return "No suggestions. Code looks clean!"

        parts: list[str] = ["## Code Review Suggestions", ""]

        critical = [s for s in suggestions if s.severity == "critical"]
        warnings = [s for s in suggestions if s.severity == "warning"]
        styles = [s for s in suggestions if s.severity in ("style", "nitpick")]

        if critical:
            parts.append(f"### Critical ({len(critical)})")
            parts.append("")
            for s in critical:
                parts.append(self._format_single(s))
                parts.append("")

        if warnings:
            parts.append(f"### Warnings ({len(warnings)})")
            parts.append("")
            for s in warnings:
                parts.append(self._format_single(s))
                parts.append("")

        if styles:
            parts.append(f"### Style ({len(styles)})")
            parts.append("")
            for s in styles:
                parts.append(self._format_single(s))
                parts.append("")

        parts.append("---")
        parts.append("*Powered by [WhiteMagic](https://github.com/lbailey94/whitemagic) — memory-augmented code review*")

        return "\n".join(parts)

    def _format_single(self, s: Suggestion) -> str:
        """Format a single suggestion as markdown."""
        lines = [
            f"**{s.title}** — `{s.file}:{s.line}`",
            "",
            s.explanation,
        ]
        if s.suggested_code:
            lines.append("")
            lines.append("```suggestion")
            lines.append(s.suggested_code)
            lines.append("```")
        return "\n".join(lines)

    def mark_resolved(self, file: str, line: int, checker: str) -> None:
        """Mark a suggestion as resolved (fix was pushed)."""
        key = f"{file}:{line}:{checker}"
        self._resolved.add(key)
        logger.info("Marked resolved: %s", key)

    def is_resolved(self, file: str, line: int, checker: str) -> bool:
        """Check if a suggestion was already resolved."""
        return f"{file}:{line}:{checker}" in self._resolved

    def filter_unresolved(self, suggestions: list[Suggestion]) -> list[Suggestion]:
        """Filter out suggestions that were already resolved."""
        return [
            s for s in suggestions
            if not self.is_resolved(s.file, s.line, s.checker)
        ]


# ── Suggestion generators ──────────────────────────────────────────────────

def _suggest_env_var(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "critical"),
        title="Hardcoded secret detected",
        explanation=(
            "Hardcoding API keys, passwords, or tokens in source code is a "
            "security risk. Secrets should be loaded from environment variables "
            "or a secrets manager.\n\n"
            "**Fix:** Replace the hardcoded value with an environment variable lookup."
        ),
        suggested_code=None,
        checker=finding.get("checker", "hardcoded_secrets"),
        auto_fixable=False,
        confidence=0.95,
    )


def _suggest_todo_format(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "style"),
        title="TODO lacks context",
        explanation=(
            "TODO/FIXME comments without an author or description make it hard "
            "to track and resolve them. Use the format: `TODO(author) description`."
        ),
        checker=finding.get("checker", "todo_without_context"),
        auto_fixable=False,
        confidence=0.7,
    )


def _suggest_mutable_default_fix(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "warning"),
        title="Mutable default argument",
        explanation=(
            "Using mutable objects (list, dict, set) as default arguments in Python "
            "is a common pitfall — the same object is shared across all calls.\n\n"
            "**Fix:** Use `None` as the default and initialize inside the function body."
        ),
        suggested_code=None,
        checker=finding.get("checker", "python_mutable_default"),
        auto_fixable=True,
        confidence=0.9,
    )


def _suggest_specific_except(finding: dict[str, Any]) -> Suggestion:
    suggested = finding.get("suggestion")
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "warning"),
        title="Bare except clause",
        explanation=(
            "Bare `except:` catches everything including `SystemExit`, `KeyboardInterrupt`, "
            "and `GeneratorExit`. This can mask real errors and make debugging difficult.\n\n"
            "**Fix:** Catch specific exceptions, or at minimum use `except Exception:`."
        ),
        suggested_code=suggested,
        checker=finding.get("checker", "python_bare_except"),
        auto_fixable=True,
        confidence=0.95,
    )


def _suggest_logging(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "style"),
        title="print() in production code",
        explanation=(
            "`print()` statements in production code can't be filtered, formatted, or "
            "routed to different outputs. Use the `logging` module instead for "
            "structured, configurable log output."
        ),
        suggested_code=None,
        checker=finding.get("checker", "python_print_debug"),
        auto_fixable=False,
        confidence=0.6,
    )


def _suggest_remove_console(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "style"),
        title="console.log() in production code",
        explanation=(
            "`console.log()` statements should be removed before deploying to production. "
            "They can leak sensitive data and impact performance.\n\n"
            "**Fix:** Remove the console.log statement or replace with a proper logging library."
        ),
        checker=finding.get("checker", "js_console_log"),
        auto_fixable=True,
        confidence=0.8,
    )


def _suggest_let_const(finding: dict[str, Any]) -> Suggestion:
    suggested = finding.get("suggestion")
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "style"),
        title="var should be let/const",
        explanation=(
            "`var` declarations are function-scoped and can lead to unexpected behavior. "
            "`let` and `const` are block-scoped and are the modern standard."
        ),
        suggested_code=suggested,
        checker=finding.get("checker", "js_var_usage"),
        auto_fixable=True,
        confidence=0.9,
    )


def _suggest_check_return(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "warning"),
        title="Unchecked external call",
        explanation=(
            "External calls in Solidity can fail silently. Not checking the return value "
            "can lead to silent failures that compromise contract logic.\n\n"
            "**Fix:** Check the return value with `require(call())` or use `try/catch`."
        ),
        checker=finding.get("checker", "solidity_unchecked_call"),
        auto_fixable=False,
        confidence=0.85,
    )


def _suggest_msg_sender(finding: dict[str, Any]) -> Suggestion:
    suggested = finding.get("suggestion")
    return Suggestion(
        file=finding["file"],
        line=finding["line"],
        severity=finding.get("severity", "critical"),
        title="tx.origin authorization vulnerability",
        explanation=(
            "Using `tx.origin` for authorization is a well-known phishing vulnerability. "
            "An attacker can trick a user into calling a malicious contract that then "
            "calls your contract, bypassing the authorization check.\n\n"
            "**Fix:** Always use `msg.sender` for authorization checks."
        ),
        suggested_code=suggested,
        checker=finding.get("checker", "solidity_tx_origin"),
        auto_fixable=True,
        confidence=0.98,
    )


def _generic_suggestion(finding: dict[str, Any]) -> Suggestion:
    return Suggestion(
        file=finding.get("file", ""),
        line=finding.get("line", 0),
        severity=finding.get("severity", "warning"),
        title=finding.get("message", "Code issue")[:80],
        explanation=finding.get("message", "A potential issue was found in this code."),
        suggested_code=finding.get("suggestion"),
        checker=finding.get("checker", "generic"),
        auto_fixable=bool(finding.get("suggestion")),
        confidence=0.5,
    )
