"""Tests for Objective U — W-Relational Axis for Improvement Dependencies."""

from __future__ import annotations

from whitemagic.core.evolution.dependency_graph import (
    DependencyGraph,
    DependencyType,
)


class TestDependencyGraph:
    def test_add_node(self):
        g = DependencyGraph()
        g.add_node("h1")
        assert "h1" in g.get_nodes()

    def test_add_edge(self):
        g = DependencyGraph()
        edge = g.add_edge("h1", "h2", DependencyType.PREREQUISITE)
        assert edge.source_id == "h1"
        assert edge.target_id == "h2"
        assert edge.edge_type == DependencyType.PREREQUISITE

    def test_get_edge(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2", DependencyType.SYNERGY)
        edge = g.get_edge("h1", "h2")
        assert edge is not None
        assert edge.edge_type == DependencyType.SYNERGY

    def test_get_edge_none(self):
        g = DependencyGraph()
        assert g.get_edge("h1", "h2") is None


class TestConditionalProbability:
    def test_update_p_b_given_a(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2")
        # A applied, B succeeded
        g.update_conditional_probability("h1", "h2", a_applied=True, b_succeeded=True)
        edge = g.get_edge("h1", "h2")
        assert edge.p_b_given_a > 0.5

    def test_update_p_b_given_not_a(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2")
        # A not applied, B failed
        g.update_conditional_probability("h1", "h2", a_applied=False, b_succeeded=False)
        edge = g.get_edge("h1", "h2")
        assert edge.p_b_given_not_a < 0.5

    def test_causal_effect(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2")
        edge = g.get_edge("h1", "h2")
        edge.p_b_given_a = 0.8
        edge.p_b_given_not_a = 0.3
        assert abs(edge.causal_effect - 0.5) < 1e-6

    def test_confirmed_dependency(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2")
        edge = g.get_edge("h1", "h2")
        edge.p_b_given_a = 0.9
        edge.p_b_given_not_a = 0.2
        edge.co_occurrences = 5
        assert edge.is_confirmed_dependency

    def test_not_confirmed_low_co_occurrences(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2")
        edge = g.get_edge("h1", "h2")
        edge.p_b_given_a = 0.9
        edge.p_b_given_not_a = 0.2
        edge.co_occurrences = 1
        assert not edge.is_confirmed_dependency

    def test_edge_type_updates_to_synergy(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2")
        # Simulate multiple outcomes where A helps B
        for _ in range(5):
            g.update_conditional_probability(
                "h1", "h2", a_applied=True, b_succeeded=True
            )
        for _ in range(5):
            g.update_conditional_probability(
                "h1", "h2", a_applied=False, b_succeeded=False
            )
        edge = g.get_edge("h1", "h2")
        assert edge.edge_type == DependencyType.SYNERGY


class TestGraphQueries:
    def test_prerequisites(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2", DependencyType.PREREQUISITE)
        g.add_edge("h1", "h3", DependencyType.PREREQUISITE)
        g.add_edge("h2", "h3", DependencyType.SYNERGY)
        prereqs = g.get_prerequisites("h3")
        assert "h1" in prereqs
        assert "h2" not in prereqs  # h2 is synergy, not prerequisite

    def test_synergies(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2", DependencyType.SYNERGY)
        g.add_edge("h1", "h3", DependencyType.CONFLICT)
        syns = g.get_synergies("h1")
        assert "h2" in syns
        assert "h3" not in syns

    def test_conflicts(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2", DependencyType.CONFLICT)
        g.add_edge("h1", "h3", DependencyType.SYNERGY)
        conflicts = g.get_conflicts("h1")
        assert "h2" in conflicts
        assert "h3" not in conflicts


class TestTopologicalOrder:
    def test_simple_order(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2", DependencyType.PREREQUISITE)
        g.add_edge("h2", "h3", DependencyType.PREREQUISITE)
        order = g.topological_order()
        assert order.index("h1") < order.index("h2")
        assert order.index("h2") < order.index("h3")

    def test_no_dependencies(self):
        g = DependencyGraph()
        g.add_node("h1")
        g.add_node("h2")
        order = g.topological_order()
        assert len(order) == 2


class TestStats:
    def test_stats(self):
        g = DependencyGraph()
        g.add_edge("h1", "h2", DependencyType.PREREQUISITE)
        g.add_edge("h2", "h3", DependencyType.SYNERGY)
        stats = g.get_stats()
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2
        assert stats["edge_types"]["prerequisite"] == 1
        assert stats["edge_types"]["synergy"] == 1
