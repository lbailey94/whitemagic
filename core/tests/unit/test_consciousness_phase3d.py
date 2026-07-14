"""Tests for Phase 3d consciousness modules: goal graph, emotional steering, self-directed attention."""

import tempfile
from pathlib import Path

import pytest

from whitemagic.core.consciousness.goal_graph import (
    Goal,
    GoalGraph,
    GoalStatus,
    GoalType,
    get_goal_graph,
)
from whitemagic.core.consciousness.emotional_steering import (
    EmotionalSignal,
    EmotionalSteering,
    get_emotional_steering,
)
from whitemagic.core.consciousness.self_initiation import (
    SelfDirectedAttention,
    SelfInitiatedTurn,
    get_self_directed_attention,
)


class TestGoalGraph:
    """Test the goal graph for cross-session intention tracking."""

    def test_create_goal(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        goal = graph.add_goal("g1", "Fix citta tests", GoalType.FIX)
        assert goal.id == "g1"
        assert goal.title == "Fix citta tests"
        assert goal.status == GoalStatus.PROPOSED
        assert goal.goal_type == GoalType.FIX

    def test_update_status(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        graph.add_goal("g1", "Build feature", GoalType.BUILD)
        updated = graph.update_status("g1", GoalStatus.ACTIVE)
        assert updated is not None
        assert updated.status == GoalStatus.ACTIVE

    def test_complete_goal(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        graph.add_goal("g1", "Test feature", GoalType.TEST)
        updated = graph.update_status("g1", GoalStatus.COMPLETED, outcome="All tests pass")
        assert updated is not None
        assert updated.status == GoalStatus.COMPLETED
        assert updated.completed_at is not None
        assert "All tests pass" in updated.outcomes

    def test_dependencies(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        graph.add_goal("g1", "Foundation", GoalType.BUILD)
        graph.add_goal("g2", "Feature", GoalType.BUILD, dependencies=["g1"])
        graph.add_dependency("g2", "g1")
        g2 = graph.get_goal("g2")
        assert "g1" in g2.dependencies
        g1 = graph.get_goal("g1")
        assert "g2" in g1.blocks

    def test_persistence(self, tmp_path):
        path = tmp_path / "goals.json"
        graph1 = GoalGraph(persist_path=path)
        graph1.add_goal("g1", "Persistent goal", GoalType.RESEARCH)
        graph2 = GoalGraph(persist_path=path)
        assert "g1" in graph2._goals
        assert graph2.get_goal("g1").title == "Persistent goal"

    def test_get_active_goals(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        graph.add_goal("g1", "Active", GoalType.BUILD)
        graph.add_goal("g2", "Proposed", GoalType.BUILD)
        graph.update_status("g1", GoalStatus.ACTIVE)
        active = graph.get_active_goals()
        assert len(active) == 1
        assert active[0].id == "g1"

    def test_summary(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        graph.add_goal("g1", "Goal 1", GoalType.BUILD)
        graph.add_goal("g2", "Goal 2", GoalType.FIX)
        graph.update_status("g1", GoalStatus.COMPLETED)
        summary = graph.get_summary()
        assert summary["total_goals"] == 2
        assert summary["completed"] == 1
        assert summary["completion_rate"] == 0.5

    def test_goal_type_string(self, tmp_path):
        graph = GoalGraph(persist_path=tmp_path / "goals.json")
        goal = graph.add_goal("g1", "Test", "build")
        assert goal.goal_type == GoalType.BUILD


class TestEmotionalSteering:
    """Test emotional steering signals."""

    def test_initial_state(self):
        steering = EmotionalSteering()
        state = steering.get_state()
        assert state["frustration"] == 0.0
        assert state["curiosity"] == 0.0
        assert state["satisfaction"] == 0.0
        assert state["dominant"] is None

    def test_frustration_from_errors(self):
        steering = EmotionalSteering()
        for _ in range(8):
            steering.record_error()
        assert steering.state.frustration > 0.5

    def test_frustration_from_retries(self):
        steering = EmotionalSteering()
        steering.record_retry(5)
        assert steering.state.frustration >= 0.3

    def test_satisfaction_from_success(self):
        steering = EmotionalSteering()
        for _ in range(10):
            steering.record_success()
        assert steering.state.satisfaction > 0.5

    def test_curiosity_from_unexplored(self):
        steering = EmotionalSteering()
        for i in range(10):
            steering.record_memory_access(f"mem_{i}", f"cluster_{i}")
        assert steering.state.curiosity > 0.0

    def test_impulse_generation(self):
        steering = EmotionalSteering()
        for _ in range(10):
            steering.record_error()
        impulse = steering.get_impulse()
        if impulse:
            assert impulse["signal"] == "frustration"
            assert impulse["action"] == "try_new_approach"

    def test_reset(self):
        steering = EmotionalSteering()
        steering.record_error()
        steering.record_error()
        steering.reset()
        assert steering.state.frustration == 0.0

    def test_tool_call_tracking(self):
        steering = EmotionalSteering()
        for _ in range(8):
            steering.record_tool_call(success=False)
        assert steering.state.frustration > 0.3
        for _ in range(20):
            steering.record_tool_call(success=True)
        assert steering.state.satisfaction > 0.3


class TestSelfDirectedAttention:
    """Test self-directed attention and internal action generation."""

    def test_observe_no_goals(self, tmp_path, monkeypatch):
        # Patch goal graph to use temp path
        import whitemagic.core.consciousness.goal_graph as gg_mod
        original_get = gg_mod.get_goal_graph
        test_graph = GoalGraph(persist_path=tmp_path / "goals.json")
        monkeypatch.setattr(gg_mod, "get_goal_graph", lambda: test_graph)

        sda = SelfDirectedAttention()
        sda._last_observation = 0  # Force observation
        turns = sda.observe_and_generate()
        assert len(turns) > 0
        assert any(t.action_type == "connect" for t in turns)

    def test_observe_blocked_goals(self, tmp_path, monkeypatch):
        import whitemagic.core.consciousness.goal_graph as gg_mod
        import whitemagic.core.consciousness.emotional_steering as es_mod
        import whitemagic.core.consciousness.self_initiation as sda_mod
        test_graph = GoalGraph(persist_path=tmp_path / "goals.json")
        test_graph.add_goal("g1", "Blocked goal", GoalType.BUILD)
        test_graph.update_status("g1", GoalStatus.BLOCKED)
        monkeypatch.setattr(gg_mod, "get_goal_graph", lambda: test_graph)
        # Reset emotional steering to avoid interference
        test_steering = EmotionalSteering()
        monkeypatch.setattr(es_mod, "get_emotional_steering", lambda: test_steering)
        monkeypatch.setattr(sda_mod, "es_mod", es_mod)
        monkeypatch.setattr(sda_mod, "gg_mod", gg_mod)

        sda = SelfDirectedAttention()
        sda._last_observation = 0
        turns = sda.observe_and_generate()
        assert any(t.action_type == "fix" for t in turns)

    def test_observe_proposed_goals(self, tmp_path, monkeypatch):
        import whitemagic.core.consciousness.goal_graph as gg_mod
        import whitemagic.core.consciousness.emotional_steering as es_mod
        import whitemagic.core.consciousness.self_initiation as sda_mod
        test_graph = GoalGraph(persist_path=tmp_path / "goals.json")
        test_graph.add_goal("g1", "Proposed goal", GoalType.BUILD)
        monkeypatch.setattr(gg_mod, "get_goal_graph", lambda: test_graph)
        # Reset emotional steering to avoid interference
        test_steering = EmotionalSteering()
        monkeypatch.setattr(es_mod, "get_emotional_steering", lambda: test_steering)
        monkeypatch.setattr(sda_mod, "es_mod", es_mod)
        monkeypatch.setattr(sda_mod, "gg_mod", gg_mod)

        sda = SelfDirectedAttention()
        sda._last_observation = 0
        turns = sda.observe_and_generate()
        assert any(t.action_type == "build" for t in turns)

    def test_observation_interval(self, tmp_path, monkeypatch):
        import whitemagic.core.consciousness.goal_graph as gg_mod
        test_graph = GoalGraph(persist_path=tmp_path / "goals.json")
        monkeypatch.setattr(gg_mod, "get_goal_graph", lambda: test_graph)

        sda = SelfDirectedAttention()
        sda._last_observation = 0
        turns1 = sda.observe_and_generate()
        assert len(turns1) > 0
        turns2 = sda.observe_and_generate()
        assert len(turns2) == 0  # Interval not elapsed

    def test_summary(self, tmp_path, monkeypatch):
        import whitemagic.core.consciousness.goal_graph as gg_mod
        test_graph = GoalGraph(persist_path=tmp_path / "goals.json")
        monkeypatch.setattr(gg_mod, "get_goal_graph", lambda: test_graph)

        sda = SelfDirectedAttention()
        sda._last_observation = 0
        sda.observe_and_generate()
        summary = sda.get_summary()
        assert summary["total_generated"] > 0
        assert "by_type" in summary

    def test_mark_acted_on(self, tmp_path, monkeypatch):
        import whitemagic.core.consciousness.goal_graph as gg_mod
        test_graph = GoalGraph(persist_path=tmp_path / "goals.json")
        monkeypatch.setattr(gg_mod, "get_goal_graph", lambda: test_graph)

        sda = SelfDirectedAttention()
        sda._last_observation = 0
        sda.observe_and_generate()
        sda.mark_acted_on(0)
        turns = sda.get_generated_turns()
        assert turns[0].acted_on is True
