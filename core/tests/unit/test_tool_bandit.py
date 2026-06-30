"""Tests for Thompson sampling tool bandit."""

from whitemagic.tools.handlers.tool_bandit import (
    ToolBandit,
    ToolStats,
    get_tool_bandit,
    reset_tool_bandit,
)


class TestToolStats:
    def test_default_prior(self):
        stats = ToolStats()
        assert stats.alpha == 1.0
        assert stats.beta == 1.0
        assert stats.total_calls == 0
        assert stats.expected_value() == 0.5

    def test_sample_in_range(self):
        stats = ToolStats(alpha=5.0, beta=2.0)
        for _ in range(100):
            s = stats.sample()
            assert 0.0 <= s <= 1.0

    def test_expected_value_after_outcomes(self):
        stats = ToolStats(alpha=1.0, beta=1.0)
        # 8 successes, 2 failures
        stats.alpha = 9.0
        stats.beta = 3.0
        assert abs(stats.expected_value() - 0.75) < 0.01


class TestToolBandit:
    def setup_method(self):
        reset_tool_bandit()
        self.bandit = ToolBandit()

    def test_register_tool(self):
        self.bandit.register_tool("memory.search")
        stats = self.bandit.get_tool_stats("memory.search")
        assert stats is not None
        assert stats["alpha"] == 1.0
        assert stats["beta"] == 1.0

    def test_register_tools_batch(self):
        self.bandit.register_tools(["tool_a", "tool_b", "tool_c"])
        assert self.bandit.get_tool_stats("tool_a") is not None
        assert self.bandit.get_tool_stats("tool_b") is not None
        assert self.bandit.get_tool_stats("tool_c") is not None

    def test_record_success(self):
        self.bandit.register_tool("test_tool")
        self.bandit.record_outcome("test_tool", success=True)
        stats = self.bandit.get_tool_stats("test_tool")
        assert stats["total_calls"] == 1
        assert stats["total_successes"] == 1
        assert stats["alpha"] == 2.0
        assert stats["beta"] == 1.0

    def test_record_failure(self):
        self.bandit.register_tool("test_tool")
        self.bandit.record_outcome("test_tool", success=False)
        stats = self.bandit.get_tool_stats("test_tool")
        assert stats["total_calls"] == 1
        assert stats["total_failures"] == 1
        assert stats["alpha"] == 1.0
        assert stats["beta"] == 2.0

    def test_record_auto_registers(self):
        self.bandit.record_outcome("new_tool", success=True)
        stats = self.bandit.get_tool_stats("new_tool")
        assert stats is not None
        assert stats["total_successes"] == 1

    def test_record_with_task_type(self):
        self.bandit.register_tool("test_tool")
        self.bandit.record_outcome("test_tool", success=True, task_type="memory_search")
        self.bandit.record_outcome("test_tool", success=True, task_type="memory_search")
        self.bandit.record_outcome("test_tool", success=False, task_type="analysis")
        stats = self.bandit.get_tool_stats("test_tool")
        assert stats["total_calls"] == 3
        # Task-type specific posteriors should differ
        assert "memory_search" in self.bandit._tools["test_tool"].task_type_stats
        assert "analysis" in self.bandit._tools["test_tool"].task_type_stats

    def test_recommend_tools_empty(self):
        recs = self.bandit.recommend_tools(k=5)
        assert recs == []

    def test_recommend_tools_returns_k(self):
        self.bandit.register_tools(["a", "b", "c", "d", "e", "f", "g"])
        recs = self.bandit.recommend_tools(k=3)
        assert len(recs) == 3
        assert all("tool" in r for r in recs)
        assert all("sample" in r for r in recs)

    def test_recommend_tools_sorted_by_sample(self):
        self.bandit.register_tools(["a", "b", "c"])
        # Make "b" clearly better
        for _ in range(20):
            self.bandit.record_outcome("b", success=True)
        for _ in range(20):
            self.bandit.record_outcome("a", success=False)
        # Run many recommendations — "b" should be first most of the time
        b_first_count = 0
        for _ in range(100):
            recs = self.bandit.recommend_tools(k=3)
            if recs[0]["tool"] == "b":
                b_first_count += 1
        assert b_first_count > 80  # Should be first >80% of the time

    def test_recommend_with_task_type(self):
        self.bandit.register_tools(["memory.search", "graph.query"])
        # Make memory.search good for memory_search tasks
        for _ in range(10):
            self.bandit.record_outcome(
                "memory.search", success=True, task_type="memory_search"
            )
        # Make graph.query bad for memory_search tasks
        for _ in range(10):
            self.bandit.record_outcome(
                "graph.query", success=False, task_type="memory_search"
            )
        recs = self.bandit.recommend_tools(k=2, task_type="memory_search")
        assert recs[0]["tool"] == "memory.search"

    def test_classify_task_type(self):
        assert self.bandit.classify_task_type("search my memories") == "memory_search"
        assert self.bandit.classify_task_type("analyze the data") == "analysis"
        assert self.bandit.classify_task_type("write a poem") == "creation"
        assert self.bandit.classify_task_type("check dharma compliance") == "governance"
        assert self.bandit.classify_task_type("run dream cycle") == "dreaming"
        assert (
            self.bandit.classify_task_type("find associations in graph")
            == "knowledge_graph"
        )
        assert self.bandit.classify_task_type("create a plan") == "planning"
        assert self.bandit.classify_task_type("hello world") == "general"

    def test_get_top_tools(self):
        self.bandit.register_tools(["good", "bad", "neutral"])
        for _ in range(10):
            self.bandit.record_outcome("good", success=True)
        for _ in range(10):
            self.bandit.record_outcome("bad", success=False)
        for _ in range(5):
            self.bandit.record_outcome("neutral", success=True)
        for _ in range(5):
            self.bandit.record_outcome("neutral", success=False)
        top = self.bandit.get_top_tools(n=3)
        assert len(top) == 3
        assert top[0]["tool"] == "good"
        assert top[0]["expected_value"] > 0.8

    def test_get_top_tools_excludes_uncalled(self):
        self.bandit.register_tools(["called", "uncalled"])
        self.bandit.record_outcome("called", success=True)
        top = self.bandit.get_top_tools(n=5)
        assert len(top) == 1  # Only "called" has data
        assert top[0]["tool"] == "called"

    def test_to_dict_summary(self):
        self.bandit.register_tools(["a", "b"])
        self.bandit.record_outcome("a", success=True)
        summary = self.bandit.to_dict()
        assert summary["total_tools"] == 2
        assert summary["tools_with_data"] == 1
        assert summary["total_calls"] == 1
        assert len(summary["top_tools"]) == 1

    def test_singleton(self):
        b1 = get_tool_bandit()
        b2 = get_tool_bandit()
        assert b1 is b2


class TestBanditExploration:
    def test_cold_start_uniform(self):
        """All tools with no data should have equal chance of being recommended."""
        bandit = ToolBandit()
        bandit.register_tools(["a", "b", "c"])
        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(300):
            recs = bandit.recommend_tools(k=1)
            counts[recs[0]["tool"]] += 1
        # With uniform priors, each should appear roughly 1/3 of the time
        for count in counts.values():
            assert 60 < count < 140  # Allow variance

    def test_exploration_vs_exploitation(self):
        """After many outcomes, the bandit should mostly exploit but still explore."""
        bandit = ToolBandit()
        bandit.register_tools(["best", "mediocre", "worst"])
        for _ in range(50):
            bandit.record_outcome("best", success=True)
        for _ in range(25):
            bandit.record_outcome("mediocre", success=True)
        for _ in range(25):
            bandit.record_outcome("mediocre", success=False)
        for _ in range(50):
            bandit.record_outcome("worst", success=False)

        best_count = 0
        for _ in range(100):
            recs = bandit.recommend_tools(k=1)
            if recs[0]["tool"] == "best":
                best_count += 1
        # Should pick "best" most of the time (>90%)
        assert best_count > 90
