"""Phase 2 — Tests for the three-layer fail-open fix.

Verifies that:
- Critical middleware fails closed (returns error envelope, does not continue)
- Enrichment middleware fails open (logs error, continues to next_fn)
- _wrap() distinguishes critical vs enrichment based on the flag
- _ensure_cached() tracks critical dependency failures
- Individual critical middleware no longer swallows exceptions internally
- DispatchPipeline.use() accepts and stores the critical flag
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from whitemagic.tools.middleware import (
    DispatchPipeline,
    DispatchContext,
    _wrap,
    _ensure_cached,
    _critical_deps_failed,
    mw_input_sanitizer,
    mw_circuit_breaker,
    mw_rate_limiter,
    mw_tool_permissions,
    mw_security_monitor,
    mw_governor,
    mw_maturity_gate,
)


class TestWrapFailClosed:
    """Layer 1: _wrap() must fail-closed for critical middleware."""

    def test_critical_middleware_exception_returns_error_envelope(self):
        """When a critical middleware raises, _wrap returns an error envelope."""
        def boom_mw(ctx, next_fn):
            raise RuntimeError("critical failure")

        def next_fn(ctx):
            return {"status": "success", "data": "should not reach"}

        wrapped = _wrap(boom_mw, next_fn, "test_critical", critical=True)
        ctx = DispatchContext(tool_name="test_tool", kwargs={})
        result = wrapped(ctx)

        assert result is not None
        assert result["status"] == "error"
        assert result["error_code"] == "middleware_fail_closed"
        assert "test_critical" in result["middleware"]
        assert "test_tool" in result["tool"]

    def test_enrichment_middleware_exception_continues(self):
        """When an enrichment middleware raises, _wrap continues to next_fn."""
        def boom_mw(ctx, next_fn):
            raise RuntimeError("enrichment failure")

        def next_fn(ctx):
            return {"status": "success", "data": "reached"}

        wrapped = _wrap(boom_mw, next_fn, "test_enrichment", critical=False)
        ctx = DispatchContext(tool_name="test_tool", kwargs={})
        result = wrapped(ctx)

        assert result is not None
        assert result["status"] == "success"
        assert result["data"] == "reached"

    def test_tool_execution_error_always_propagates(self):
        """ToolExecutionError must always re-raise, regardless of critical flag."""
        from whitemagic.tools.errors import ToolExecutionError

        def boom_mw(ctx, next_fn):
            raise ToolExecutionError("typed error", error_code="TEST_ERROR")

        def next_fn(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="test_tool", kwargs={})
        wrapped_critical = _wrap(boom_mw, next_fn, "critical", critical=True)
        with pytest.raises(ToolExecutionError):
            wrapped_critical(ctx)

        wrapped_enrichment = _wrap(boom_mw, next_fn, "enrichment", critical=False)
        with pytest.raises(ToolExecutionError):
            wrapped_enrichment(ctx)

    def test_middleware_errors_recorded_in_context(self):
        """Both critical and enrichment errors should be recorded in ctx.meta."""
        def boom_mw(ctx, next_fn):
            raise ValueError("test error")

        def next_fn(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="test_tool", kwargs={})
        wrapped = _wrap(boom_mw, next_fn, "test_mw", critical=False)
        wrapped(ctx)

        assert "middleware_errors" in ctx.meta
        assert len(ctx.meta["middleware_errors"]) == 1
        assert ctx.meta["middleware_errors"][0]["middleware"] == "test_mw"


class TestDispatchPipelineCriticalFlag:
    """Layer 1: DispatchPipeline.use() must accept and store critical flag."""

    def test_use_accepts_critical_kwarg(self):
        p = DispatchPipeline()
        p.use("test_mw", lambda ctx, next_fn: next_fn(ctx), critical=True)
        assert len(p._middlewares) == 1
        name, mw, critical = p._middlewares[0]
        assert name == "test_mw"
        assert critical is True

    def test_use_defaults_to_enrichment(self):
        p = DispatchPipeline()
        p.use("test_mw", lambda ctx, next_fn: next_fn(ctx))
        name, mw, critical = p._middlewares[0]
        assert critical is False

    def test_describe_returns_names(self):
        p = DispatchPipeline()
        p.use("first", lambda ctx, next_fn: next_fn(ctx), critical=True)
        p.use("second", lambda ctx, next_fn: next_fn(ctx))
        assert p.describe() == ["first", "second"]


class TestEnsureCachedCriticalDeps:
    """Layer 2: _ensure_cached() must track critical dependency failures."""

    def test_critical_deps_failed_set_exists(self):
        # Ensure the set exists and is accessible
        assert isinstance(_critical_deps_failed, set)

    def test_successful_load_does_not_add_to_failed(self):
        """When deps load successfully, _critical_deps_failed stays empty."""
        # _ensure_cached may have already been called — check it didn't
        # add false positives for deps that actually loaded
        _ensure_cached()
        # If the deps loaded, they shouldn't be in the failed set
        from whitemagic.tools.middleware import _sanitize_tool_args
        if _sanitize_tool_args is not None:
            assert "input_sanitizer" not in _critical_deps_failed


class TestCriticalMiddlewareNoInternalCatch:
    """Layer 3: Critical middleware must not swallow exceptions internally."""

    def test_input_sanitizer_propagates_exception(self):
        """If _sanitize_tool_args raises, mw_input_sanitizer should let it propagate."""
        ctx = DispatchContext(tool_name="test", kwargs={})
        with patch("whitemagic.tools.middleware._ensure_cached"), \
             patch("whitemagic.tools.middleware._sanitize_tool_args") as mock:
            mock.side_effect = RuntimeError("sanitizer crash")
            with pytest.raises(RuntimeError, match="sanitizer crash"):
                mw_input_sanitizer(ctx, lambda c: {"status": "success"})

    def test_circuit_breaker_propagates_exception(self):
        """If breaker registry raises, mw_circuit_breaker should let it propagate."""
        ctx = DispatchContext(tool_name="test", kwargs={})
        with patch("whitemagic.tools.middleware._ensure_cached"), \
             patch("whitemagic.tools.middleware._get_breaker_registry") as mock:
            mock.return_value.get.side_effect = RuntimeError("breaker crash")
            with pytest.raises(RuntimeError, match="breaker crash"):
                mw_circuit_breaker(ctx, lambda c: {"status": "success"})

    def test_rate_limiter_propagates_exception(self):
        """If rate limiter raises, mw_rate_limiter should let it propagate."""
        ctx = DispatchContext(tool_name="test", kwargs={})
        with patch("whitemagic.tools.middleware._ensure_cached"), \
             patch("whitemagic.tools.middleware._get_rate_limiter") as mock:
            mock.side_effect = RuntimeError("rate limiter crash")
            with pytest.raises(RuntimeError, match="rate limiter crash"):
                mw_rate_limiter(ctx, lambda c: {"status": "success"})

    def test_tool_permissions_propagates_exception(self):
        """If permission check raises, mw_tool_permissions should let it propagate."""
        ctx = DispatchContext(tool_name="test", kwargs={})
        with patch("whitemagic.tools.middleware._ensure_cached"), \
             patch("whitemagic.tools.middleware._check_tool_permission") as mock:
            mock.side_effect = RuntimeError("permission crash")
            with pytest.raises(RuntimeError, match="permission crash"):
                mw_tool_permissions(ctx, lambda c: {"status": "success"})

    def test_security_monitor_propagates_exception(self):
        """If security monitor raises, mw_security_monitor should let it propagate."""
        ctx = DispatchContext(tool_name="test", kwargs={})
        with patch("whitemagic.tools.middleware._ensure_cached"), \
             patch("whitemagic.tools.middleware._get_security_monitor") as mock:
            mock.return_value.record_call.side_effect = RuntimeError("monitor crash")
            with pytest.raises(RuntimeError, match="monitor crash"):
                mw_security_monitor(ctx, lambda c: {"status": "success"})

    def test_governor_propagates_exception(self):
        """If governor raises, mw_governor should let it propagate."""
        import os
        old = os.environ.get("WM_BENCHMARK_MODE", "")
        os.environ.pop("WM_BENCHMARK_MODE", None)
        try:
            ctx = DispatchContext(tool_name="test", kwargs={})
            with patch("whitemagic.tools.middleware._ensure_cached"), \
                 patch("whitemagic.tools.middleware._get_governor") as mock:
                mock.return_value.validate_tool_call.side_effect = RuntimeError("governor crash")
                with pytest.raises(RuntimeError, match="governor crash"):
                    mw_governor(ctx, lambda c: {"status": "success"})
        finally:
            if old:
                os.environ["WM_BENCHMARK_MODE"] = old

    def test_maturity_gate_propagates_exception(self):
        """If maturity check raises, mw_maturity_gate should let it propagate."""
        import os
        old = os.environ.get("WM_BENCHMARK_MODE", "")
        os.environ.pop("WM_BENCHMARK_MODE", None)
        try:
            ctx = DispatchContext(tool_name="test", kwargs={})
            with patch("whitemagic.tools.middleware._ensure_cached"), \
                 patch("whitemagic.tools.middleware._check_maturity_for_tool") as mock:
                mock.side_effect = RuntimeError("maturity crash")
                with pytest.raises(RuntimeError, match="maturity crash"):
                    mw_maturity_gate(ctx, lambda c: {"status": "success"})
        finally:
            if old:
                os.environ["WM_BENCHMARK_MODE"] = old


class TestInputSanitizerFailClosed:
    """Input sanitizer must fail-closed when dependency is missing."""

    def test_returns_error_when_dep_missing(self):
        """When input_sanitizer is in _critical_deps_failed, return error envelope."""
        ctx = DispatchContext(tool_name="test", kwargs={})
        with patch("whitemagic.tools.middleware._ensure_cached"), \
             patch("whitemagic.tools.middleware._sanitize_tool_args", None), \
             patch("whitemagic.tools.middleware._critical_deps_failed", {"input_sanitizer"}):
            result = mw_input_sanitizer(ctx, lambda c: {"status": "success"})
            assert result is not None
            assert result["status"] == "error"
            assert result["error_code"] == "dependency_missing"


class TestPipelineIntegrationFailClosed:
    """Integration: a critical middleware failure in the real pipeline blocks execution."""

    def test_critical_failure_blocks_execution(self):
        """When a critical middleware raises in the pipeline, execution is blocked."""
        p = DispatchPipeline()
        p.use("critical_boom", lambda ctx, next_fn: (_ for _ in ()).throw(RuntimeError("boom")), critical=True)
        p.use("handler", lambda ctx, next_fn: {"status": "success", "data": "reached"})

        result = p.execute("test_tool")
        assert result is not None
        assert result["status"] == "error"
        assert result["error_code"] == "middleware_fail_closed"
        assert "critical_boom" in result["middleware"]

    def test_enrichment_failure_continues_execution(self):
        """When an enrichment middleware raises, execution continues."""
        p = DispatchPipeline()
        p.use("enrichment_boom", lambda ctx, next_fn: (_ for _ in ()).throw(RuntimeError("boom")), critical=False)
        p.use("handler", lambda ctx, next_fn: {"status": "success", "data": "reached"})

        result = p.execute("test_tool")
        assert result is not None
        assert result["status"] == "success"
        assert result["data"] == "reached"
