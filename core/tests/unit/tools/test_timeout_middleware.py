"""Tests for the timeout middleware."""

import os
import time

import pytest

from whitemagic.tools.middleware import (
    DispatchContext,
    DispatchPipeline,
    mw_timeout,
)


class TestTimeoutMiddleware:
    """Tests for mw_timeout middleware."""

    def test_fast_tool_passes_through(self):
        """Tools that complete quickly should return normally."""
        ctx = DispatchContext(tool_name="fast_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "success", "data": "fast"}

        result = mw_timeout(ctx, next_fn)
        assert result is not None
        assert result["status"] == "success"
        assert result["data"] == "fast"

    def test_slow_tool_times_out(self):
        """Tools that exceed the timeout should return a TIMEOUT error."""
        ctx = DispatchContext(tool_name="slow_tool", kwargs={"_timeout_s": 0.1})

        def next_fn(ctx):
            time.sleep(2.0)
            return {"status": "success"}

        result = mw_timeout(ctx, next_fn)
        assert result is not None
        assert result["status"] == "error"
        assert result["error_code"] == "TIMEOUT"
        assert result["tool"] == "slow_tool"
        assert result["timeout_s"] == 0.1

    def test_zero_timeout_disables(self):
        """A timeout of 0 should disable the timeout middleware."""
        ctx = DispatchContext(tool_name="any_tool", kwargs={"_timeout_s": 0})

        def next_fn(ctx):
            return {"status": "success"}

        result = mw_timeout(ctx, next_fn)
        assert result is not None
        assert result["status"] == "success"

    def test_exception_propagates(self):
        """Exceptions from the tool should propagate through the timeout."""
        ctx = DispatchContext(tool_name="error_tool", kwargs={"_timeout_s": 5.0})

        def next_fn(ctx):
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            mw_timeout(ctx, next_fn)

    def test_custom_timeout_via_env(self):
        """WM_TOOL_TIMEOUT env var should set the default timeout."""
        os.environ["WM_TOOL_TIMEOUT"] = "0.1"
        try:
            ctx = DispatchContext(tool_name="env_tool", kwargs={})

            def next_fn(ctx):
                time.sleep(2.0)
                return {"status": "success"}

            result = mw_timeout(ctx, next_fn)
            assert result is not None
            assert result["status"] == "error"
            assert result["error_code"] == "TIMEOUT"
        finally:
            del os.environ["WM_TOOL_TIMEOUT"]

    def test_timeout_in_pipeline(self):
        """Timeout middleware should work within the full pipeline."""
        p = DispatchPipeline()

        # Add a slow middleware that simulates a long-running tool
        def _slow_mw(ctx, next_fn):
            time.sleep(2.0)
            return {"status": "success"}

        p.use("timeout", mw_timeout)
        p.use("slow_tool", _slow_mw)

        result = p.execute("slow_pipeline_tool", _timeout_s=0.1)
        assert result is not None
        assert result["status"] == "error"
        assert result["error_code"] == "TIMEOUT"
