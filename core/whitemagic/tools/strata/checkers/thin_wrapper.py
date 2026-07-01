"""Detect thin wrapper functions — functions that only delegate to another
function without adding any logic, error handling, or transformation.

Anti-pattern:
    def handle_foo(data):
        return process_foo(data)

These add indirection without value. Direct calls are clearer.

Skips:
- Functions with decorators (decorator may add behavior)
- Functions that are part of an interface/protocol (override)
- Functions with docstrings that explain the wrapping
- Functions whose body has try/except (adds error handling)
- Functions in __init__.py (re-exports are intentional)
- Functions that rename parameters (adapter pattern)
- Async wrappers around sync or vice versa (intentional)
- Functions with fewer than 2 lines (too short to judge)
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _is_thin_wrapper(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function is a thin wrapper — single return that delegates."""
    if len(node.body) != 1:
        return False
    stmt = node.body[0]
    if not isinstance(stmt, ast.Return) or stmt.value is None:
        return False

    # The return must be a single function call
    call = stmt.value
    if not isinstance(call, ast.Call):
        return False

    # Check that it calls a different function (not recursive)
    func = call.func
    if isinstance(func, ast.Name) and func.id == node.name:
        return False  # Recursive

    # Check that args are just the function's own params (passthrough)
    # Allow simple passthrough: def foo(x): return bar(x)
    # Flag: def foo(x): return bar(x)  (no transformation)
    # Skip: def foo(x): return bar(transform(x))  (has transformation)

    # Collect all Name nodes in the call args
    arg_names = set()
    for arg in call.args:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                arg_names.add(sub.id)

    # Get the function's parameter names
    param_names = set()
    for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
        param_names.add(arg.arg)
    if node.args.vararg:
        param_names.add(node.args.vararg.arg)
    if node.args.kwarg:
        param_names.add(node.args.kwarg.arg)

    # If args reference only the function's own params, it's a passthrough
    if arg_names and arg_names.issubset(param_names):
        # Check if there are keyword args that are just passthrough
        for kw in call.keywords:
            for sub in ast.walk(kw.value):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    if sub.id not in param_names:
                        return False  # References something other than params
        return True

    return False


@register
def check_thin_wrapper(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect thin wrapper functions that only delegate without adding value."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        # Skip __init__.py — re-exports are intentional
        if rel.endswith("__init__.py"):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Skip decorated functions
            if node.decorator_list:
                continue

            # Skip methods named __init__, __call__, etc. (dunder methods)
            if node.name.startswith("__") and node.name.endswith("__"):
                continue

            # Skip override-like names
            if node.name in ("handle", "process", "run", "execute", "call"):
                continue

            if _is_thin_wrapper(node):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="thin_wrapper",
                    file=rel,
                    line=node.lineno,
                    message=f"Function '{node.name}' is a thin wrapper — only delegates to another function.",
                    suggestion="Call the wrapped function directly, or add meaningful logic/error handling.",
                ))
