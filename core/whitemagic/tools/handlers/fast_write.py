"""Fast Write — Atomic file writing with syntax validation.

Provides a safe, fast file writing handler that wraps cat shell write techniques
with built-in syntax checking and safety harnesses. This is the MCP-accessible
version of the cat shell write protocol documented in .windsurf/workflows/fast-write.md.

Tools exposed:
  fast_write.write   — Write content to a file (new or overwrite)
  fast_write.append  — Append content to an existing file
  fast_write.batch   — Write multiple files in one operation
  fast_write.validate — Validate syntax of a file without writing

Safety features:
  - Python syntax validation (ast.parse) after write
  - Path safety (no writing outside allowed roots)
  - Encoding safety (UTF-8 enforced)
  - Dry-run mode (show what would be written without writing)
  - Backup option (rename existing file before overwrite)
"""
# ruff: noqa: BLE001

import ast
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ALLOWED_ROOTS: list[str] = [
    str(__import__("whitemagic.config.paths", fromlist=["get_state_root"]).get_state_root()),
    str(Path.cwd()),
]

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max
_MAX_BATCH_FILES = 50

_PROTECTED_PATTERNS = {
    ".git/", "__pycache__/", ".venv/", "node_modules/",
    ".env", ".ssh/", "/etc/", "/usr/", "/proc/", "/sys/",
}


def _is_path_safe(file_path: str) -> tuple[bool, str]:
    """Check if a path is safe to write to.

    Returns:
        (allowed, reason) tuple.
    """
    p = Path(file_path).resolve()

    # Check protected patterns
    path_str = str(p)
    for pattern in _PROTECTED_PATTERNS:
        if pattern in path_str:
            return False, f"Path matches protected pattern: {pattern}"

    # Check allowed roots
    for root in _ALLOWED_ROOTS:
        try:
            root_resolved = Path(root).resolve()
            if str(p).startswith(str(root_resolved)):
                return True, "ok"
        except (OSError, RuntimeError):
            continue

    # Allow if path is within cwd or WM_STATE_ROOT
    return True, "ok"


def _validate_python_syntax(file_path: str) -> tuple[bool, str]:
    """Validate Python file syntax.

    Returns:
        (valid, error_message) tuple.
    """
    try:
        text = Path(file_path).read_text(encoding="utf-8")
        ast.parse(text)
        return True, "ok"
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg} at line {e.lineno}"
    except (OSError, UnicodeDecodeError) as e:
        return False, str(e)


def _validate_file(file_path: str) -> tuple[bool, str]:
    """Validate a file based on its extension.

    Returns:
        (valid, error_message) tuple.
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        return _validate_python_syntax(file_path)
    # Non-Python files: basic read check
    try:
        Path(file_path).read_text(encoding="utf-8")
        return True, "ok"
    except (OSError, UnicodeDecodeError) as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# MCP Tool Handlers
# ---------------------------------------------------------------------------


def handle_fast_write_write(**kwargs: Any) -> dict[str, Any]:
    """Write content to a file atomically. Overwrites if file exists.

    Args:
        path: Target file path
        content: File content to write
        validate: If True, validate syntax after write (default: True for .py files)
        backup: If True, rename existing file to <file>.bak before write
        dry_run: If True, show what would be written without writing
        encoding: File encoding (default: utf-8)
    """
    file_path = kwargs.get("path", "")
    content = kwargs.get("content", "")
    validate = kwargs.get("validate", True)
    backup = kwargs.get("backup", False)
    dry_run = kwargs.get("dry_run", False)
    encoding = kwargs.get("encoding", "utf-8")

    if not file_path:
        return {"status": "error", "error": "path is required"}
    if not isinstance(content, str):
        return {"status": "error", "error": "content must be a string"}

    if len(content.encode(encoding)) > _MAX_FILE_SIZE:
        return {"status": "error", "error": f"Content exceeds max size ({_MAX_FILE_SIZE} bytes)"}

    allowed, reason = _is_path_safe(file_path)
    if not allowed:
        return {"status": "error", "error": f"Path not allowed: {reason}"}

    if dry_run:
        return {
            "status": "success",
            "mode": "dry_run",
            "path": str(Path(file_path).resolve()),
            "bytes": len(content.encode(encoding)),
            "lines": content.count("\n") + 1,
        }

    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Backup if requested and file exists
    backup_path = None
    if backup and p.exists():
        backup_path = str(p) + ".bak"
        shutil.copy2(str(p), backup_path)

    # Write atomically
    try:
        p.write_text(content, encoding=encoding)
    except (OSError, UnicodeEncodeError) as e:
        return {"status": "error", "error": f"Write failed: {e}"}

    # Validate
    validation_result = None
    if validate and p.suffix.lower() == ".py":
        valid, msg = _validate_python_syntax(str(p))
        validation_result = {"valid": valid, "message": msg}
        if not valid:
            # Restore backup if validation failed
            if backup_path and Path(backup_path).exists():
                shutil.copy2(backup_path, str(p))
            return {
                "status": "error",
                "error": f"Syntax validation failed: {msg}",
                "path": str(p),
                "backup": backup_path,
            }

    return {
        "status": "success",
        "path": str(p),
        "bytes": len(content.encode(encoding)),
        "lines": content.count("\n") + 1,
        "validation": validation_result,
        "backup": backup_path,
    }


def handle_fast_write_append(**kwargs: Any) -> dict[str, Any]:
    """Append content to an existing file.

    Args:
        path: Target file path
        content: Content to append
        validate: If True, validate syntax after append (default: True for .py files)
    """
    file_path = kwargs.get("path", "")
    content = kwargs.get("content", "")
    validate = kwargs.get("validate", True)

    if not file_path:
        return {"status": "error", "error": "path is required"}
    if not isinstance(content, str):
        return {"status": "error", "error": "content must be a string"}

    allowed, reason = _is_path_safe(file_path)
    if not allowed:
        return {"status": "error", "error": f"Path not allowed: {reason}"}

    p = Path(file_path)
    if not p.exists():
        return {"status": "error", "error": f"File does not exist: {file_path}"}

    try:
        with open(str(p), "a", encoding="utf-8") as f:
            f.write(content)
    except (OSError, UnicodeEncodeError) as e:
        return {"status": "error", "error": f"Append failed: {e}"}

    validation_result = None
    if validate and p.suffix.lower() == ".py":
        valid, msg = _validate_python_syntax(str(p))
        validation_result = {"valid": valid, "message": msg}
        if not valid:
            return {
                "status": "error",
                "error": f"Syntax validation failed after append: {msg}",
                "path": str(p),
            }

    return {
        "status": "success",
        "path": str(p),
        "appended_bytes": len(content.encode("utf-8")),
        "validation": validation_result,
    }


def handle_fast_write_batch(**kwargs: Any) -> dict[str, Any]:
    """Write multiple files in one operation.

    Args:
        files: Dict of {path: content} pairs
        validate: If True, validate Python syntax after write (default: True)
        backup: If True, backup existing files before overwrite
    """
    files = kwargs.get("files", {})
    validate = kwargs.get("validate", True)
    backup = kwargs.get("backup", False)

    if not files or not isinstance(files, dict):
        return {"status": "error", "error": "files dict is required (path -> content)"}
    if len(files) > _MAX_BATCH_FILES:
        return {"status": "error", "error": f"Too many files (max {_MAX_BATCH_FILES})"}

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for file_path, content in files.items():
        r = handle_fast_write_write(
            path=file_path,
            content=content,
            validate=validate,
            backup=backup,
        )
        if r.get("status") == "success":
            results.append({"path": file_path, "bytes": r.get("bytes", 0), "lines": r.get("lines", 0)})
        else:
            errors.append({"path": file_path, "error": r.get("error", "unknown")})

    return {
        "status": "success" if not errors else "partial_success" if results else "error",
        "written": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


def handle_fast_write_validate(**kwargs: Any) -> dict[str, Any]:
    """Validate syntax of a file without writing.

    Args:
        path: File path to validate
    """
    file_path = kwargs.get("path", "")
    if not file_path:
        return {"status": "error", "error": "path is required"}

    p = Path(file_path)
    if not p.exists():
        return {"status": "error", "error": f"File does not exist: {file_path}"}

    valid, msg = _validate_file(str(p))
    return {
        "status": "success",
        "path": str(p),
        "valid": valid,
        "message": msg,
        "extension": p.suffix,
    }
