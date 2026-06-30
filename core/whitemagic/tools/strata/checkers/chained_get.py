"""Detect chained .get() patterns that could use a single dict lookup.

Multiple chained .get() calls on the same object are a sign of
overly defensive coding — each .get() adds a default, but the chain
can often be simplified.

Example:
    val = data.get("a", {}).get("b", {}).get("c", "default")

This pattern is common in JSON parsing but can mask missing keys
that should be explicit errors. Flagged as INFO since it's a style
issue, not a bug.

Threshold: 3+ chained .get() calls.
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_THRESHOLD = 3  # Minimum chained .get() calls to flag


def _count_chained_gets(node: ast.AST) -> int:
    """Count the number of chained .get() calls in a Call expression."""
    count = 0
    current = node
    while isinstance(current, ast.Call):
        if isinstance(current.func, ast.Attribute) and current.func.attr == "get":
            count += 1
            current = current.func.value
        else:
            break
    return count


@register
def check_chained_get(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect deeply chained .get() patterns."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                depth = _count_chained_gets(node)
                if depth >= _THRESHOLD:
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="chained_get",
                        file=str(py_file.relative_to(project_path)),
                        line=node.lineno,
                        message=f"Deeply chained .get() ({depth} levels) — consider explicit key access or a helper.",
                        suggestion="Use a try/except KeyError or a dedicated nested-lookup helper for clarity.",
                    ))
