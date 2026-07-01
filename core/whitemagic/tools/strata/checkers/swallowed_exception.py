"""Detect swallowed exceptions — empty catch blocks or catch blocks that only
assign to a variable without logging or re-raising.

Swallowed exceptions hide bugs silently. The error is caught and discarded
with no logging, no re-raise, and no meaningful recovery.

Patterns detected:
- except Exception: pass
- except Exception as e: pass
- except Exception: (empty body, only assignments)
- except Exception as e: result = None  (no logging)

Skips false positives:
- Handlers that log (even without re-raising) — that's graceful degradation
- Handlers that return error envelopes — that's the dispatch pattern
- Handlers that re-raise — that's error logging
- Handlers inside import-only try blocks — optional dependency pattern
- Handlers that set flags (e.g. _AVAILABLE = False) — feature detection
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _handler_is_empty(handler: ast.ExceptHandler) -> bool:
    """Check if handler body is only pass or equivalent."""
    if len(handler.body) == 1:
        stmt = handler.body[0]
        if isinstance(stmt, ast.Pass):
            return True
        # `...` literal as statement
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
            return True
    return False


def _handler_only_assigns(handler: ast.ExceptHandler) -> bool:
    """Check if handler body only contains assignments (no logging, no raise)."""
    has_log = False
    has_raise = False
    for stmt in ast.walk(handler):
        if isinstance(stmt, ast.Raise):
            has_raise = True
        elif isinstance(stmt, ast.Call):
            func = stmt.func
            if isinstance(func, ast.Attribute) and func.attr in (
                "debug", "info", "warning", "warn", "error", "critical", "exception", "log",
            ):
                has_log = True
            # Also check print() as a form of logging
            if isinstance(func, ast.Name) and func.id == "print":
                has_log = True
    return not has_log and not has_raise


def _handler_sets_flag(handler: ast.ExceptHandler) -> bool:
    """Check if handler only sets boolean/None flags (feature detection pattern)."""
    for stmt in handler.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id.upper() == target.id:
                    # ALL_CAPS variable = feature flag pattern
                    return True
        elif isinstance(stmt, ast.Pass):
            continue
        else:
            return False
    return len(handler.body) > 0


def _try_has_importerror_handler(try_node: ast.Try) -> bool:
    for handler in try_node.handlers:
        if handler.type is None:
            continue
        if isinstance(handler.type, ast.Name) and handler.type.id == "ImportError":
            return True
        if isinstance(handler.type, ast.Tuple):
            for elt in handler.type.elts:
                if isinstance(elt, ast.Name) and elt.id == "ImportError":
                    return True
    return False


def _try_body_is_import_only(try_node: ast.Try) -> bool:
    for stmt in try_node.body:
        if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
            return False
    return len(try_node.body) > 0


@register
def check_swallowed_exception(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect swallowed exceptions — catch blocks that silently discard errors."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue

            # Skip optional import patterns
            if _try_body_is_import_only(node) or _try_has_importerror_handler(node):
                continue

            for handler in node.handlers:
                # Skip bare except (covered by bare_except checker)
                if handler.type is None:
                    continue

                # Empty handler (pass or ...)
                if _handler_is_empty(handler):
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="swallowed_exception",
                        file=rel,
                        line=handler.lineno,
                        message="Swallowed exception — empty catch block silently discards errors.",
                        suggestion="Log the exception, re-raise it, or handle it explicitly.",
                    ))
                    continue

                # Non-empty but no logging and no re-raise
                if _handler_only_assigns(handler) and not _handler_sets_flag(handler):
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="swallowed_exception",
                        file=rel,
                        line=handler.lineno,
                        message="Swallowed exception — catch block assigns values but never logs or re-raises.",
                        suggestion="Add logging (logger.exception(...)) or re-raise to surface the error.",
                    ))
