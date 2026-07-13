"""Phase 4 — Typed Errors, Partial Operations, and Async Correctness.

Tests:
- Fault injection for every core error class
- classify_exception maps stdlib exceptions to typed errors
- ToolResult.from_error produces correct typed results
- PartialOperationResult tracks completed/skipped/failed
- Async execute produces same envelope as sync
- Cancellation propagation
- No coroutine warnings from LazyHandler
"""
from __future__ import annotations

import asyncio
import sqlite3
import warnings
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.tools.errors import (
    AuthorizationError,
    BridgeProtocolError,
    CancellationError,
    DatabaseIntegrityError,
    DependencyUnavailableError,
    ErrorCode,
    PartialOperationError,
    PolicyUnavailableError,
    TimeoutError,
    ToolExecutionError,
    ValidationError,
    classify_exception,
)
from whitemagic.tools.partial_result import ItemError, PartialOperationResult
from whitemagic.tools.runtime import (
    ExecutionMode,
    ToolRequest,
    ToolResult,
    ToolRuntime,
    async_dispatch,
    async_execute,
)


# ── Error Hierarchy ────────────────────────────────────────────────────


class TestTypedErrorHierarchy:
    """Every typed error inherits from ToolExecutionError and has correct code."""

    @pytest.mark.parametrize(
        "exc_cls,expected_code",
        [
            (ValidationError, ErrorCode.INVALID_PARAMS),
            (AuthorizationError, ErrorCode.PERMISSION_DENIED),
            (PolicyUnavailableError, ErrorCode.POLICY_UNAVAILABLE),
            (DependencyUnavailableError, ErrorCode.DEPENDENCY_UNAVAILABLE),
            (DatabaseIntegrityError, ErrorCode.DATABASE_INTEGRITY),
            (TimeoutError, ErrorCode.TIMEOUT),
            (CancellationError, ErrorCode.CANCELLED),
            (BridgeProtocolError, ErrorCode.BRIDGE_PROTOCOL),
            (PartialOperationError, ErrorCode.PARTIAL_OPERATION),
        ],
    )
    def test_error_code(self, exc_cls, expected_code):
        exc = exc_cls("test message")
        assert exc.error_code == expected_code
        assert isinstance(exc, ToolExecutionError)
        assert exc.message == "test message"

    def test_retryable_defaults(self):
        assert ValidationError("x").retryable is False
        assert PolicyUnavailableError("x").retryable is True
        assert TimeoutError("x").retryable is True
        assert BridgeProtocolError("x").retryable is True
        assert CancellationError("x").retryable is False

    def test_to_dict_serializes_error_info(self):
        exc = ValidationError("bad input", details={"field": "name"})
        d = exc.to_dict()
        assert d["error_code"] == ErrorCode.INVALID_PARAMS
        assert d["message"] == "bad input"
        assert d["details"] == {"field": "name"}
        assert d["error_type"] == "ValidationError"
        assert d["retryable"] is False

    def test_details_default_empty_dict(self):
        exc = ValidationError("x")
        assert exc.details == {}


# ── classify_exception ─────────────────────────────────────────────────


class TestClassifyException:
    """classify_exception maps stdlib exceptions to typed errors."""

    def test_value_error_becomes_validation(self):
        typed = classify_exception(ValueError("bad"))
        assert isinstance(typed, ValidationError)
        assert typed.details["original_type"] == "ValueError"

    def test_key_error_becomes_validation(self):
        typed = classify_exception(KeyError("missing"))
        assert isinstance(typed, ValidationError)

    def test_permission_error_becomes_authorization(self):
        typed = classify_exception(PermissionError("denied"))
        assert isinstance(typed, AuthorizationError)

    def test_sqlite_database_error_becomes_database_integrity(self):
        typed = classify_exception(sqlite3.DatabaseError("corrupt"))
        assert isinstance(typed, DatabaseIntegrityError)

    def test_cancelled_error_becomes_cancellation(self):
        typed = classify_exception(asyncio.CancelledError())
        assert isinstance(typed, CancellationError)

    def test_timeout_error_becomes_typed_timeout(self):
        typed = classify_exception(TimeoutError("slow"))
        # Our typed TimeoutError, not builtin
        assert isinstance(typed, ToolExecutionError)
        assert typed.error_code == ErrorCode.TIMEOUT

    def test_connection_error_becomes_dependency(self):
        typed = classify_exception(ConnectionError("refused"))
        assert isinstance(typed, DependencyUnavailableError)
        assert typed.retryable is True

    def test_import_error_becomes_dependency(self):
        typed = classify_exception(ImportError("no module"))
        assert isinstance(typed, DependencyUnavailableError)

    def test_tool_execution_error_passes_through(self):
        original = ValidationError("already typed")
        typed = classify_exception(original)
        assert typed is original

    def test_generic_exception_becomes_internal_error(self):
        typed = classify_exception(RuntimeError("unexpected"))
        assert isinstance(typed, ToolExecutionError)
        assert typed.error_code == ErrorCode.INTERNAL_ERROR
        assert typed.details["original_type"] == "RuntimeError"


# ── ToolResult.from_error ──────────────────────────────────────────────


class TestToolResultFromError:
    """ToolResult.from_error produces typed error results."""

    def test_from_error_with_validation_error(self):
        req = ToolRequest(tool_name="test.tool", request_id="r1")
        result = ToolResult.from_error(req, ValueError("bad input"))
        assert result.status == "error"
        assert result.error_code == ErrorCode.INVALID_PARAMS
        assert result.error_type == "ValidationError"
        assert result.is_error

    def test_from_error_preserves_request_id(self):
        req = ToolRequest(tool_name="test.tool", request_id="custom-id-123")
        result = ToolResult.from_error(req, RuntimeError("boom"))
        assert result.request_id == "custom-id-123"

    def test_from_error_envelope_has_error_code(self):
        req = ToolRequest(tool_name="test.tool", request_id="r1")
        result = ToolResult.from_error(req, PermissionError("no"))
        env = result.to_dict()
        assert env["status"] == "error"
        assert env["error_code"] == ErrorCode.PERMISSION_DENIED


# ── PartialOperationResult ─────────────────────────────────────────────


class TestPartialOperationResult:
    """PartialOperationResult tracks batch operation outcomes."""

    def test_complete_success(self):
        r = PartialOperationResult(operation="import", total=10, completed=10)
        assert r.is_complete_success
        assert not r.is_partial_failure
        assert not r.is_total_failure
        assert r.success_rate == 1.0
        status, code, retry = r.to_envelope_status()
        assert status == "success"

    def test_partial_failure(self):
        r = PartialOperationResult(operation="import", total=10, completed=7)
        r.add_error(7, ValueError("bad"), item_id="item-7")
        r.add_error(8, KeyError("missing"), item_id="item-8")
        r.add_error(9, RuntimeError("boom"), item_id="item-9")
        assert r.is_partial_failure
        assert r.failed == 3
        assert r.success_rate == 0.7
        status, code, retry = r.to_envelope_status()
        assert status == "error"
        assert code == ErrorCode.PARTIAL_OPERATION
        assert retry is True

    def test_total_failure(self):
        r = PartialOperationResult(operation="import", total=3, completed=0)
        r.add_error(0, ValueError("a"), item_id="a")
        r.add_error(1, ValueError("b"), item_id="b")
        r.add_error(2, ValueError("c"), item_id="c")
        assert r.is_total_failure
        assert not r.is_partial_failure
        status, code, retry = r.to_envelope_status()
        assert status == "error"
        assert code == ErrorCode.INTERNAL_ERROR

    def test_to_dict_structure(self):
        r = PartialOperationResult(
            operation="restore",
            total=5,
            completed=3,
            rollback_state="committed",
        )
        r.add_error(3, ValueError("x"), item_id="f3")
        d = r.to_dict()
        assert d["operation"] == "restore"
        assert d["total"] == 5
        assert d["completed"] == 3
        assert d["failed"] == 1
        assert d["rollback_state"] == "committed"
        assert len(d["item_errors"]) == 1
        assert d["item_errors"][0]["item_id"] == "f3"
        assert d["item_errors"][0]["error_code"] == ErrorCode.INVALID_PARAMS

    def test_add_error_increments_failed(self):
        r = PartialOperationResult(operation="test", total=2, completed=1)
        assert r.failed == 0
        r.add_error(1, RuntimeError("boom"), item_id="x")
        assert r.failed == 1
        assert len(r.item_errors) == 1

    def test_empty_result(self):
        r = PartialOperationResult(operation="test")
        assert r.total == 0
        assert r.success_rate == 0.0
        assert r.is_complete_success  # 0 total, 0 failed, 0 skipped


# ── Async Execute / Cancellation ───────────────────────────────────────


class TestAsyncExecute:
    """async_execute produces same results as sync execute."""

    def test_async_health_check_matches_sync(self):
        req = ToolRequest(tool_name="health.check", request_id="async-1")
        sync_result = ToolRuntime.get().execute(req)
        async_result = asyncio.run(ToolRuntime.get().async_execute(req))
        assert sync_result.status == async_result.status
        assert sync_result.tool == async_result.tool

    def test_module_level_async_execute(self):
        req = ToolRequest(tool_name="health.check", request_id="async-2")
        result = asyncio.run(async_execute(req))
        assert isinstance(result, ToolResult)
        assert result.tool == "health.check"

    def test_module_level_async_dispatch(self):
        result = asyncio.run(async_dispatch("health.check", request_id="async-3"))
        assert isinstance(result, ToolResult)
        assert result.tool == "health.check"

    def test_async_unknown_tool_returns_error(self):
        req = ToolRequest(tool_name="nonexistent.tool.xyz", request_id="async-err")
        result = asyncio.run(ToolRuntime.get().async_execute(req))
        assert result.is_error

    def test_async_request_id_survives(self):
        rid = "async-survive-999"
        req = ToolRequest(tool_name="health.check", request_id=rid)
        result = asyncio.run(ToolRuntime.get().async_execute(req))
        assert result.request_id == rid


class TestCancellationPropagation:
    """Cancellation propagates correctly through async_execute."""

    def test_cancellation_raises_typed_error(self):
        async def _cancel_test():
            req = ToolRequest(tool_name="health.check", request_id="cancel-1")

            # Mock execute to block so we can cancel
            original_execute = ToolRuntime.execute
            ToolRuntime.execute = MagicMock(side_effect=lambda r: __import__("time").sleep(10))
            try:
                task = asyncio.create_task(ToolRuntime.get().async_execute(req))
                await asyncio.sleep(0.05)
                task.cancel()
                with pytest.raises(CancellationError):
                    await task
            finally:
                ToolRuntime.execute = original_execute

        asyncio.run(_cancel_test())


# ── No Coroutine Warnings ──────────────────────────────────────────────


class TestNoCoroutineWarnings:
    """LazyHandler must not silently close coroutines or emit warnings."""

    def test_lazy_handler_uses_run_async(self):
        """Verify that LazyHandler delegates to _run_async for coroutines."""
        from whitemagic.tools.dispatch_core import LazyHandler

        # Create a handler that returns a coroutine
        async def async_handler(**kwargs):
            return {"status": "success", "data": "async"}

        handler = LazyHandler.__new__(LazyHandler)
        handler.module_name = "test"
        handler.function_name = "test"
        handler.tool_name = ""
        handler._cached_func = async_handler

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = handler()
        assert isinstance(result, dict)
        assert result["status"] == "success"

    def test_lazy_handler_abs_uses_run_async(self):
        """Verify that LazyHandlerAbs delegates to _run_async for coroutines."""
        from whitemagic.tools.dispatch_core import LazyHandlerAbs

        async def async_handler(**kwargs):
            return {"status": "success", "data": "async-abs"}

        handler = LazyHandlerAbs.__new__(LazyHandlerAbs)
        handler.module_path = "test"
        handler.function_name = "test"
        handler._cached_func = async_handler

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = handler()
        assert isinstance(result, dict)
        assert result["status"] == "success"


# ── Middleware Typed Error Recording ───────────────────────────────────


class TestMiddlewareTypedErrors:
    """Middleware _wrap records typed error info in context."""

    def test_middleware_error_has_error_code(self):
        from whitemagic.tools.middleware import DispatchContext, _wrap

        def failing_mw(ctx, next_fn):
            raise ValueError("bad input")

        def terminal(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="test", kwargs={})
        wrapped = _wrap(failing_mw, terminal, "failing_mw")
        result = wrapped(ctx)

        # Should have fallen through to terminal
        assert result["status"] == "success"
        # Should have recorded typed error
        errors = ctx.meta.get("middleware_errors", [])
        assert len(errors) == 1
        assert errors[0]["error_code"] == ErrorCode.INVALID_PARAMS
        assert errors[0]["retryable"] is False

    def test_middleware_passes_through_tool_execution_error(self):
        from whitemagic.tools.middleware import DispatchContext, _wrap

        def raising_mw(ctx, next_fn):
            raise ValidationError("explicit typed error")

        def terminal(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="test", kwargs={})
        wrapped = _wrap(raising_mw, terminal, "raising_mw")
        with pytest.raises(ValidationError):
            wrapped(ctx)


# ── Fast-Path Typed Errors ─────────────────────────────────────────────


class TestFastPathTypedErrors:
    """Fast-path dispatch returns typed error codes."""

    def test_fast_path_error_has_typed_code(self):
        from whitemagic.tools.dispatch_table import _fast_path_dispatch, DISPATCH_TABLE

        def failing_handler(**kwargs):
            raise ValueError("bad param")

        # Temporarily register a handler
        original = DISPATCH_TABLE.get("test.typed_error")
        DISPATCH_TABLE["test.typed_error"] = failing_handler
        try:
            result = _fast_path_dispatch("test.typed_error")
            assert result["status"] == "error"
            assert result["error_code"] == ErrorCode.INVALID_PARAMS
            assert result["retryable"] is False
        finally:
            if original is not None:
                DISPATCH_TABLE["test.typed_error"] = original
            else:
                DISPATCH_TABLE.pop("test.typed_error", None)

    def test_fast_path_tool_execution_error_passes_through(self):
        from whitemagic.tools.dispatch_table import _fast_path_dispatch, DISPATCH_TABLE

        def raising_handler(**kwargs):
            raise AuthorizationError("not allowed")

        original = DISPATCH_TABLE.get("test.auth_error")
        DISPATCH_TABLE["test.auth_error"] = raising_handler
        try:
            result = _fast_path_dispatch("test.auth_error")
            assert result["status"] == "error"
            assert result["error_code"] == ErrorCode.PERMISSION_DENIED
        finally:
            if original is not None:
                DISPATCH_TABLE["test.auth_error"] = original
            else:
                DISPATCH_TABLE.pop("test.auth_error", None)
