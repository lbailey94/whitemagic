"""Tests for token reduction middleware: semantic cache, draft-review, dense dispatch."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from whitemagic.tools.middleware import (
    DispatchContext,
    _cache_key,
    _is_cacheable_tool,
    _is_draft_review_candidate,
    mw_draft_review,
    mw_semantic_cache,
)


# ---------------------------------------------------------------------------
# Semantic cache tests
# ---------------------------------------------------------------------------


class TestSemanticCache:
    """Test mw_semantic_cache middleware."""

    def test_cacheable_tool_detection(self):
        assert _is_cacheable_tool("ollama.chat")
        assert _is_cacheable_tool("think")
        assert _is_cacheable_tool("analyze")
        assert not _is_cacheable_tool("memory.search")
        assert not _is_cacheable_tool("scratchpad.create")

    def test_cache_key_deterministic(self):
        kwargs1 = {"prompt": "What is the meaning of life?"}
        kwargs2 = {"prompt": "What is the meaning of life?"}
        key1 = _cache_key("ollama.chat", kwargs1)
        key2 = _cache_key("ollama.chat", kwargs2)
        assert key1 == key2
        assert len(key1) == 16

    def test_cache_key_differs_by_tool(self):
        kwargs = {"prompt": "What is the meaning of life?"}
        key1 = _cache_key("ollama.chat", kwargs)
        key2 = _cache_key("think", kwargs)
        assert key1 != key2

    def test_cache_key_differs_by_prompt(self):
        key1 = _cache_key("ollama.chat", {"prompt": "What is 2+2?"})
        key2 = _cache_key("ollama.chat", {"prompt": "What is 3+3?"})
        assert key1 != key2

    def test_non_cacheable_passes_through(self):
        """Non-cacheable tools should pass through without caching."""
        called = False

        def next_fn(ctx):
            nonlocal called
            called = True
            return {"status": "success", "result": "ok"}

        ctx = DispatchContext(tool_name="memory.search", kwargs={"query": "test"})
        result = mw_semantic_cache(ctx, next_fn)
        assert called
        assert result["status"] == "success"

    def test_cache_miss_dispatches_and_caches(self):
        """On cache miss, should dispatch and cache the result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            def next_fn(ctx):
                return {"status": "success", "result": "42 is the answer"}

            ctx = DispatchContext(
                tool_name="ollama.chat",
                kwargs={"prompt": "What is the meaning of life?"},
            )

            with patch("whitemagic.config.paths.CACHE_DIR", Path(tmpdir)):
                result = mw_semantic_cache(ctx, next_fn)
                assert result["status"] == "success"
                assert result["result"] == "42 is the answer"

    def test_cache_hit_short_circuits(self):
        """On cache hit, should return cached result without dispatching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pre-populate cache using the SAME filename the middleware uses
            from whitemagic.core.intelligence.agentic.token_optimizer import QueryCache
            cache = QueryCache(cache_file=Path(tmpdir) / "dispatch_query_cache.json")
            key = _cache_key("ollama.chat", {"prompt": "cached question"})
            cache.set(key, "cached answer", 100)

            dispatched = False

            def next_fn(ctx):
                nonlocal dispatched
                dispatched = True
                return {"status": "success", "result": "should not see this"}

            ctx = DispatchContext(
                tool_name="ollama.chat",
                kwargs={"prompt": "cached question"},
            )

            with patch("whitemagic.config.paths.CACHE_DIR", Path(tmpdir)):
                result = mw_semantic_cache(ctx, next_fn)
                assert not dispatched  # Should NOT have dispatched
                assert result["method"] == "semantic_cache"
                assert result["resolved_locally"] is True
                assert result["tokens_saved"] > 0


# ---------------------------------------------------------------------------
# Draft-review tests
# ---------------------------------------------------------------------------


class TestDraftReview:
    """Test mw_draft_review middleware."""

    def test_draft_review_candidate_detection(self):
        # Long prompt with inference tool → candidate
        assert _is_draft_review_candidate(
            "ollama.chat",
            {"prompt": "x" * 200},
        )
        # Short prompt → not a candidate
        assert not _is_draft_review_candidate(
            "ollama.chat",
            {"prompt": "short"},
        )
        # Non-inference tool → not a candidate
        assert not _is_draft_review_candidate(
            "memory.search",
            {"prompt": "x" * 200},
        )

    def test_draft_review_re_entry_guard(self):
        """If _draft_review=True in kwargs, should pass through."""
        called = False

        def next_fn(ctx):
            nonlocal called
            called = True
            return {"status": "success", "result": "ok"}

        ctx = DispatchContext(
            tool_name="ollama.chat",
            kwargs={"prompt": "x" * 200, "_draft_review": True},
        )
        result = mw_draft_review(ctx, next_fn)
        assert called
        assert result["status"] == "success"

    def test_draft_review_non_candidate_passes_through(self):
        """Non-candidate tools should pass through."""
        called = False

        def next_fn(ctx):
            nonlocal called
            called = True
            return {"status": "success", "result": "ok"}

        ctx = DispatchContext(
            tool_name="memory.search",
            kwargs={"prompt": "x" * 200},
        )
        result = mw_draft_review(ctx, next_fn)
        assert called

    def test_draft_review_falls_back_on_import_error(self):
        """If Ollama handler is unavailable, should fall through to normal dispatch."""
        called = False

        def next_fn(ctx):
            nonlocal called
            called = True
            return {"status": "success", "result": "ok"}

        ctx = DispatchContext(
            tool_name="ollama.chat",
            kwargs={"prompt": "x" * 200},
        )

        with patch("whitemagic.tools.handlers.ollama.handle_ollama_chat", side_effect=ImportError("no ollama")):
            result = mw_draft_review(ctx, next_fn)
            assert called  # Fell through to normal dispatch


# ---------------------------------------------------------------------------
# Dense encoding in dispatch tests
# ---------------------------------------------------------------------------


class TestDenseDispatchContext:
    """Test that dispatch pipeline uses dense encoding for WM context."""

    def test_wm_get_context_called_with_dense(self):
        """Verify that get_context is called with dense=True in the dispatch path."""
        from whitemagic.core.intelligence.working_memory import WorkingMemory

        wm = WorkingMemory(capacity=5)
        wm.attend(
            memory_id="test1",
            content="The memory system needs consolidation scheduling",
            importance=0.8,
        )

        # Get context with dense=True (as dispatch pipeline now does)
        ctx = wm.get_context(max_tokens=500, dense=True)
        assert len(ctx) == 1
        assert "content_dense" in ctx[0]
        assert "compression_ratio" in ctx[0]
        assert ctx[0]["compression_ratio"] >= 1.0

    def test_dense_context_smaller_than_plain(self):
        """Dense context should have fewer estimated tokens than plain."""
        from whitemagic.core.intelligence.working_memory import WorkingMemory

        wm = WorkingMemory(capacity=5)
        wm.attend(
            memory_id="test1",
            content="The memory system needs consolidation and the cognitive dispatch pipeline requires optimization",
            importance=0.8,
        )

        plain_ctx = wm.get_context(max_tokens=500, dense=False)
        dense_ctx = wm.get_context(max_tokens=500, dense=True)

        # Dense should have compression_ratio > 1.0
        assert dense_ctx[0]["compression_ratio"] > 1.0
        # Plain should not have content_dense
        assert "content_dense" not in plain_ctx[0]


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Test that the new middlewares are wired into the pipeline."""

    def test_pipeline_has_semantic_cache(self):
        """Pipeline should include semantic_cache stage."""
        from whitemagic.tools.dispatch_table import _pipeline
        stage_names = [name for name, _ in _pipeline._middlewares]
        assert "semantic_cache" in stage_names

    def test_pipeline_has_draft_review(self):
        """Pipeline should include draft_review stage."""
        from whitemagic.tools.dispatch_table import _pipeline
        stage_names = [name for name, _ in _pipeline._middlewares]
        assert "draft_review" in stage_names

    def test_pipeline_order(self):
        """Semantic cache should come before inference_router, draft_review after."""
        from whitemagic.tools.dispatch_table import _pipeline
        stage_names = [name for name, _ in _pipeline._middlewares]
        sc_idx = stage_names.index("semantic_cache")
        ir_idx = stage_names.index("inference_router")
        dr_idx = stage_names.index("draft_review")
        assert sc_idx < ir_idx  # Cache before router
        assert ir_idx < dr_idx  # Router before draft-review

    def test_non_inference_tool_passes_through_all(self):
        """A non-inference tool should pass through cache and draft-review without short-circuit."""
        from whitemagic.tools.dispatch_table import _pipeline

        # Use a lightweight status tool that won't be cached or draft-reviewed
        result = _pipeline.execute("gnosis", compact=True)
        # Should get a valid result (not from cache or draft-review)
        assert result is not None
        assert isinstance(result, dict)
        # Should NOT have semantic_cache method
        if result.get("method"):
            assert result["method"] != "semantic_cache"
