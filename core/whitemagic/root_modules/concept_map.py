# ruff: noqa: BLE001
"""
Concept Mapping System — Graph-based concept relationships.

Provides a graph-based system for mapping concepts and their relationships,
with visualization and analysis capabilities.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConceptMap:
    """Graph-based concept relationship mapping."""

    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []

    def add_node(self, concept: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a concept node."""
        self._nodes[concept] = metadata or {}

    def add_edge(self, source: str, target: str, relation: str = "related", weight: float = 1.0) -> None:
        """Add a relationship edge between concepts."""
        self._edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
        })

    def get_node(self, concept: str) -> dict[str, Any] | None:
        return self._nodes.get(concept)

    def get_neighbors(self, concept: str) -> list[str]:
        """Get all concepts directly connected to a concept."""
        neighbors: set[str] = set()
        for edge in self._edges:
            if edge["source"] == concept:
                neighbors.add(edge["target"])
            elif edge["target"] == concept:
                neighbors.add(edge["source"])
        return list(neighbors)

    def find_path(self, start: str, end: str) -> list[str] | None:
        """Find shortest path between two concepts (BFS)."""
        if start not in self._nodes or end not in self._nodes:
            return None
        if start == end:
            return [start]

        visited: set[str] = {start}
        queue: list[list[str]] = [[start]]

        while queue:
            path = queue.pop(0)
            node = path[-1]
            for neighbor in self.get_neighbors(node):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def clusters(self) -> list[list[str]]:
        """Find connected clusters of concepts."""
        visited: set[str] = set()
        clusters: list[list[str]] = []

        for node in self._nodes:
            if node in visited:
                continue
            cluster: list[str] = []
            queue = [node]
            while queue:
                n = queue.pop(0)
                if n in visited:
                    continue
                visited.add(n)
                cluster.append(n)
                queue.extend(self.get_neighbors(n))
            clusters.append(cluster)
        return clusters

    def summary(self) -> dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "clusters": len(self.clusters()),
        }


_map: ConceptMap | None = None


def get_concept_map() -> ConceptMap:
    global _map
    if _map is None:
        _map = ConceptMap()
    return _map
