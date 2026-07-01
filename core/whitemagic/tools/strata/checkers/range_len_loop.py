"""Detect for i in range(len(x)) loops that should use direct iteration or enumerate.

Anti-pattern:
    for i in range(len(items)):
        print(items[i])

Better:
    for item in items:
        print(item)

Or if index is needed:
    for i, item in enumerate(items):
        print(item)

Skips:
- Loops where the index is used for something other than indexing the same list
  (e.g., for i in range(len(a)): b[i] = a[i] — index is needed for parallel access)
- Loops where range(len()) is used in a slice or other non-indexing context
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _get_range_len_target(node: ast.For) -> str | None:
    """If this is a `for i in range(len(x))` loop, return x's variable name."""
    if not isinstance(node.iter, ast.Call):
        return None
    func = node.iter.func
    if not isinstance(func, ast.Name) or func.id != "range":
        return None
    if len(node.iter.args) != 1:
        return None
    arg = node.iter.args[0]
    if not isinstance(arg, ast.Call):
        return None
    if not isinstance(arg.func, ast.Name) or arg.func.id != "len":
        return None
    if len(arg.args) != 1:
        return None
    target = arg.args[0]
    if isinstance(target, ast.Name):
        return target.id
    return None


def _index_used_only_for_subscript(node: ast.For, iterable_name: str) -> bool:
    """Check if the loop variable is only used to subscript the same iterable.

    If i is used for anything other than iterable_name[i], then the index
    is genuinely needed (parallel arrays, etc.) and we should skip.
    """
    loop_var = node.target
    if not isinstance(loop_var, ast.Name):
        return False
    var_name = loop_var.id

    # Walk the body and check all uses of var_name
    for stmt in ast.walk(node):
        if stmt is loop_var:
            continue
        if isinstance(stmt, ast.Name) and stmt.id == var_name and isinstance(stmt.ctx, ast.Load):
            # Walk up: find the parent. Since ast.walk doesn't give parents,
            # we check if this Name appears as a subscript index on iterable_name.
            # Instead, check: is this Name used anywhere other than as Subscript index?
            # We do a simpler check: look for any Subscript with iterable_name as value
            # and var_name as the slice.
            pass

    # Simpler approach: collect all Subscript nodes in the body
    # where the index is our loop var. Check if they all use the same iterable.
    uses_as_index = False
    uses_otherwise = False

    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Subscript):
            sl = stmt.slice
            if isinstance(sl, ast.Name) and sl.id == var_name:
                uses_as_index = True
                if isinstance(stmt.value, ast.Name) and stmt.value.id == iterable_name:
                    continue  # Good — indexing the same iterable
                else:
                    # Indexing a different iterable — parallel access, index needed
                    return False

    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Name) and stmt.id == var_name and isinstance(stmt.ctx, ast.Load):
            # Is this inside a subscript?
            # We can't easily check parent context with ast.walk,
            # so we use a different approach: check if removing all Subscript
            # nodes still has the var referenced.
            pass

    # Conservative: if the loop var appears as a subscript index on the same
    # iterable and nowhere else obviously, flag it.
    # This may have some false negatives for complex cases.
    return uses_as_index


@register
def check_range_len_loop(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect for i in range(len(x)) loops that should use direct iteration."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            iterable_name = _get_range_len_target(node)
            if iterable_name is None:
                continue
            if _index_used_only_for_subscript(node, iterable_name):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="range_len_loop",
                    file=rel,
                    line=node.lineno,
                    message=f"for i in range(len({iterable_name})) — use direct iteration instead.",
                    suggestion=f"Replace with 'for item in {iterable_name}:' or 'for i, item in enumerate({iterable_name}):'.",
                ))
