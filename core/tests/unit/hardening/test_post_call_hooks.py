"""Phase 3 — Tests for post-call hook separation.

Verifies that:
- DispatchPipeline.use_post_call() registers hooks
- Post-call hooks receive (ctx, result) and can augment result
- Post-call hooks always fail-open (exceptions logged, result preserved)
- The 5 observers are registered as post-call hooks, not main pipeline
- The main pipeline has been reduced (no observer middleware in _middlewares)
- describe_post_call() returns hook names
"""
from __future__ import annotations

import pytest
from whitemagic.tools.middleware import (
    DispatchPipeline,
    DispatchContext,
    PostCallHook,
)


class TestPostCallHookRegistration:
    """Verify use_post_call() and describe_post_call()."""

    def test_use_post_call_registers_hook(self):
        p = DispatchPipeline()
        p.use_post_call("my_hook", lambda ctx, result: result)
        assert len(p._post_call_hooks) == 1
        assert p.describe_post_call() == ["my_hook"]

    def test_use_post_call_returns_pipeline(self):
        p = DispatchPipeline()
        ret = p.use_post_call("hook", lambda ctx, result: result)
        assert ret is p

    def test_multiple_post_call_hooks_registered_in_order(self):
        p = DispatchPipeline()
        p.use_post_call("first", lambda ctx, result: result)
        p.use_post_call("second", lambda ctx, result: result)
        assert p.describe_post_call() == ["first", "second"]


class TestPostCallHookExecution:
    """Verify post-call hooks execute after main pipeline."""

    def test_hook_receives_ctx_and_result(self):
        received = []
        p = DispatchPipeline()
        p.use("handler", lambda ctx, next_fn: {"status": "success", "data": "test"})
        p.use_post_call("observer", lambda ctx, result: received.append((ctx.tool_name, result)) or result)
        p.execute("test_tool")
        assert len(received) == 1
        assert received[0][0] == "test_tool"
        assert received[0][1]["status"] == "success"

    def test_hook_can_augment_result(self):
        p = DispatchPipeline()
        p.use("handler", lambda ctx, next_fn: {"status": "success"})
        p.use_post_call("augmenter", lambda ctx, result: {**result, "_augmented": True})
        result = p.execute("test_tool")
        assert result["_augmented"] is True

    def test_hook_failure_preserves_original_result(self):
        p = DispatchPipeline()
        p.use("handler", lambda ctx, next_fn: {"status": "success", "data": "important"})
        def boom_hook(ctx, result):
            raise RuntimeError("hook crashed")
        p.use_post_call("boom", boom_hook)
        result = p.execute("test_tool")
        assert result["status"] == "success"
        assert result["data"] == "important"

    def test_multiple_hooks_run_sequentially(self):
        order = []
        p = DispatchPipeline()
        p.use("handler", lambda ctx, next_fn: {"status": "success"})
        p.use_post_call("first", lambda ctx, result: order.append("first") or result)
        p.use_post_call("second", lambda ctx, result: order.append("second") or result)
        p.execute("test_tool")
        assert order == ["first", "second"]

    def test_hook_returning_none_preserves_result(self):
        p = DispatchPipeline()
        p.use("handler", lambda ctx, next_fn: {"status": "success", "data": "kept"})
        p.use_post_call("noop", lambda ctx, result: None)
        result = p.execute("test_tool")
        assert result["status"] == "success"
        assert result["data"] == "kept"


class TestPipelineStructure:
    """Verify the 5 observers are post-call hooks, not main pipeline middleware."""

    def test_observers_not_in_main_pipeline(self):
        from whitemagic.tools.dispatch_table import _pipeline
        main_names = set(_pipeline.describe())
        observers = {"karma_effects", "observability", "session_recorder", "error_learner", "wasm_verify"}
        in_main = observers & main_names
        assert not in_main, f"Observers still in main pipeline: {in_main}"

    def test_observers_in_post_call_hooks(self):
        from whitemagic.tools.dispatch_table import _pipeline
        hook_names = set(_pipeline.describe_post_call())
        observers = {"karma_effects", "observability", "session_recorder", "error_learner", "wasm_verify"}
        missing = observers - hook_names
        assert not missing, f"Observers missing from post-call hooks: {missing}"

    def test_main_pipeline_reduced(self):
        """Main pipeline should have fewer stages now that 5 observers moved out."""
        from whitemagic.tools.dispatch_table import _pipeline
        main_count = len(_pipeline.describe())
        # Was 27, now should be 23 (22 original minus 5 observers plus timing)
        assert main_count <= 23, f"Main pipeline has {main_count} stages — expected <= 23"
        assert main_count >= 20, f"Main pipeline has {main_count} stages — expected >= 20"

    def test_post_call_hook_count(self):
        from whitemagic.tools.dispatch_table import _pipeline
        assert len(_pipeline.describe_post_call()) == 5

    def test_timing_middleware_in_main_pipeline(self):
        from whitemagic.tools.dispatch_table import _pipeline
        assert "timing" in _pipeline.describe()

    def test_core_router_still_last(self):
        from whitemagic.tools.dispatch_table import _pipeline
        names = _pipeline.describe()
        assert names[-1] == "core_router"


class TestPostCallHookFailOpen:
    """Verify post-call hooks fail open even with multiple hooks."""

    def test_one_hook_failing_does_not_stop_others(self):
        order = []
        p = DispatchPipeline()
        p.use("handler", lambda ctx, next_fn: {"status": "success"})
        def boom(ctx, result):
            raise RuntimeError("boom")
        p.use_post_call("boom", boom)
        p.use_post_call("after_boom", lambda ctx, result: order.append("ran") or result)
        result = p.execute("test_tool")
        assert result["status"] == "success"
        assert order == ["ran"]
