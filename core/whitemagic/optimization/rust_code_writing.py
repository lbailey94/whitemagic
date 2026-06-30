# ruff: noqa: BLE001
"""Python bridge for Rust Code Writing Clone Army.

Provides access to parallel file write/edit/copy/move/delete operations
via the Rust CodeWritingClone and CodeWritingArmy PyO3 bindings.

Recovered from archive v0.2 whitemagic-rust/src/code_writing_clone.rs.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_rs: Any = None
try:
    import whitemagic_rust as _wmr

    if hasattr(_wmr, "CodeWritingClone"):
        _rs = _wmr
        logger.debug("Rust CodeWritingClone available — parallel file ops enabled")
except ImportError:
    pass


def code_writing_available() -> bool:
    """Check if Rust code writing clone is available."""
    return _rs is not None


def create_code_operation(
    op_type: str,
    target_file: str,
    content: str = "",
    source_file: str = "",
    line_start: int | None = None,
    line_end: int | None = None,
) -> Any:
    """Create a CodeOperation object for use with CodeWritingClone/Army.

    Args:
        op_type: One of "write", "edit", "copy", "move", "delete"
        target_file: Target file path (relative to base_path)
        content: Content to write (for write/edit operations)
        source_file: Source file path (for copy/move operations)
        line_start: Starting line number (for edit operations)
        line_end: Ending line number (for edit operations)
    """
    if not code_writing_available():
        raise RuntimeError("Rust code writing clone not available")
    return _rs.CodeOperation(
        op_type, source_file, target_file, content, line_start, line_end
    )


def write_file(base_path: str, target_file: str, content: str) -> dict[str, Any]:
    """Write a single file via Rust CodeWritingClone.

    Args:
        base_path: Base directory path
        target_file: Target file path relative to base_path
        content: File content to write

    Returns:
        Dict with success, files_modified, lines_written, duration_ms
    """
    if not code_writing_available():
        raise RuntimeError("Rust code writing clone not available")
    clone = _rs.CodeWritingClone("writer-1", base_path)
    op = create_code_operation("write", target_file, content=content)
    result = clone.execute_operation(op)
    return {
        "success": result.success,
        "files_modified": result.files_modified,
        "lines_written": result.lines_written,
        "duration_ms": result.duration_ms,
        "error": result.error_message,
    }


def deploy_writing_army(
    base_path: str,
    operations: list[dict[str, Any]],
    clone_count: int = 8,
    army_id: str = "code-army",
) -> list[dict[str, Any]]:
    """Deploy a parallel code writing army for batch file operations.

    Args:
        base_path: Base directory path
        operations: List of operation dicts with keys: op_type, target_file,
                    content (optional), source_file (optional),
                    line_start (optional), line_end (optional)
        clone_count: Number of clones in the army
        army_id: Identifier for the army

    Returns:
        List of result dicts with success, files_modified, lines_written, etc.
    """
    if not code_writing_available():
        raise RuntimeError("Rust code writing clone not available")
    army = _rs.CodeWritingArmy(army_id, base_path, clone_count)
    ops = [create_code_operation(**op) for op in operations]
    results = army.deploy_operations(ops)
    return [
        {
            "success": r.success,
            "files_modified": r.files_modified,
            "lines_written": r.lines_written,
            "duration_ms": r.duration_ms,
            "error": r.error_message,
        }
        for r in results
    ]


def benchmark_code_writing(operation_count: int, base_path: str) -> dict[str, float]:
    """Benchmark parallel code writing performance.

    Args:
        operation_count: Number of write operations to benchmark
        base_path: Base directory for test output

    Returns:
        Dict with throughput and timing stats
    """
    if not code_writing_available():
        raise RuntimeError("Rust code writing clone not available")
    return dict(_rs.benchmark_code_writing(operation_count, base_path))
