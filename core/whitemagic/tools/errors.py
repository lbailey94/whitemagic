"""Stable error codes and typed exception hierarchy for the Whitemagic tool contract.

Phase 4 of the Codebase Hardening Strategy.

Error hierarchy (all inherit from ToolExecutionError):

    ToolExecutionError
    ├── ValidationError          — invalid input parameters
    ├── AuthorizationError       — permission/RBAC denied
    ├── PolicyUnavailableError   — governance service unavailable
    ├── DependencyUnavailableError — optional dependency missing
    ├── DatabaseIntegrityError   — corruption, schema mismatch
    ├── TimeoutError             — operation exceeded time budget
    ├── CancellationError        — operation was cancelled
    ├── BridgeProtocolError      — native bridge protocol violation
    └── PartialOperationError    — batch/restore/import partially completed

Each typed exception carries:
- error_code: stable string code (from ErrorCode)
- message: human-readable
- details: structured dict
- retryable: whether the caller should retry
- cause: the original exception (preserved via raise ... from ...)
"""
from __future__ import annotations

from typing import Any


class ErrorCode:
    """ErrorCode: error code.

    Keep these codes stable across versions; add new codes instead of renaming.
    """

    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_PARAMS = "invalid_params"
    POLICY_BLOCKED = "policy_blocked"
    MISSING_DEPENDENCY = "missing_dependency"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    UNAUTHORIZED = "unauthorized"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    DOWNSTREAM_ERROR = "downstream_error"
    INTERNAL_ERROR = "internal_error"
    # Dispatch pipeline gates
    INPUT_INVALID = "input_invalid"
    INPUT_REJECTED = "input_rejected"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    MATURITY_GATE = "maturity_gate"
    # Phase 4 typed error codes
    POLICY_UNAVAILABLE = "policy_unavailable"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    DATABASE_INTEGRITY = "database_integrity"
    CANCELLED = "cancelled"
    BRIDGE_PROTOCOL = "bridge_protocol"
    PARTIAL_OPERATION = "partial_operation"


class ToolExecutionError(Exception):
    """Exception raised when a tool execution fails with a specific contract error code.

    All typed errors in the hierarchy inherit from this class so that existing
    ``except ToolExecutionError`` catches continue to work.
    """

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        """Serialize error info to a dict suitable for envelope details."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "error_type": self.__class__.__name__,
        }


# ── Typed Error Hierarchy ──────────────────────────────────────────────


class ValidationError(ToolExecutionError):
    """Invalid input parameters or schema validation failure."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.INVALID_PARAMS,
            details=details,
            retryable=retryable,
        )


class AuthorizationError(ToolExecutionError):
    """Permission denied, RBAC rejection, or unauthorized access."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.PERMISSION_DENIED,
            details=details,
            retryable=retryable,
        )


class PolicyUnavailableError(ToolExecutionError):
    """A required governance/policy service is unavailable.

    This is distinct from PolicyBlocked (the service was available and denied
    the request).  PolicyUnavailable means we could not determine whether the
    action is allowed.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = True,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.POLICY_UNAVAILABLE,
            details=details,
            retryable=retryable,
        )


class DependencyUnavailableError(ToolExecutionError):
    """An optional dependency (native bridge, library, service) is missing."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.DEPENDENCY_UNAVAILABLE,
            details=details,
            retryable=retryable,
        )


class DatabaseIntegrityError(ToolExecutionError):
    """Database corruption, schema mismatch, or integrity check failure."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.DATABASE_INTEGRITY,
            details=details,
            retryable=retryable,
        )


class TimeoutError(ToolExecutionError):  # noqa: A001 — intentional shadow
    """Operation exceeded its time budget.

    Shadows builtin TimeoutError so that ``except TimeoutError`` in tool
    code catches the typed version.  The builtin is still accessible via
    ``builtins.TimeoutError``.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = True,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.TIMEOUT,
            details=details,
            retryable=retryable,
        )


class CancellationError(ToolExecutionError):
    """Operation was cancelled before completion."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.CANCELLED,
            details=details,
            retryable=retryable,
        )


class BridgeProtocolError(ToolExecutionError):
    """Native bridge protocol violation (malformed JSON, unexpected response)."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = True,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.BRIDGE_PROTOCOL,
            details=details,
            retryable=retryable,
        )


class PartialOperationError(ToolExecutionError):
    """A batch/restore/import operation partially completed.

    The ``details`` dict should contain:
    - completed: int — successfully processed items
    - skipped: int — items skipped (e.g. validation failure)
    - failed: int — items that raised an error
    - item_errors: list[dict] — per-item error details
    - rollback_state: str — "none", "staged", "rolled_back", "committed"
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.PARTIAL_OPERATION,
            details=details,
            retryable=retryable,
        )


# ── Classification Helper ──────────────────────────────────────────────


def classify_exception(exc: Exception) -> ToolExecutionError:
    """Convert a generic exception into a typed ToolExecutionError.

    This is used at core boundaries to replace broad ``except Exception``
    catches with typed classification.  If the exception is already a
    ``ToolExecutionError``, it is returned as-is.
    """
    if isinstance(exc, ToolExecutionError):
        return exc

    # Map known stdlib exceptions to typed errors
    import asyncio
    import sqlite3

    if isinstance(exc, asyncio.CancelledError):
        return CancellationError(
            f"Operation cancelled: {exc}",
            details={"original_type": type(exc).__name__},
        )
    if isinstance(exc, TimeoutError):
        # builtins.TimeoutError — not our typed one
        return TimeoutError(
            f"Operation timed out: {exc}",
            details={"original_type": type(exc).__name__},
        )
    if isinstance(exc, sqlite3.DatabaseError):
        return DatabaseIntegrityError(
            f"Database error: {exc}",
            details={"original_type": type(exc).__name__},
        )
    if isinstance(exc, PermissionError):
        return AuthorizationError(
            f"Permission denied: {exc}",
            details={"original_type": type(exc).__name__},
        )
    if isinstance(exc, ValueError):
        return ValidationError(
            f"Invalid value: {exc}",
            details={"original_type": type(exc).__name__},
        )
    if isinstance(exc, KeyError):
        return ValidationError(
            f"Missing required key: {exc}",
            details={"original_type": type(exc).__name__},
        )
    if isinstance(exc, (ConnectionError, ConnectionRefusedError, ConnectionResetError)):
        return DependencyUnavailableError(
            f"Connection failed: {exc}",
            details={"original_type": type(exc).__name__},
            retryable=True,
        )
    if isinstance(exc, ImportError):
        return DependencyUnavailableError(
            f"Dependency missing: {exc}",
            details={"original_type": type(exc).__name__},
        )

    # Fallback: wrap as generic internal error
    return ToolExecutionError(
        f"{type(exc).__name__}: {exc}",
        error_code=ErrorCode.INTERNAL_ERROR,
        details={"original_type": type(exc).__name__},
    )
