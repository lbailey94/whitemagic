"""Canonical Tool Runtime — Single entry point for all tool execution.

Phase 1 of the Codebase Hardening Strategy. Extended in Phase 4 with:
- Typed error info on ToolResult
- async_execute() / async_dispatch() for async callers
- Cancellation propagation and timeout classification

This module defines:

- ``ExecutionMode``: explicit enum replacing implicit name-based behavior
- ``ToolRequest``: typed request with all identity fields
- ``ToolResult``: typed result with status, payload, metadata, and typed error
- ``ToolRuntime``: the canonical execution boundary (sync + async)

Design principles:
1. All existing entry points (call_tool, dispatch, MCP handlers) become
   adapters that delegate to ``ToolRuntime.execute()``.
2. Name normalization, schema validation, idempotency, and envelope
   normalization live inside the runtime boundary.
3. The runtime is initially a thin wrapper around ``call_tool()``
   to preserve existing behavior. As phases progress, logic moves
   from call_tool() into the runtime.
4. A feature flag (WM_TOOL_RUNTIME=1) controls whether the runtime
   is active. When disabled, call_tool() behaves as before.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionMode(StrEnum):
    """Explicit execution mode for tool dispatch.

    Replaces implicit behavior based on tool-name string patterns.

    - FULL: Complete pipeline — all middleware, governance, telemetry
    - READ_ONLY_AUDITED: Read-only tools with audit trail but no write gates
    - INTERNAL: System-internal calls (e.g. dream cycle, maintenance) —
      skips cognitive mode and self-model checks but keeps governance
    - MAINTENANCE: Admin/maintenance mode — bypasses non-essential
      middleware but keeps audit logging. Used by health checks and
      infrastructure tools.
    """

    FULL = "full"
    READ_ONLY_AUDITED = "read_only_audited"
    INTERNAL = "internal"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class ToolRequest:
    """Typed tool request with full identity context.

    All fields that affect routing, caching, governance, and audit
    are explicit here — no implicit extraction from kwargs.

    Attributes:
        tool_name: The tool to execute (may be an alias).
        arguments: Tool arguments (kwargs).
        request_id: Unique request identifier. Auto-generated if None.
        user_id: The user owning this request. Default "local".
        agent_id: The agent initiating this request. Default "default".
        requested_mode: Execution mode. Default FULL.
        policy_profile: Governance profile name. Default "default".
        galaxy: Memory galaxy context. Default "default".
        idempotency_key: Optional idempotency key for write tools.
        dry_run: If True, simulate without side effects.
    """

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    user_id: str = "local"
    agent_id: str = "default"
    requested_mode: ExecutionMode = ExecutionMode.FULL
    policy_profile: str = "default"
    galaxy: str = "default"
    idempotency_key: str | None = None
    dry_run: bool = False

    def resolved_request_id(self) -> str:
        """Return the request_id, generating one if not set."""
        return self.request_id or str(uuid4())

    def to_kwargs(self) -> dict[str, Any]:
        """Convert to the kwargs dict expected by call_tool()."""
        kwargs = dict(self.arguments)
        if self.request_id:
            kwargs["request_id"] = self.request_id
        if self.idempotency_key:
            kwargs["idempotency_key"] = self.idempotency_key
        if self.dry_run:
            kwargs["dry_run"] = True
        return kwargs


@dataclass
class ToolResult:
    """Typed tool result with status, payload, and execution metadata.

    This is the canonical return type from ``ToolRuntime.execute()``.
    It wraps the envelope dict produced by the existing envelope system
    and provides typed access to common fields.

    Attributes:
        status: "success" or "error"
        tool: The canonical tool name that was executed.
        request_id: The request ID (survives the full pipeline).
        envelope: The full envelope dict (stable contract shape).
        error_code: Error code if status is "error", else None.
        message: Human-readable status message.
        details: Tool-specific payload.
        duration_s: Wall-clock execution time in seconds.
        degradation: List of degradation notes (e.g. fallbacks used).
    """

    status: str
    tool: str
    request_id: str
    envelope: dict[str, Any]
    error_code: str | None = None
    error_type: str | None = None
    retryable: bool = False
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    degradation: list[str] = field(default_factory=list)

    @classmethod
    def from_envelope(
        cls,
        envelope: dict[str, Any],
        duration_s: float = 0.0,
        degradation: list[str] | None = None,
    ) -> ToolResult:
        """Build a ToolResult from an envelope dict."""
        details = envelope.get("details", {})
        # Extract typed error info from details if present
        error_type = None
        retryable = envelope.get("retryable", False)
        if isinstance(details, dict):
            error_type = details.get("error_type")
            if "retryable" in details:
                retryable = details["retryable"]
        return cls(
            status=envelope.get("status", "error"),
            tool=envelope.get("tool", ""),
            request_id=envelope.get("request_id", ""),
            envelope=envelope,
            error_code=envelope.get("error_code"),
            error_type=error_type,
            retryable=retryable,
            message=envelope.get("message", ""),
            details=details if isinstance(details, dict) else {},
            duration_s=duration_s,
            degradation=degradation or [],
        )

    @classmethod
    def from_error(
        cls,
        request: ToolRequest,
        exc: Exception,
        duration_s: float = 0.0,
        degradation: list[str] | None = None,
    ) -> ToolResult:
        """Build a ToolResult from a typed exception.

        Uses ``classify_exception`` to convert generic exceptions.
        """
        from whitemagic.tools.envelope import err
        from whitemagic.tools.errors import classify_exception

        typed = classify_exception(exc)
        env = err(
            tool=request.tool_name,
            request_id=request.resolved_request_id(),
            error_code=typed.error_code,
            message=typed.message,
            details=typed.details,
            retryable=typed.retryable,
        )
        return cls(
            status="error",
            tool=request.tool_name,
            request_id=request.resolved_request_id(),
            envelope=env,
            error_code=typed.error_code,
            error_type=type(typed).__name__,
            retryable=typed.retryable,
            message=typed.message,
            details=typed.details,
            duration_s=duration_s,
            degradation=degradation or [],
        )

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_error(self) -> bool:
        return self.status == "error"

    def to_dict(self) -> dict[str, Any]:
        """Return the envelope dict (backward compat with callers expecting dict)."""
        return self.envelope


class ToolRuntime:
    """The canonical tool execution boundary.

    All tool execution must flow through ``ToolRuntime.execute()``.
    Existing entry points (call_tool, dispatch, MCP handlers) delegate here.

    Initially, this class wraps ``call_tool()`` to preserve existing
    behavior. As the hardening strategy progresses, logic moves from
    call_tool() into the runtime, and call_tool() becomes a thin adapter.
    """

    _instance: ToolRuntime | None = None

    @classmethod
    def get(cls) -> ToolRuntime:
        """Get the singleton ToolRuntime instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute(self, request: ToolRequest) -> ToolResult:
        """Execute a tool request and return a typed result.

        This is THE canonical entry point for tool execution.

        Args:
            request: A typed ToolRequest with all identity fields.

        Returns:
            A ToolResult containing the envelope, status, and metadata.
        """
        t0 = time.perf_counter()
        degradation: list[str] = []

        # Resolve request ID early so it survives the full pipeline
        request_id = request.resolved_request_id()

        # Canonical name normalization — resolve aliases before dispatch
        from whitemagic.tools.canonical import canonical_tool_name

        canonical_name = canonical_tool_name(request.tool_name)
        if canonical_name != request.tool_name.strip():
            degradation.append(f"alias:{request.tool_name}->{canonical_name}")

        # Build kwargs for the existing call_tool() adapter
        kwargs = request.to_kwargs()
        kwargs.setdefault("request_id", request_id)

        # Inject user_id and galaxy into kwargs for downstream consumers
        # (these are no-ops for tools that don't read them, but they make
        # the identity context available to middleware and handlers)
        if request.user_id != "local":
            kwargs.setdefault("user_id", request.user_id)
        if request.galaxy != "default":
            kwargs.setdefault("galaxy", request.galaxy)

        # Mode-based dispatch
        if request.requested_mode == ExecutionMode.MAINTENANCE:
            # Maintenance mode: use fast-path dispatch directly
            result = self._execute_maintenance(request, kwargs)
            degradation.append("maintenance_mode")
        elif request.requested_mode == ExecutionMode.INTERNAL:
            # Internal mode: skip cognitive mode and self-model checks
            kwargs["_force_full_pipeline"] = True
            result = self._execute_full(request, kwargs)
            degradation.append("internal_mode")
        else:
            # FULL and READ_ONLY_AUDITED both go through the full pipeline
            result = self._execute_full(request, kwargs)

        duration = time.perf_counter() - t0

        # Wrap the raw result dict into a ToolResult
        if isinstance(result, dict):
            return ToolResult.from_envelope(result, duration, degradation)
        else:
            # Non-dict result — wrap as error
            from whitemagic.tools.envelope import err
            env = err(
                tool=request.tool_name,
                request_id=request_id,
                error_code="internal_error",
                message=f"Tool returned non-dict result: {type(result).__name__}",
            )
            return ToolResult.from_envelope(env, duration, degradation)

    def _execute_full(
        self, request: ToolRequest, kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute through the full call_tool() pipeline."""
        from whitemagic.tools.unified_api import call_tool

        return call_tool(request.tool_name, **kwargs)

    def _execute_maintenance(
        self, request: ToolRequest, kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute in maintenance mode — fast-path only, no middleware."""
        # Try fast-path first
        from whitemagic.tools.dispatch_table import _fast_path_dispatch, _is_fast_path
        if _is_fast_path(request.tool_name):
            return _fast_path_dispatch(request.tool_name, **kwargs)

        # Fall back to full pipeline if not fast-path eligible
        return self._execute_full(request, kwargs)

    async def async_execute(self, request: ToolRequest) -> ToolResult:
        """Execute a tool request asynchronously.

        This is the canonical async entry point. It wraps the sync
        ``execute()`` in ``asyncio.to_thread()`` so that:
        - The event loop is not blocked during tool execution
        - Cancellation propagates correctly (``asyncio.CancelledError``)
        - No coroutine warnings are emitted

        If the underlying handler is itself async (returns a coroutine),
        the sync ``execute()`` already handles it via ``_run_async``.
        This method ensures the *runtime* call itself is non-blocking.

        Args:
            request: A typed ToolRequest with all identity fields.

        Returns:
            A ToolResult containing the envelope, status, and metadata.
        """
        t0 = time.perf_counter()
        try:
            result = await asyncio.to_thread(self.execute, request)
            return result
        except asyncio.CancelledError:
            duration = time.perf_counter() - t0
            from whitemagic.tools.errors import CancellationError

            raise CancellationError(
                f"Tool execution cancelled: {request.tool_name}",
                details={
                    "tool": request.tool_name,
                    "request_id": request.resolved_request_id(),
                    "duration_s": duration,
                },
            ) from None

    async def async_dispatch(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Convenience async dispatch — build a ToolRequest and call async_execute.

        This is the async equivalent of ``execute(ToolRequest(...))``.
        Extracts common identity fields from kwargs.
        """
        request_id = kwargs.pop("request_id", None)
        user_id = kwargs.pop("user_id", "local")
        galaxy = kwargs.pop("galaxy", "default")
        agent_id = kwargs.pop("_agent_id", "default")
        policy_profile = kwargs.pop("_policy_profile", "default")
        request = ToolRequest(
            tool_name=tool_name,
            arguments=kwargs,
            request_id=request_id,
            user_id=user_id,
            agent_id=agent_id,
            policy_profile=policy_profile,
            galaxy=galaxy,
        )
        return await self.async_execute(request)


def is_runtime_enabled() -> bool:
    """Check if the ToolRuntime is enabled via feature flag.

    When disabled, call_tool() behaves as before (direct dispatch).
    When enabled, call_tool() delegates to ToolRuntime.execute().
    """
    return os.environ.get("WM_TOOL_RUNTIME", "0") in ("1", "true", "yes")


def execute(request: ToolRequest) -> ToolResult:
    """Module-level convenience function for ToolRuntime.execute()."""
    return ToolRuntime.get().execute(request)


async def async_execute(request: ToolRequest) -> ToolResult:
    """Module-level convenience function for ToolRuntime.async_execute()."""
    return await ToolRuntime.get().async_execute(request)


async def async_dispatch(tool_name: str, **kwargs: Any) -> ToolResult:
    """Module-level convenience function for ToolRuntime.async_dispatch()."""
    return await ToolRuntime.get().async_dispatch(tool_name, **kwargs)
