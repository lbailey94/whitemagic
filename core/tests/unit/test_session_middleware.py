"""Tests for session recorder middleware (auto-recording)."""

# ruff: noqa: BLE001
import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_mw_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_SKIP_POLYGLOT"] = "1"


@pytest.fixture(autouse=True)
def reset_recorder():
    from whitemagic.core.memory.session_recorder import reset_session_recorder
    reset_session_recorder()
    yield()
    reset_session_recorder()


class TestSessionRecorderMiddleware:
    def test_records_tool_call(self):
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_session_recorder,
        )

        def next_fn(ctx):
            return {"status": "success", "tool": ctx.tool_name}

        ctx = DispatchContext(tool_name="create_memory", kwargs={})
        result = mw_session_recorder(ctx, next_fn)

        assert result["status"] == "success"

        from whitemagic.core.memory.session_recorder import get_session_recorder
        recorder = get_session_recorder()
        stats = recorder.get_stats()
        assert stats["total_turns"] == 1
        assert stats["roles"].get("ai", 0) == 1

    def test_records_wm_thought_as_user(self):
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_session_recorder,
        )

        def next_fn(ctx):
            return {"status": "success", "routed_to": "gana_neck.create_memory"}

        ctx = DispatchContext(tool_name="wm", kwargs={"thought": "remember that we built session memory"})
        result = mw_session_recorder(ctx, next_fn)

        assert result["status"] == "success"

        from whitemagic.core.memory.session_recorder import get_session_recorder
        recorder = get_session_recorder()
        stats = recorder.get_stats()
        # Should have 2 turns: user (from thought) + ai (from result)
        assert stats["total_turns"] == 2
        assert stats["roles"].get("user", 0) == 1
        assert stats["roles"].get("ai", 0) == 1

    def test_skips_session_tools(self):
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_session_recorder,
        )

        called = False

        def next_fn(ctx):
            nonlocal called
            called = True
            return {"status": "success"}

        ctx = DispatchContext(tool_name="session.recall", kwargs={})
        result = mw_session_recorder(ctx, next_fn)

        assert called is True
        assert result["status"] == "success"

        from whitemagic.core.memory.session_recorder import get_session_recorder
        recorder = get_session_recorder()
        stats = recorder.get_stats()
        assert stats["total_turns"] == 0

    def test_skips_when_disabled(self):
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_session_recorder,
        )

        old_val = os.environ.get("WM_SESSION_RECORD")
        os.environ["WM_SESSION_RECORD"] = "0"

        try:
            def next_fn(ctx):
                return {"status": "success"}

            ctx = DispatchContext(tool_name="create_memory", kwargs={})
            mw_session_recorder(ctx, next_fn)

            from whitemagic.core.memory.session_recorder import get_session_recorder
            recorder = get_session_recorder()
            stats = recorder.get_stats()
            assert stats["total_turns"] == 0
        finally:
            if old_val is None:
                del os.environ["WM_SESSION_RECORD"]
            else:
                os.environ["WM_SESSION_RECORD"] = old_val

    def test_error_turns_get_higher_importance(self):
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_session_recorder,
        )

        def next_fn(ctx):
            return {"status": "error", "error_code": "test"}

        ctx = DispatchContext(tool_name="some_tool", kwargs={})
        mw_session_recorder(ctx, next_fn)

        from whitemagic.core.memory.session_recorder import get_session_recorder
        recorder = get_session_recorder()
        turns = recorder.recall_recent(n=1)
        assert len(turns) == 1
        assert turns[0]["turn_type"] == "error"
        assert turns[0]["importance"] >= 0.7

    def test_never_breaks_pipeline(self):
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_session_recorder,
        )

        def next_fn(ctx):
            return {"status": "success"}

        # Even if recorder fails internally, pipeline should work
        ctx = DispatchContext(tool_name="test_tool", kwargs={})
        result = mw_session_recorder(ctx, next_fn)
        assert result is not None
        assert result["status"] == "success"
