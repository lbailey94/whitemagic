"""Detect repetitive dispatch ladder patterns.

A dispatch ladder is a long if/elif chain that maps a string key to a
handler function. These are common in MCP tool dispatchers and can
often be replaced with a dictionary lookup.

Example:
    if action == "create":
        return handle_create(params)
    elif action == "read":
        return handle_read(params)
    elif action == "update":
        return handle_update(params)
    elif action == "delete":
        return handle_delete(params)
    # ... 10+ more branches

Better:
    _HANDLERS = {"create": handle_create, "read": handle_read, ...}
    handler = _HANDLERS.get(action)
    if handler:
        return handler(params)

WhiteMagic uses dispatch ladders intentionally in some places (lazy
imports, conditional routing), so this checker flags ladders with 8+
branches as INFO severity.
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_THRESHOLD = 8  # Minimum number of elif branches to flag


@register
def check_repetitive_dispatch(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect long if/elif chains that could be replaced with a dict dispatch."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        # Track If nodes that are elif branches of a parent — skip them
        elif_nodes: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    elif_nodes.add(id(node.orelse[0]))

        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            # Skip elif branches — only flag the outermost if
            if id(node) in elif_nodes:
                continue

            # Count the length of the elif chain
            count = 0
            current = node
            while isinstance(current, ast.If):
                count += 1
                if current.orelse and len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                    current = current.orelse[0]
                else:
                    break

            if count >= _THRESHOLD:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="repetitive_dispatch",
                    file=str(py_file.relative_to(project_path)),
                    line=node.lineno,
                    message=f"Long if/elif chain ({count} branches) — consider a dict dispatch table.",
                    suggestion="Replace with _HANDLERS = {key: handler, ...} and handler = _HANDLERS.get(action).",
                ))
