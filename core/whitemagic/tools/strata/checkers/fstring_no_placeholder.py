"""Detect f-strings without any placeholders ({...}).

An f-string with no interpolated expressions is pointless overhead —
it's equivalent to a regular string but with the f-prefix misleading
readers into thinking something is being interpolated.

Example:
    x = f"hello world"          # should be "hello world"
    x = f"constant string"      # should be "constant string"

False positives: f-strings inside __repr__ or format methods that
intentionally use f-prefix for consistency are still flagged, but
the fix is trivial (remove the f-prefix).
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_fstring_no_placeholder(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect f-strings that don't contain any {...} placeholders."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr) and not node.values:
                # Empty f-string: f"" — no values at all
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="fstring_no_placeholder",
                    file=str(py_file.relative_to(project_path)),
                    line=node.lineno,
                    message="f-string with no placeholders — remove the f-prefix.",
                    suggestion='Change f"..." to "..." — no expressions are interpolated.',
                ))
            elif isinstance(node, ast.JoinedStr):
                # Check if all values are constant strings (no FormattedValue)
                has_formatted = any(isinstance(v, ast.FormattedValue) for v in node.values)
                if not has_formatted:
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="fstring_no_placeholder",
                        file=str(py_file.relative_to(project_path)),
                        line=node.lineno,
                        message="f-string with no placeholders — remove the f-prefix.",
                        suggestion='Change f"..." to "..." — no expressions are interpolated.',
                    ))
