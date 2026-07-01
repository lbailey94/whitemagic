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

        # Pre-collect JoinedStr nodes that are format_spec of a FormattedValue.
        # In Python 3.12+, format specs like {x:.0f} are parsed as separate
        # JoinedStr nodes — these are NOT f-strings without placeholders.
        format_spec_ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FormattedValue) and node.format_spec:
                if isinstance(node.format_spec, ast.JoinedStr):
                    format_spec_ids.add(id(node.format_spec))

        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr):
                continue
            # Skip format_spec JoinedStr nodes (Python 3.12+)
            if id(node) in format_spec_ids:
                continue
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
