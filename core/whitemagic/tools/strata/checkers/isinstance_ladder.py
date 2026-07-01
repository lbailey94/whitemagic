"""Detect isinstance() ladders — repeated isinstance() checks that should use
a handler map or polymorphism.

Anti-pattern:
    if isinstance(x, int):
        handle_int(x)
    elif isinstance(x, float):
        handle_float(x)
    elif isinstance(x, str):
        handle_str(x)
    elif isinstance(x, list):
        handle_list(x)

Better:
    handlers = {int: handle_int, float: handle_float, str: handle_str, list: handle_list}
    handler = handlers.get(type(x))
    if handler:
        handler(x)

Detects: 3+ consecutive if/elif branches where each condition is an
isinstance() call. Reports the first branch only.
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _is_isinstance_call(node: ast.AST) -> bool:
    """Check if a node is an isinstance() call."""
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
            return True
    return False


def _count_isinstance_branches(node: ast.If) -> int:
    """Count consecutive if/elif branches that use isinstance()."""
    count = 0
    current = node
    while current is not None:
        if isinstance(current, ast.If) and _is_isinstance_call(current.test):
            count += 1
            # Move to first elif (orelse with single If)
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
            else:
                break
        else:
            break
    return count


@register
def check_isinstance_ladder(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect isinstance() ladders with 3+ branches that should be a handler map."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        # Track lines we've already reported (to avoid duplicate findings for same ladder)
        reported_lines: set[int] = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            if node.lineno in reported_lines:
                continue
            if not _is_isinstance_call(node.test):
                continue

            branch_count = _count_isinstance_branches(node)
            if branch_count >= 3:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="isinstance_ladder",
                    file=rel,
                    line=node.lineno,
                    message=f"isinstance() ladder with {branch_count} branches — consider a handler map.",
                    suggestion="Use a dict mapping types to handler functions, or use polymorphism.",
                ))
                # Mark all branches as reported
                current = node
                while current is not None:
                    reported_lines.add(current.lineno)
                    if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                        current = current.orelse[0]
                    else:
                        break
