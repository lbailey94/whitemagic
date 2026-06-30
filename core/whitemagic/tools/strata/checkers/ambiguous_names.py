"""Detect ambiguous single-letter variable names.

PEP 8 recommends avoiding lowercase `l` (confusable with `1`), 
`O` (confusable with `0`), and `I` (confusable with `l` and `1`).

These are real readability hazards that aislop catches but STRATA
previously missed.
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_AMBIGUOUS_NAMES = frozenset({"l", "O", "I"})


@register
def check_ambiguous_variable_names(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect variable assignments using ambiguous single-letter names."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in _AMBIGUOUS_NAMES:
                        findings.append(Finding(
                            severity=FindingSeverity.WARNING,
                            category="ambiguous_variable",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Ambiguous variable name '{target.id}' — easily confused with numbers.",
                            suggestion=f"Rename to a more descriptive name (e.g. 'lower', 'upper', 'index').",
                        ))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    if arg.arg in _AMBIGUOUS_NAMES:
                        findings.append(Finding(
                            severity=FindingSeverity.WARNING,
                            category="ambiguous_variable",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Ambiguous parameter name '{arg.arg}' — easily confused with numbers.",
                            suggestion=f"Rename to a more descriptive name.",
                        ))
