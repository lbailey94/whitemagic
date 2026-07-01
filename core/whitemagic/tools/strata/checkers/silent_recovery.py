"""Detect silent recovery — catch blocks that log but don't include the caught
error in the log message, then continue without re-raising.

This is subtler than swallowed exceptions. The handler does log something,
but the actual exception is discarded — making debugging impossible because
the log message doesn't tell you what went wrong.

Example:
    try:
        do_something()
    except Exception:
        logger.warning("Something went wrong")  # What went wrong??
        return None

vs. correct:
    try:
        do_something()
    except Exception as e:
        logger.warning("Something went wrong: %s", e)
        return None

Skips:
- Handlers that don't bind the exception (no 'as e') — can't include it
- Handlers that re-raise
- Handlers that return error envelopes (dispatch pattern)
- Import-only try blocks
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


_LOG_ATTRS = frozenset({
    "debug", "info", "warning", "warn", "error", "critical", "exception", "log",
})


def _handler_has_raise(handler: ast.ExceptHandler) -> bool:
    for stmt in ast.walk(handler):
        if isinstance(stmt, ast.Raise):
            return True
    return False


def _handler_returns_envelope(handler: ast.ExceptHandler) -> bool:
    for stmt in ast.walk(handler):
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            if isinstance(stmt.value, ast.Dict):
                for key in stmt.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value == "status":
                        return True
    return False


def _try_body_is_import_only(try_node: ast.Try) -> bool:
    for stmt in try_node.body:
        if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
            return False
    return len(try_node.body) > 0


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


def _log_call_uses_exception_var(call: ast.Call, exc_name: str) -> bool:
    """Check if a logging call references the exception variable."""
    for arg in call.args:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Name) and sub.id == exc_name:
                return True
    for kw in call.keywords:
        if kw.arg == "exc_info" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


@register
def check_silent_recovery(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect catch blocks that log without including the caught exception."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            if _try_body_is_import_only(node) or _try_has_importerror_handler(node):
                continue

            for handler in node.handlers:
                # Must bind the exception (as e) — otherwise can't include it
                if handler.name is None:
                    continue
                # Skip if re-raises or returns envelope
                if _handler_has_raise(handler):
                    continue
                if _handler_returns_envelope(handler):
                    continue

                # Find logging calls in the handler
                for stmt in ast.walk(handler):
                    if isinstance(stmt, ast.Call):
                        func = stmt.func
                        if isinstance(func, ast.Attribute) and func.attr in _LOG_ATTRS:
                            if not _log_call_uses_exception_var(stmt, handler.name):
                                findings.append(Finding(
                                    severity=FindingSeverity.WARNING,
                                    category="silent_recovery",
                                    file=rel,
                                    line=handler.lineno,
                                    message=f"Silent recovery — logs without including caught exception '{handler.name}'.",
                                    suggestion=f"Add '{handler.name}' to the log message or use exc_info=True.",
                                ))
                                break  # One finding per handler
