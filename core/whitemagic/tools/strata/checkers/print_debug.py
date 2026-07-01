"""Detect print() calls left in production modules.

print() in production code is debug leftover. Use logging instead so output
can be controlled, filtered, and formatted.

Skips:
- Files in tests/ directories (print is acceptable in tests)
- print() inside if __name__ == "__main__" blocks (CLI/demo usage)
- print() inside functions named main/cli/demo (CLI output)
- print() that's inside a try block that catches ImportError (fallback messaging)
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _is_in_main_block(node: ast.AST, tree: ast.AST) -> bool:
    """Check if a node is inside an if __name__ == '__main__' block."""
    for sub in ast.walk(tree):
        if isinstance(sub, ast.If):
            test = sub.test
            if isinstance(test, ast.Compare):
                if isinstance(test.left, ast.Name) and test.left.id == "__name__":
                    for comp in test.comparators:
                        if isinstance(comp, ast.Constant) and comp.value == "__main__":
                            for child in ast.walk(sub):
                                if child is node:
                                    return True
    return False


def _is_in_cli_function(node: ast.AST, tree: ast.AST) -> bool:
    """Check if node is inside a function named main, cli, demo, or _main."""
    _CLI_NAMES = frozenset({"main", "cli", "demo", "_main", "run", "serve"})
    for sub in ast.walk(tree):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if sub.name in _CLI_NAMES or sub.name.startswith("cli_"):
                for child in ast.walk(sub):
                    if child is node:
                        return True
    return False


@register
def check_print_debug(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect print() calls in production modules."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        # Skip test files
        if file_index.is_test_file(py_file):
            continue

        # Skip CLI entry points
        if rel.endswith(("__main__.py", "cli.py", "run_mcp.py", "run_mcp_lean.py")):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Direct print() call
            if isinstance(func, ast.Name) and func.id == "print":
                if _is_in_main_block(node, tree):
                    continue
                if _is_in_cli_function(node, tree):
                    continue
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="print_debug",
                    file=rel,
                    line=node.lineno,
                    message="print() in production module — use logging instead.",
                    suggestion="Replace with logger.debug/info/warning/error(...) for controllable output.",
                ))
