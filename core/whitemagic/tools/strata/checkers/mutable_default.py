"""Detect mutable default arguments in function definitions.

Anti-pattern:
    def foo(items=[]):
        items.append(1)
        return items  # accumulates across calls!

    def bar(config={}):
        ...

Better:
    def foo(items=None):
        if items is None:
            items = []
    def bar(config=None):
        if config is None:
            config = {}

Detects: list literals [], dict literals {}, set literals set() as defaults.
Skips: tuple (), frozenset(), string "", int, float, bool, None — these are immutable.
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _is_mutable_default(node: ast.AST) -> bool:
    """Check if a default value is a mutable literal."""
    if isinstance(node, ast.List):
        return True
    if isinstance(node, ast.Dict):
        return True
    if isinstance(node, ast.Set):
        return True
    # set() call
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "set":
            return True
        if isinstance(node.func, ast.Name) and node.func.id == "dict":
            return True
        if isinstance(node.func, ast.Name) and node.func.id == "list":
            return True
    return False


@register
def check_mutable_default(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect mutable default arguments in function definitions."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            args = node.args

            # Check regular args with defaults
            # defaults are aligned to the right end of args
            n_args = len(args.args)
            n_defaults = len(args.defaults)
            if n_defaults > 0:
                start = n_args - n_defaults
                for i, default in enumerate(args.defaults):
                    arg_idx = start + i
                    if _is_mutable_default(default):
                        arg_name = args.args[arg_idx].arg
                        findings.append(Finding(
                            severity=FindingSeverity.WARNING,
                            category="mutable_default",
                            file=rel,
                            line=node.lineno,
                            message=f"Mutable default argument '{arg_name}' — shared across all calls.",
                            suggestion=f"Use '{arg_name}=None' and initialize inside the function body.",
                        ))

            # Check kwonly args with defaults
            for i, default in enumerate(args.kw_defaults):
                if default is not None and _is_mutable_default(default):
                    arg_name = args.kwonlyargs[i].arg
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="mutable_default",
                        file=rel,
                        line=node.lineno,
                        message=f"Mutable default argument '{arg_name}' — shared across all calls.",
                        suggestion=f"Use '{arg_name}=None' and initialize inside the function body.",
                    ))
