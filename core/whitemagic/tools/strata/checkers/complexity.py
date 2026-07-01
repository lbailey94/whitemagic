"""Detect complexity issues: oversized files, oversized functions, deep nesting,
and functions with too many parameters.

Thresholds (configurable in future):
- File too large: > 500 lines
- Function too long: > 50 lines
- Deep nesting: > 5 levels
- Too many params: > 7

Skips:
- Test files (test functions are naturally long)
- __init__.py files (usually just imports and exports)
- Files in archive/ directories
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_FILE_TOO_LARGE = 500
_FUNC_TOO_LONG = 50
_DEEP_NESTING = 5
_TOO_MANY_PARAMS = 7


def _count_lines(node: ast.AST) -> int:
    """Count the number of lines a node spans."""
    if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
        return (node.end_lineno or node.lineno) - node.lineno + 1
    return 0


def _count_params(args: ast.arguments) -> int:
    """Count total parameters including positional-only, keyword-only, *args, **kwargs."""
    count = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    return count


def _max_depth(node: ast.AST, current_depth: int = 0) -> int:
    """Find maximum nesting depth of control flow statements."""
    max_d = current_depth
    control_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
                     ast.Try, ast.ExceptHandler, ast.Match)
    for child in ast.iter_child_nodes(node):
        if isinstance(child, control_types):
            d = _max_depth(child, current_depth + 1)
            if d > max_d:
                max_d = d
        else:
            d = _max_depth(child, current_depth)
            if d > max_d:
                max_d = d
    return max_d


@register
def check_complexity(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect complexity issues: oversized files, functions, deep nesting, too many params."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        is_test = file_index.is_test_file(py_file)
        is_init = rel.endswith("__init__.py")

        # File too large
        if not is_init:
            try:
                line_count = sum(1 for _ in py_file.open(encoding="utf-8", errors="replace"))
            except OSError:
                line_count = 0
            if line_count > _FILE_TOO_LARGE:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="file_too_large",
                    file=rel,
                    line=1,
                    message=f"File has {line_count} lines (threshold: {_FILE_TOO_LARGE}).",
                    suggestion="Consider splitting into smaller modules.",
                ))

        if is_test:
            continue  # Skip function-level checks for test files

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = _count_lines(node)

                if func_lines > _FUNC_TOO_LONG:
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="function_too_long",
                        file=rel,
                        line=node.lineno,
                        message=f"Function '{node.name}' is {func_lines} lines (threshold: {_FUNC_TOO_LONG}).",
                        suggestion="Consider extracting helper functions or simplifying logic.",
                    ))

                # Too many params
                n_params = _count_params(node.args)
                if n_params > _TOO_MANY_PARAMS:
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="too_many_params",
                        file=rel,
                        line=node.lineno,
                        message=f"Function '{node.name}' has {n_params} parameters (threshold: {_TOO_MANY_PARAMS}).",
                        suggestion="Consider using a config object or dataclass to group parameters.",
                    ))

                # Deep nesting
                depth = _max_depth(node)
                if depth > _DEEP_NESTING:
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="deep_nesting",
                        file=rel,
                        line=node.lineno,
                        message=f"Function '{node.name}' has {depth} levels of nesting (threshold: {_DEEP_NESTING}).",
                        suggestion="Extract nested logic into helper functions or use early returns.",
                    ))
