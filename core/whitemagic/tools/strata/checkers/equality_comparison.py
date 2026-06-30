"""Detect equality comparisons to True/False/None using == or !=.

PEP 8 recommends using `is` / `is not` for comparisons to singletons
(True, False, None) rather than `==` / `!=`.

Example:
    if x == True:    # should be: if x is True:
    if x == False:   # should be: if x is False:
    if x != None:    # should be: if x is not None:

This is both a style issue and a correctness issue — `==` can be
overridden by __eq__ and may not behave as expected for singletons.
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_equality_comparison(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect == True, == False, == None, != True, != False, != None."""
    _SINGLETON_NAMES = frozenset({"True", "False", "None"})

    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                    # Check left side — use type+identity check to avoid
                    # 0 == False and 1 == True matching (Python equality quirk)
                    left = node.left
                    if isinstance(left, ast.Constant) and isinstance(left.value, bool | type(None)):
                        if left.value is True or left.value is False or left.value is None:
                            op_str = "==" if isinstance(node.ops[0], ast.Eq) else "!="
                            val = repr(left.value)
                            findings.append(Finding(
                                severity=FindingSeverity.WARNING,
                                category="equality_comparison",
                                file=str(py_file.relative_to(project_path)),
                                line=node.lineno,
                                message=f"Use 'is'/'is not' instead of '{op_str}' for comparison to {val}.",
                                suggestion=f"Replace '{op_str} {val}' with 'is{'' if isinstance(node.ops[0], ast.Eq) else ' not'} {val}'.",
                            ))
                    # Check right side (comparators)
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, bool | type(None)):
                            if comparator.value is True or comparator.value is False or comparator.value is None:
                                op_str = "==" if isinstance(node.ops[0], ast.Eq) else "!="
                                val = repr(comparator.value)
                                findings.append(Finding(
                                    severity=FindingSeverity.WARNING,
                                    category="equality_comparison",
                                    file=str(py_file.relative_to(project_path)),
                                    line=node.lineno,
                                    message=f"Use 'is'/'is not' instead of '{op_str}' for comparison to {val}.",
                                    suggestion=f"Replace '{op_str} {val}' with 'is{'' if isinstance(node.ops[0], ast.Eq) else ' not'} {val}'.",
                                ))
