"""Stable error codes for the Whitemagic tool contract.

Keep these codes stable across versions; add new codes instead of renaming.
"""

from __future__ import annotations

from typing import Any


class ErrorCode:
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


class ToolExecutionError(Exception):
    """Exception raised when a tool execution fails with a specific contract error code."""

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

