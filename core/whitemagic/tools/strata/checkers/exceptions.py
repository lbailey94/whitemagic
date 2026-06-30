import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _try_body_is_import_only(try_node: ast.Try) -> bool:
    """Check if a try block body contains only import statements (optional dependency pattern)."""
    for stmt in try_node.body:
        if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
            return False
    return len(try_node.body) > 0


def _handler_logs_and_reraises(handler: ast.ExceptHandler) -> bool:
    """Check if an except handler only logs and re-raises (error logging pattern)."""
    has_raise = False
    has_log = False
    for stmt in ast.walk(handler):
        if isinstance(stmt, ast.Raise):
            has_raise = True
        elif isinstance(stmt, ast.Call):
            # Check for logging calls
            func = stmt.func
            if isinstance(func, ast.Attribute) and func.attr in (
                "debug",
                "info",
                "warning",
                "warn",
                "error",
                "critical",
                "exception",
                "log",
            ):
                has_log = True
    return has_raise and has_log


def _try_has_importerror_handler(try_node: ast.Try) -> bool:
    """Check if a try block has an 'except ImportError' handler (explicit optional import)."""
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


def _handler_returns_error_envelope(handler: ast.ExceptHandler) -> bool:
    """Check if an except handler returns a dict with 'status' key (error envelope pattern)."""
    for stmt in ast.walk(handler):
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            # Check for dict return with "status" key
            if isinstance(stmt.value, ast.Dict):
                for key in stmt.value.keys:
                    if (
                        isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and key.value == "status"
                    ):
                        return True
            # Check for dict() call with status key
            if (
                isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == "dict"
            ):
                for kw in stmt.value.keywords:
                    if kw.arg == "status":
                        return True
    return False


def _handler_logs_and_continues(handler: ast.ExceptHandler) -> bool:
    """Check if an except handler logs the error and continues (graceful degradation pattern).

    This is the WhiteMagic standard pattern: catch broad Exception, log it, return a
    default value (None, empty collection, False) or just fall through. This is
    intentional for systems that must keep running even when sub-components fail.
    """
    has_log = False
    has_raise = False
    for stmt in ast.walk(handler):
        if isinstance(stmt, ast.Raise):
            has_raise = True
        elif isinstance(stmt, ast.Call):
            func = stmt.func
            if isinstance(func, ast.Attribute) and func.attr in (
                "debug",
                "info",
                "warning",
                "warn",
                "error",
                "critical",
                "exception",
                "log",
            ):
                has_log = True
    # Only skip if it logs AND does NOT re-raise (log+continue, not log+rereraise)
    return has_log and not has_raise


@register
def check_bare_except(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect bare/blank except clauses and overly broad Exception catches.

    Skips false positives:
    - try blocks containing only imports (graceful degradation / optional dependencies)
    - except handlers that log and re-raise (error logging pattern)
    - try blocks that also have ImportError handlers (explicit optional import pattern)
    - except handlers that return error envelope dicts (dispatch handler pattern)
    """
    # Directories where broad except is intentional (graceful degradation / safety loops)
    _BROAD_EXCEPT_SKIP_DIRS = (
        "optimization/",
        "core/evolution/",
        "core/dreaming/",
        "cli/",
        "interfaces/",
    )

    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        rel = py_file.relative_to(project_path)
        rel_str = str(rel)
        # Skip bridge/wrapper files — MCP bridge handlers must catch all exceptions
        # to return the stable JSON envelope per AGENTS.md
        if "bridge/" in rel_str or "gana_wrappers" in rel_str or "handlers/" in rel_str:
            # Still check for bare except: in bridge files (those are always wrong)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="bare_except",
                            file=str(rel),
                            line=node.lineno,
                            message="Bare 'except:' clause catches KeyboardInterrupt and SystemExit.",
                            suggestion="Use 'except Exception:' or be more specific.",
                        )
                    )
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    # bare except:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="bare_except",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message="Bare 'except:' clause catches KeyboardInterrupt and SystemExit.",
                            suggestion="Use 'except Exception:' or be more specific.",
                        )
                    )
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    # overly broad except Exception:
                    # Skip if parent try block is import-only (graceful degradation)
                    parent_try = None
                    for sub in ast.walk(tree):
                        if isinstance(sub, ast.Try):
                            for handler in sub.handlers:
                                if handler is node:
                                    parent_try = sub
                                    break
                    if parent_try:
                        if _try_body_is_import_only(parent_try):
                            continue
                        if _try_has_importerror_handler(parent_try):
                            continue
                    # Skip if handler logs and re-raises
                    if _handler_logs_and_reraises(node):
                        continue
                    # Skip if handler returns error envelope (dispatch handler pattern)
                    if _handler_returns_error_envelope(node):
                        continue
                    # Skip if handler logs and continues without re-raising (graceful degradation)
                    if _handler_logs_and_continues(node):
                        continue
                    # Skip files in directories where broad except is intentional
                    if any(skip_dir in rel_str for skip_dir in _BROAD_EXCEPT_SKIP_DIRS):
                        continue
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="broad_except",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message="Overly broad 'except Exception:' may hide bugs.",
                            suggestion="Catch specific exceptions where possible.",
                        )
                    )
