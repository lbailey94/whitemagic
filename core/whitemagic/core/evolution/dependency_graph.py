"""W-Relational Axis for Improvement Dependencies (Objective U).

Builds an improvement dependency graph using the w-axis (relational).
Models conditional probabilities: P(B works | A applied) vs P(B works | A not applied).

Edge types:
- prerequisite: A must be done before B can be evaluated
- synergy: A and B together produce more than A + B separately
- conflict: A and B cannot both be applied
- independence: A and B don't interact

This is proper causal graph reasoning (do-calculus in Pearl's framework).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DependencyType(Enum):
    """Type of dependency between two improvements."""
    PREREQUISITE = "prerequisite"
    SYNERGY = "synergy"
    CONFLICT = "conflict"
    INDEPENDENCE = "independence"


@dataclass
class DependencyEdge:
    """An edge in the improvement dependency graph."""
    source_id: str  # A
    target_id: str  # B
    edge_type: DependencyType
    p_b_given_a: float = 0.5      # P(B succeeds | A applied)
    p_b_given_not_a: float = 0.5  # P(B succeeds | A not applied)
    co_occurrences: int = 0
    confirmed: bool = False  # True if conditional probs differ significantly
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def causal_effect(self) -> float:
        """Causal effect of A on B.

        effect = P(B|A) - P(B|¬A)
        >0 = A helps B, <0 = A hurts B, ≈0 = independent
        """
        return self.p_b_given_a - self.p_b_given_not_a

    @property
    def is_confirmed_dependency(self) -> bool:
        """True if the causal effect is significant (|effect| > 0.1)."""
        return abs(self.causal_effect) > 0.1 and self.co_occurrences >= 2


class DependencyGraph:
    """Improvement dependency graph for causal reasoning.

    Tracks conditional probabilities between improvements and models
    prerequisite, synergy, conflict, and independence relationships.
    """

    def __init__(self) -> None:
        self._edges: dict[tuple[str, str], DependencyEdge] = {}
        self._nodes: set[str] = set()

    def add_node(self, node_id: str) -> None:
        """Register a node in the graph."""
        self._nodes.add(node_id)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: DependencyType = DependencyType.INDEPENDENCE,
    ) -> DependencyEdge:
        """Add or update an edge between two improvements.

        Args:
            source_id: Source improvement (A).
            target_id: Target improvement (B).
            edge_type: Type of dependency.

        Returns:
            The created/updated edge.
        """
        self.add_node(source_id)
        self.add_node(target_id)
        key = (source_id, target_id)
        edge = DependencyEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
        )
        self._edges[key] = edge
        return edge

    def get_edge(self, source_id: str, target_id: str) -> DependencyEdge | None:
        return self._edges.get((source_id, target_id))

    def update_conditional_probability(
        self,
        source_id: str,
        target_id: str,
        a_applied: bool,
        b_succeeded: bool,
    ) -> DependencyEdge:
        """Update conditional probability P(B|A) from observed outcome.

        Args:
            source_id: Improvement A.
            target_id: Improvement B.
            a_applied: Whether A was applied.
            b_succeeded: Whether B succeeded.

        Returns:
            Updated edge.
        """
        key = (source_id, target_id)
        edge = self._edges.get(key)
        if edge is None:
            edge = self.add_edge(source_id, target_id)

        edge.co_occurrences += 1

        # Update conditional probability using running average
        if a_applied:
            # Update P(B|A)
            n = edge.co_occurrences
            edge.p_b_given_a = ((n - 1) * edge.p_b_given_a + (1.0 if b_succeeded else 0.0)) / n
        else:
            # Update P(B|¬A)
            n = edge.co_occurrences
            edge.p_b_given_not_a = ((n - 1) * edge.p_b_given_not_a + (1.0 if b_succeeded else 0.0)) / n

        # Update edge type based on causal effect
        if edge.is_confirmed_dependency:
            effect = edge.causal_effect
            if effect > 0.15:
                edge.edge_type = DependencyType.SYNERGY
            elif effect < -0.15:
                edge.edge_type = DependencyType.CONFLICT
            else:
                edge.edge_type = DependencyType.INDEPENDENCE
            edge.confirmed = True

        return edge

    def get_prerequisites(self, target_id: str) -> list[str]:
        """Get all prerequisites for a given improvement.

        Args:
            target_id: The improvement to check.

        Returns:
            List of prerequisite improvement IDs.
        """
        return [
            edge.source_id for edge in self._edges.values()
            if edge.target_id == target_id and edge.edge_type == DependencyType.PREREQUISITE
        ]

    def get_synergies(self, source_id: str) -> list[str]:
        """Get all improvements that synergize with the given one."""
        return [
            edge.target_id for edge in self._edges.values()
            if edge.source_id == source_id and edge.edge_type == DependencyType.SYNERGY
        ]

    def get_conflicts(self, source_id: str) -> list[str]:
        """Get all improvements that conflict with the given one."""
        return [
            edge.target_id for edge in self._edges.values()
            if edge.source_id == source_id and edge.edge_type == DependencyType.CONFLICT
        ]

    def topological_order(self) -> list[str]:
        """Compute topological ordering of improvements.

        Prerequisites come before dependents. Useful for determining
        the order in which to apply improvements.

        Returns:
            List of node IDs in topological order.
        """
        # Build adjacency list for prerequisites
        adj: dict[str, list[str]] = {n: [] for n in self._nodes}
        in_degree: dict[str, int] = {n: 0 for n in self._nodes}

        for edge in self._edges.values():
            if edge.edge_type == DependencyType.PREREQUISITE:
                adj[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        # Kahn's algorithm
        queue = [n for n in self._nodes if in_degree.get(n, 0) == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add any remaining nodes (cycles or disconnected)
        for n in self._nodes:
            if n not in order:
                order.append(n)

        return order

    def get_all_edges(self) -> list[DependencyEdge]:
        return list(self._edges.values())

    def get_nodes(self) -> set[str]:
        return set(self._nodes)

    def get_stats(self) -> dict[str, Any]:
        type_counts = {t.value: 0 for t in DependencyType}
        for edge in self._edges.values():
            type_counts[edge.edge_type.value] += 1
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "edge_types": type_counts,
            "confirmed_dependencies": sum(1 for e in self._edges.values() if e.confirmed),
        }
