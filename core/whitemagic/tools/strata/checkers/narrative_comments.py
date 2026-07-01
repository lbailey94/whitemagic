"""Detect narrative and meta comments — decorative prose that adds noise.

Narrative comments: section headers, phase markers, step-by-step narration
that describes the code's structure rather than explaining why.

Meta comments: comments about the implementation process or agent behavior
rather than the code itself.

Examples:
    # Step 1: Initialize the system
    # Step 2: Process the data
    # === Routers implemented here ===
    # --- Lazy imports ---
    # Phase 1: Setup
    # This was added by the AI agent in session 2

Skips:
- noqa, type: ignore, ruff/mypy/pyright directives
- TODO/FIXME/HACK (covered by todo_style checker)
- Comments inside docstrings
- Shebang/encoding declarations
"""

import ast
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_NARRATIVE_PATTERNS = [
    re.compile(r"^#\s*={3,}.*={3,}\s*$"),  # === Section ===
    re.compile(r"^#\s*-{3,}.*-{3,}\s*$"),  # --- Section ---
    re.compile(r"^#\s*\*{3,}.*\*{3,}\s*$"),  # *** Section ***
    re.compile(r"^#\s*(Step|Phase|Stage)\s+\d+", re.I),
    re.compile(r"^#\s*(Step|Phase|Stage)\s+\w+", re.I),
    re.compile(r"^#\s*-{2,}\s+\w+.*-{2,}\s*$"),  # --- Word ---
    re.compile(r"^#\s*={2,}\s+\w+.*={2,}\s*$"),  # == Word ==
]

_META_PATTERNS = [
    re.compile(r"(added|created|modified|generated|written)\s+by\s+(the\s+)?(AI|agent|assistant|model|GPT|Claude|Copilot)", re.I),
    re.compile(r"(in|during)\s+(session|phase|step|iteration)\s+\d+", re.I),
    re.compile(r"this\s+(code|function|module|file)\s+(was|is)\s+(generated|written|created|produced)", re.I),
    re.compile(r"auto[- ]?generated", re.I),
    re.compile(r"AI[- ]?generated", re.I),
    re.compile(r"placeholder\s+(for|until|to)\s+", re.I),
]

_SKIP_PATTERNS = [
    re.compile(r"noqa", re.I),
    re.compile(r"type:\s*ignore", re.I),
    re.compile(r"pyright:", re.I),
    re.compile(r"mypy:", re.I),
    re.compile(r"ruff:", re.I),
    re.compile(r"TODO|FIXME|HACK|XXX|BUG", re.I),
]


@register
def check_narrative_comments(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect narrative and meta comments that add noise without value."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))
        if file_index.is_test_file(py_file):
            continue

        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = source.splitlines()

        # Build set of line numbers inside string literals
        string_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        string_lines.add(ln)

        for i, line in enumerate(lines, start=1):
            if i in string_lines:
                continue
            stripped = line.lstrip()
            if not stripped.startswith("#"):
                continue
            if i <= 2 and (stripped.startswith("#!") or "coding" in stripped or "encoding" in stripped):
                continue

            full = stripped.strip()
            skip = False
            for pat in _SKIP_PATTERNS:
                if pat.search(full):
                    skip = True
                    break
            if skip:
                continue

            for pat in _NARRATIVE_PATTERNS:
                if pat.match(full):
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="narrative_comment",
                        file=rel,
                        line=i,
                        message="Narrative comment — decorative separator or step marker adds noise.",
                        suggestion="Remove the decorative comment or replace with a brief 'why' explanation.",
                    ))
                    break

            for pat in _META_PATTERNS:
                if pat.search(full):
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="meta_comment",
                        file=rel,
                        line=i,
                        message="Meta comment — discusses the implementation process rather than the code.",
                        suggestion="Remove the meta comment. Code should explain itself, not its history.",
                    ))
                    break
