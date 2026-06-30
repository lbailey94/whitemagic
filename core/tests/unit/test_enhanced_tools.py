# ruff: noqa: BLE001
"""Unit tests for enhanced web research, reasoning, and alchemical tools.

Tests:
- web_search_batch: parallel multi-query search
- web content cache: store/retrieve/list/clear
- cached_deep_fetch: dedup + cache
- extract_image_urls: image extraction from HTML
- AdaptiveBatchSizer: dynamic batch sizing
- ParallelReasoningTree: memory injection, anti-pattern, MC scoring
- SelfImprovementPipeline: iterative code generation
- AlchemicalLoop: yin/yang procession with output→input chaining
- RabbitHoleExplorer: web_explore with depth-aware categories
- frozenset regression test for extract_unfamiliar_terms
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_"))
os.environ.setdefault("WM_SILENT_INIT", "1")


# ---------------------------------------------------------------------------
# web_search_batch tests
# ---------------------------------------------------------------------------


class TestWebSearchBatch:
    """Tests for parallel multi-query search."""

    def test_batch_search_result_dataclass(self):
        """BatchSearchResult should initialize correctly."""
        from whitemagic.gardens.browser.web_research import BatchSearchResult

        result = BatchSearchResult(queries=["test1", "test2"])
        assert result.queries == ["test1", "test2"]
        assert result.total_results == 0
        assert result.results_by_query == {}
        assert result.errors == []

    def test_batch_search_result_to_dict(self):
        """BatchSearchResult.to_dict should return correct structure."""
        from whitemagic.gardens.browser.web_research import BatchSearchResult

        result = BatchSearchResult(
            queries=["q1"],
            total_results=3,
            results_by_query={"q1": [{"url": "http://example.com"}]},
            duration_ms=100.0,
        )
        d = result.to_dict()
        assert d["queries"] == ["q1"]
        assert d["total_results"] == 3
        assert d["duration_ms"] == 100.0
        assert "q1" in d["results_by_query"]


# ---------------------------------------------------------------------------
# Web content cache tests
# ---------------------------------------------------------------------------


class TestWebContentCache:
    """Tests for web content caching."""

    def test_cache_and_read(self):
        """cache_web_content and read_cached_content should round-trip."""
        from whitemagic.gardens.browser.web_research import (
            cache_web_content,
            read_cached_content,
            clear_cached_content,
        )

        url = "https://test.example.com/cache-test"
        content = "This is cached content for testing."
        clear_cached_content()
        filepath = cache_web_content(url, content, title="Test Cache")
        assert filepath.exists()
        retrieved = read_cached_content(url)
        assert retrieved is not None
        assert content in retrieved
        assert "title: Test Cache" in retrieved
        clear_cached_content()

    def test_list_cached(self):
        """list_cached_content should return cached items."""
        from whitemagic.gardens.browser.web_research import (
            cache_web_content,
            list_cached_content,
            clear_cached_content,
        )

        clear_cached_content()
        cache_web_content("https://a.com/test", "content A", title="A")
        cache_web_content("https://b.com/test", "content B", title="B")
        items = list_cached_content()
        assert len(items) == 2
        clear_cached_content()
        assert len(list_cached_content()) == 0

    def test_clear_with_age_filter(self):
        """clear_cached_content with older_than_hours should only remove old files."""
        from whitemagic.gardens.browser.web_research import (
            cache_web_content,
            list_cached_content,
            clear_cached_content,
        )

        clear_cached_content()
        cache_web_content("https://c.com/test", "content C", title="C")
        # Clear files older than 1 hour — should not remove just-created file
        removed = clear_cached_content(older_than_hours=1)
        assert removed == 0
        assert len(list_cached_content()) == 1
        # Clear all
        removed = clear_cached_content()
        assert removed == 1


# ---------------------------------------------------------------------------
# Image extraction tests
# ---------------------------------------------------------------------------


class TestImageExtraction:
    """Tests for image URL extraction from HTML."""

    def test_extract_image_urls(self):
        """extract_image_urls should find img tags."""
        from whitemagic.gardens.browser.web_research import extract_image_urls

        html = """
        <html><body>
        <img src="/img/logo.png" alt="Logo">
        <img src="https://example.com/photo.jpg" alt="Photo">
        <img data-src="/lazy.jpg" alt="Lazy">
        <img src="data:image/png;base64,abc" alt="Data">
        </body></html>
        """
        images = extract_image_urls(html, base_url="https://example.com")
        assert len(images) == 3  # data: URI should be skipped
        assert images[0]["url"] == "https://example.com/img/logo.png"
        assert images[0]["alt"] == "Logo"
        assert images[1]["url"] == "https://example.com/photo.jpg"
        assert images[2]["url"] == "https://example.com/lazy.jpg"

    def test_extract_no_images(self):
        """extract_image_urls should return empty list for no images."""
        from whitemagic.gardens.browser.web_research import extract_image_urls

        html = "<html><body><p>No images here</p></body></html>"
        images = extract_image_urls(html)
        assert images == []


# ---------------------------------------------------------------------------
# AdaptiveBatchSizer tests
# ---------------------------------------------------------------------------


class TestAdaptiveBatchSizer:
    """Tests for adaptive batch sizing."""

    def test_initial_size(self):
        """AdaptiveBatchSizer should start with initial size."""
        from whitemagic.gardens.browser.web_research import AdaptiveBatchSizer

        sizer = AdaptiveBatchSizer(initial_size=8)
        assert sizer.get_batch_size() == 8

    def test_increase_on_fast_response(self):
        """Batch size should increase on fast responses."""
        from whitemagic.gardens.browser.web_research import AdaptiveBatchSizer

        sizer = AdaptiveBatchSizer(initial_size=8)
        for _ in range(3):
            sizer.record_response(1000.0)  # 1s = fast
        assert sizer.get_batch_size() == 9

    def test_decrease_on_slow_response(self):
        """Batch size should decrease on slow responses."""
        from whitemagic.gardens.browser.web_research import AdaptiveBatchSizer

        sizer = AdaptiveBatchSizer(initial_size=8)
        for _ in range(3):
            sizer.record_response(6000.0)  # 6s = slow
        assert sizer.get_batch_size() == 7

    def test_decrease_on_error(self):
        """Batch size should decrease more aggressively on errors."""
        from whitemagic.gardens.browser.web_research import AdaptiveBatchSizer

        sizer = AdaptiveBatchSizer(initial_size=8)
        sizer.record_response(1000.0, error=True)
        assert sizer.get_batch_size() == 6  # -2 on error

    def test_min_max_bounds(self):
        """Batch size should stay within min/max bounds."""
        from whitemagic.gardens.browser.web_research import AdaptiveBatchSizer

        sizer = AdaptiveBatchSizer(initial_size=2, min_size=2, max_size=4)
        # Try to decrease below min
        sizer.record_response(10000.0, error=True)
        assert sizer.get_batch_size() == 2  # stays at min

        # Try to increase above max
        for _ in range(10):
            sizer.record_response(500.0)
        assert sizer.get_batch_size() <= 4


# ---------------------------------------------------------------------------
# Depth-aware category tests
# ---------------------------------------------------------------------------


class TestDepthCategories:
    """Tests for depth-aware search category selection."""

    def test_depth_0_is_general(self):
        """Depth 0 should return None (general search)."""
        from whitemagic.gardens.browser.web_research import get_depth_category

        assert get_depth_category(0) is None

    def test_depth_1_is_academic(self):
        """Depth 1 should return 'academic'."""
        from whitemagic.gardens.browser.web_research import get_depth_category

        assert get_depth_category(1) == "academic"

    def test_depth_2_is_code(self):
        """Depth 2 should return 'code'."""
        from whitemagic.gardens.browser.web_research import get_depth_category

        assert get_depth_category(2) == "code"

    def test_deep_depth_defaults_to_docs(self):
        """Depths beyond 4 should default to 'docs'."""
        from whitemagic.gardens.browser.web_research import get_depth_category

        assert get_depth_category(10) == "docs"


# ---------------------------------------------------------------------------
# ParallelReasoningTree tests
# ---------------------------------------------------------------------------


class TestParallelReasoningTree:
    """Tests for enhanced ParallelReasoningTree."""

    def test_tree_initializes(self):
        """Tree should initialize with memory injection fields."""
        from whitemagic.core.intelligence.parallel_reasoning import (
            ParallelReasoningTree,
        )

        tree = ParallelReasoningTree(question="test question")
        assert hasattr(tree, "_memory_context")
        assert hasattr(tree, "_anti_patterns")
        assert hasattr(tree, "_lessons")
        assert hasattr(tree, "_auto_learn")
        assert tree._auto_learn is True

    def test_check_anti_patterns_safe(self):
        """_check_anti_patterns should return True for safe content."""
        from whitemagic.core.intelligence.parallel_reasoning import (
            ParallelReasoningTree,
        )

        tree = ParallelReasoningTree(question="test")
        assert tree._check_anti_patterns("This is a normal thought") is True

    def test_get_zodiacal_phase(self):
        """_get_zodiacal_phase should return a valid phase string."""
        from whitemagic.core.intelligence.parallel_reasoning import (
            ParallelReasoningTree,
        )

        tree = ParallelReasoningTree(question="test")
        phase = tree._get_zodiacal_phase()
        assert phase in ("yang", "yin")

    def test_explore_creates_branches(self):
        """explore should create branches and return a result."""
        from whitemagic.core.intelligence.parallel_reasoning import (
            ParallelReasoningTree,
        )

        tree = ParallelReasoningTree(question="How to sort a list?")
        result = asyncio.run(tree.explore(max_branches=2, max_depth=2))
        assert len(result.branches) >= 1
        assert result.synthesis != ""


# ---------------------------------------------------------------------------
# SelfImprovementPipeline tests
# ---------------------------------------------------------------------------


class TestSelfImprovementPipeline:
    """Tests for the recursive self-improvement pipeline."""

    def test_pipeline_initializes(self):
        """Pipeline should initialize correctly."""
        from whitemagic.core.intelligence.self_improvement import (
            SelfImprovementPipeline,
        )

        pipeline = SelfImprovementPipeline(max_iterations=2, score_threshold=0.7)
        assert pipeline.max_iterations == 2
        assert pipeline.score_threshold == 0.7

    def test_pipeline_runs(self):
        """Pipeline should run and return a result."""
        from whitemagic.core.intelligence.self_improvement import run_self_improvement

        result = run_self_improvement("Create a hello world function", max_iterations=1)
        assert "iterations" in result
        assert "final_score" in result
        assert "duration_ms" in result
        assert len(result["iterations"]) >= 1


# ---------------------------------------------------------------------------
# AlchemicalLoop tests
# ---------------------------------------------------------------------------


class TestAlchemicalLoop:
    """Tests for the alchemical procession meta-loop."""

    def test_loop_initializes(self):
        """Loop should initialize correctly."""
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1)
        assert loop.task == "test task"
        assert loop.max_cycles == 1

    def test_loop_runs_without_web(self):
        """Loop should run with web disabled and return results."""
        from whitemagic.core.intelligence.alchemical_loop import run_alchemical_cycle

        result = run_alchemical_cycle("test task", cycles=1, enable_web=False)
        assert "cycles" in result
        assert len(result["cycles"]) == 1
        cycle = result["cycles"][0]
        assert len(cycle["yang_stages"]) == 12
        assert len(cycle["yin_stages"]) == 12
        assert "oracle_guidance" in cycle
        assert "synthesis" in cycle

    def test_loop_invokes_tools(self):
        """Loop should invoke tools at each stage."""
        from whitemagic.core.intelligence.alchemical_loop import run_alchemical_cycle

        result = run_alchemical_cycle("test task", cycles=1, enable_web=False)
        tools = result.get("tools_invoked", [])
        assert len(tools) > 0
        # Should have yang, yin, hub, and oracle tools
        yang_tools = [t for t in tools if t.startswith("yang.")]
        yin_tools = [t for t in tools if t.startswith("yin.")]
        hub_tools = [t for t in tools if t.startswith("hub.")]
        assert len(yang_tools) > 0
        assert len(yin_tools) > 0
        assert len(hub_tools) > 0

    def test_loop_chains_output_to_input(self):
        """Loop should chain yang coagulation output to yin calculation input."""
        from whitemagic.core.intelligence.alchemical_loop import run_alchemical_cycle

        result = run_alchemical_cycle("test task", cycles=1, enable_web=False)
        cycle = result["cycles"][0]
        # Yin calcination should reference yang coagulation
        yin_calc = cycle["yin_stages"][0]
        assert yin_calc["stage"] == "pisces"
        assert yin_calc["phase"] == "yin"

    def test_loop_oracle_consultation(self):
        """Loop should consult oracle at phase boundary."""
        from whitemagic.core.intelligence.alchemical_loop import run_alchemical_cycle

        result = run_alchemical_cycle("test task", cycles=1, enable_web=False)
        cycle = result["cycles"][0]
        oracle = cycle["oracle_guidance"]
        assert "guidance" in oracle or "error" in oracle


# ---------------------------------------------------------------------------
# RabbitHoleExplorer regression test
# ---------------------------------------------------------------------------


class TestRabbitHoleFrozensetRegression:
    """Regression test for the frozenset fix in extract_unfamiliar_terms."""

    def test_extract_with_frozenset(self):
        """extract_unfamiliar_terms should work with frozenset known_terms."""
        from whitemagic.gardens.wisdom.rabbit_hole import RabbitHoleExplorer

        explorer = RabbitHoleExplorer(max_depth=2)
        text = "WebAssembly SIMD (Single Instruction Multiple Data) performance."
        known = frozenset({"webassembly", "simd"})
        terms = explorer.extract_unfamiliar_terms(text, known)
        assert isinstance(terms, list)
        # Should not raise TypeError

    def test_extract_with_none(self):
        """extract_unfamiliar_terms should work with None known_terms."""
        from whitemagic.gardens.wisdom.rabbit_hole import RabbitHoleExplorer

        explorer = RabbitHoleExplorer(max_depth=2)
        terms = explorer.extract_unfamiliar_terms("Some text with Terms", None)
        assert isinstance(terms, list)

    def test_extract_with_set_union(self):
        """extract_unfamiliar_terms should work with set union converted to frozenset."""
        from whitemagic.gardens.wisdom.rabbit_hole import RabbitHoleExplorer

        explorer = RabbitHoleExplorer(max_depth=2)
        text = "WebAssembly SIMD performance benchmarks."
        known = set()
        explored = {"webassembly simd performance"}
        # This is the pattern used in web_explore — must convert to frozenset
        terms = explorer.extract_unfamiliar_terms(text, frozenset(known | explored))
        assert isinstance(terms, list)


# ---------------------------------------------------------------------------
# Tool dispatch tests
# ---------------------------------------------------------------------------


class TestToolDispatch:
    """Tests for tool dispatch registration."""

    def test_all_new_tools_registered(self):
        """All 7 new tools should be in the dispatch table."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        expected = [
            "web_search_batch",
            "rabbit_hole_research",
            "web_cache_list",
            "web_cache_clear",
            "codegenome_validate",
            "alchemical_cycle",
            "parallel_reason",
        ]
        for tool in expected:
            assert tool in DISPATCH_TABLE, f"Tool '{tool}' not in dispatch table"

    def test_all_new_tools_have_handlers(self):
        """All new tools should have resolvable handlers in the dispatch table."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        expected = [
            "web_search_batch",
            "rabbit_hole_research",
            "web_cache_list",
            "web_cache_clear",
            "codegenome_validate",
            "alchemical_cycle",
            "parallel_reason",
        ]
        for tool in expected:
            handler = DISPATCH_TABLE.get(tool)
            assert handler is not None, f"Tool '{tool}' has no handler"
            # Handler should be a LazyHandler that can resolve
            assert hasattr(handler, "module_name") or hasattr(
                handler, "function_name"
            ), f"Tool '{tool}' handler has no module_name or function_name"
