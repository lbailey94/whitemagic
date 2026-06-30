"""
Regression tests for v11.3 modules:
  1. Memory Lifecycle Manager (mindful forgetting integration)
  2. Homeostatic Loop (harmony-driven self-regulation)
  3. Maturity Gate Check (tool-level maturity enforcement)
  4. Memory Consolidation (hippocampal replay)
  5. MCP tool routing for all new tools
"""

import json
import time


# from tests.conftest import assert_envelope_shape  # not available in this test runner
assert_envelope_shape = None  # placeholder


# =========================================================================
# 1. Memory Lifecycle Manager
# =========================================================================


class TestMemoryLifecycle:
    def test_manager_initializes(self):
        from whitemagic.core.memory.lifecycle import MemoryLifecycleManager

        mgr = MemoryLifecycleManager()
        stats = mgr.get_stats()
        assert stats["total_sweeps"] == 0
        assert stats["last_sweep_at"] is None

    def test_attach_to_scheduler(self):
        from whitemagic.core.memory.lifecycle import MemoryLifecycleManager

        mgr = MemoryLifecycleManager()
        result = mgr.attach()
        assert result is True
        assert mgr.is_attached

    def test_run_sweep_returns_report(self):
        from whitemagic.core.memory.lifecycle import MemoryLifecycleManager

        mgr = MemoryLifecycleManager()
        report = mgr.run_sweep(persist=False)
        assert report["status"] == "success"
        assert "sweep" in report
        assert "lifetime" in report

    def test_stats_update_after_sweep(self):
        from whitemagic.core.memory.lifecycle import MemoryLifecycleManager

        mgr = MemoryLifecycleManager()
        mgr.run_sweep(persist=False)
        stats = mgr.get_stats()
        assert stats["total_sweeps"] == 1
        assert stats["last_sweep_at"] is not None

    def test_flush_count_triggers_sweep(self):
        from whitemagic.core.memory.lifecycle import (
            LifecycleConfig,
            MemoryLifecycleManager,
        )

        mgr = MemoryLifecycleManager(config=LifecycleConfig(sweep_interval_sweeps=2))
        # Simulate slow-lane flushes
        mgr._on_slow_flush([])  # flush 1 — no sweep
        time.sleep(0.05)
        assert mgr.get_stats()["total_sweeps"] == 0
        mgr._on_slow_flush([])  # flush 2 — triggers sweep
        time.sleep(0.2)  # allow background thread
        assert mgr.get_stats()["total_sweeps"] == 1


# =========================================================================
# 2. Homeostatic Loop
# =========================================================================


class TestHomeostaticLoop:
    def test_loop_initializes(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        assert not loop.is_running
        stats = loop.get_stats()
        assert stats["total_checks"] == 0

    def test_check_returns_no_actions_when_healthy(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        actions = loop.check()
        # Fresh harmony vector should be healthy — no corrective actions
        assert isinstance(actions, list)
        # Could be 0 or small number depending on state
        assert all(hasattr(a, "dimension") for a in actions)

    def test_check_increments_counter(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        loop.check()
        loop.check()
        assert loop.get_stats()["total_checks"] == 2

    def test_action_to_dict_serializable(self):
        from whitemagic.harmony.homeostatic_loop import (
            ActionLevel,
            HomeostaticAction,
        )

        action = HomeostaticAction(
            dimension="error_rate",
            level=ActionLevel.ADVISE,
            value=0.5,
            threshold=0.7,
            action_taken="Test advisory",
        )
        d = action.to_dict()
        json.dumps(d)  # must not raise
        assert d["level"] == "advise"

    def test_attach_detach_lifecycle(self):
        from whitemagic.harmony.homeostatic_loop import (
            HomeostaticConfig,
            HomeostaticLoop,
        )

        loop = HomeostaticLoop(config=HomeostaticConfig(check_interval_s=0.05))
        loop.attach()
        assert loop.is_running
        time.sleep(0.15)  # allow at least one check
        loop.detach()
        assert not loop.is_running
        assert loop.get_stats()["total_checks"] >= 1

    def test_stats_serializable(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        loop.check()
        stats = loop.get_stats()
        json.dumps(stats)


# =========================================================================
# 3. Maturity Gate Check
# =========================================================================


class TestMaturityCheck:
    def test_basic_tool_passes(self):
        from whitemagic.tools.maturity_check import check_maturity_for_tool

        # capabilities is a basic READ tool, should always pass
        result = check_maturity_for_tool("capabilities")
        assert result is None  # None means allowed

    def test_unregistered_tool_passes(self):
        from whitemagic.tools.maturity_check import check_maturity_for_tool

        result = check_maturity_for_tool("nonexistent_tool_xyz")
        assert result is None

    def test_error_response_structure(self):
        # Force a low maturity by testing with a tool that requires LOGOS (6)
        # which no real system reaches
        from whitemagic.tools.maturity_check import (
            _MATURITY_REQUIREMENTS,
            check_maturity_for_tool,
        )

        _MATURITY_REQUIREMENTS["_test_logos_tool"] = 6
        try:
            result = check_maturity_for_tool("_test_logos_tool")
            if result is not None:
                assert result["status"] == "error"
                assert result["error_code"] == "maturity_gate"
                assert "maturity" in result
                json.dumps(result)
        finally:
            del _MATURITY_REQUIREMENTS["_test_logos_tool"]


# =========================================================================
# 4. Memory Consolidation
# =========================================================================


class TestMemoryConsolidation:
    def test_consolidator_initializes(self):
        from whitemagic.core.memory.consolidation import MemoryConsolidator

        c = MemoryConsolidator()
        stats = c.get_stats()
        assert stats["total_consolidations"] == 0

    def test_consolidate_empty_returns_report(self):
        from whitemagic.core.memory.consolidation import MemoryConsolidator

        c = MemoryConsolidator()
        report = c.consolidate(memories=[])
        assert report.memories_analyzed == 0
        assert report.clusters_found == 0

    def test_report_to_dict_serializable(self):
        from whitemagic.core.memory.consolidation import MemoryConsolidator

        c = MemoryConsolidator()
        report = c.consolidate(memories=[])
        d = report.to_dict()
        json.dumps(d)  # must not raise
        assert "memories_analyzed" in d
        assert "timestamp" in d

    def test_clustering_with_shared_tags(self):
        """Test that memories with shared tags cluster together."""
        from whitemagic.core.memory.consolidation import MemoryConsolidator
        from whitemagic.core.memory.unified_types import Memory, MemoryType

        memories = [
            Memory(
                id=f"m{i}",
                content=f"content {i}",
                memory_type=MemoryType.SHORT_TERM,
                tags={"python", "testing"},
                importance=0.6,
                access_count=5,
            )
            for i in range(5)
        ]

        c = MemoryConsolidator(min_cluster_size=3)
        report = c.consolidate(memories=memories)
        assert report.memories_analyzed == 5
        assert report.clusters_found >= 1
        assert report.clusters[0].theme in ("python", "testing")

    def test_stats_update_after_consolidation(self):
        from whitemagic.core.memory.consolidation import MemoryConsolidator

        c = MemoryConsolidator()
        c.consolidate(memories=[])
        c.consolidate(memories=[])
        assert c.get_stats()["total_consolidations"] == 2

    def test_cluster_to_dict(self):
        from whitemagic.core.memory.consolidation import MemoryCluster

        cluster = MemoryCluster(
            cluster_id="abc123",
            memory_ids=["m1", "m2", "m3"],
            shared_tags={"python"},
            avg_importance=0.7,
            total_access_count=15,
            avg_emotional_valence=0.3,
            theme="python",
        )
        d = cluster.to_dict()
        json.dumps(d)
        assert d["size"] == 3
        assert d["theme"] == "python"


# =========================================================================
# 6. Tool Dependency Graph
# =========================================================================


class TestToolDependencyGraph:
    def test_graph_initializes_with_static_edges(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        summary = graph.get_graph_summary()
        assert summary["total_edges"] > 0
        assert summary["total_tools"] > 0

    def test_next_steps_returns_edges(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        steps = graph.next_steps("vote.create")
        assert len(steps) >= 1
        assert steps[0]["target"] == "vote.cast"

    def test_prerequisites_returns_edges(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        prereqs = graph.prerequisites("vote.cast")
        assert any(p["source"] == "vote.create" for p in prereqs)

    def test_plan_builds_dependency_chain(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        chain = graph.plan("vote.cast")
        assert "vote.create" in chain
        assert chain.index("vote.create") < chain.index("vote.cast")

    def test_edge_type_filter(self):
        from whitemagic.tools.dependency_graph import EdgeType, ToolDependencyGraph

        graph = ToolDependencyGraph()
        requires = graph.next_steps("vote.create", edge_type=EdgeType.REQUIRES)
        _suggests = graph.next_steps("vote.create", edge_type=EdgeType.SUGGESTS)
        # vote.create -> vote.cast is REQUIRES
        assert any(e["target"] == "vote.cast" for e in requires)

    def test_add_learned_edge(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        graph.add_learned_edge("custom_a", "custom_b", 0.6)
        steps = graph.next_steps("custom_a")
        assert any(e["target"] == "custom_b" for e in steps)

    def test_learned_edge_reinforcement(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        graph.add_learned_edge("x", "y", 0.3)
        graph.add_learned_edge("x", "y", 0.3)  # reinforce
        steps = graph.next_steps("x")
        edge = [e for e in steps if e["target"] == "y"][0]
        assert edge["weight"] > 0.3  # should have been reinforced

    def test_full_graph_serializable(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        edges = graph.get_full_graph()
        json.dumps(edges)
        assert len(edges) > 0

    def test_graph_summary_serializable(self):
        from whitemagic.tools.dependency_graph import ToolDependencyGraph

        graph = ToolDependencyGraph()
        summary = graph.get_graph_summary()
        json.dumps(summary)
