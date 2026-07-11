"""Vulnerability knowledge graph — cross-link findings, patterns, and exploit chains."""
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    node_id: str
    node_type: str  # vulnerability, pattern, exploit, contract, function, finding
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str  # exploits, requires, enables, similar_to, leads_to
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)


class VulnerabilityGraph:
    """Directed graph of vulnerabilities, exploit chains, and cross-domain patterns."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[str]] = defaultdict(list)

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)
        self._adjacency[edge.source].append(edge.target)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def find_exploit_chains(self, start_vuln: str, max_depth: int = 5) -> list[list[str]]:
        """Find all exploit chains starting from a vulnerability node."""
        chains: list[list[str]] = []
        self._dfs(start_vuln, [], chains, max_depth, set())
        return chains

    def _dfs(self, node: str, path: list[str], chains: list[list[str]], max_depth: int, visited: set[str]) -> None:
        if len(path) >= max_depth:
            chains.append(path[:])
            return
        if node in visited:
            chains.append(path[:])
            return
        visited.add(node)
        path.append(node)
        neighbors = self._adjacency.get(node, [])
        if not neighbors:
            chains.append(path[:])
        else:
            for n in neighbors:
                self._dfs(n, path, chains, max_depth, visited.copy())
        visited.discard(node)

    def find_similar(self, vuln_id: str, threshold: float = 0.5) -> list[tuple[str, float]]:
        """Find similar vulnerabilities based on edge weights."""
        similar: list[tuple[str, float]] = []
        for edge in self._edges:
            if edge.source == vuln_id and edge.edge_type == "similar_to":
                similar.append((edge.target, edge.weight))
            elif edge.target == vuln_id and edge.edge_type == "similar_to":
                similar.append((edge.source, edge.weight))
        return sorted(similar, key=lambda x: -x[1])

    def predict_severity(self, vuln_id: str) -> str:
        """Predict severity based on connected exploit nodes."""
        exploit_edges = [e for e in self._edges if e.source == vuln_id and e.edge_type == "enables"]
        if not exploit_edges:
            return "unknown"
        max_weight = max(e.weight for e in exploit_edges)
        if max_weight >= 0.8:
            return "critical"
        if max_weight >= 0.6:
            return "high"
        if max_weight >= 0.4:
            return "medium"
        return "low"

    def cross_chain_analysis(self, chains: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze vulnerabilities across multiple blockchain protocols."""
        chain_nodes: dict[str, list[str]] = {}
        for chain in chains:
            chain_id = chain.get("chain_id", "unknown")
            vulns = chain.get("vulnerabilities", [])
            for v in vulns:
                node_id = f"{chain_id}:{v['category']}"
                self.add_node(GraphNode(
                    node_id=node_id,
                    node_type="vulnerability",
                    label=v.get("name", v["category"]),
                    properties={"chain": chain_id, **v},
                ))
                chain_nodes.setdefault(chain_id, []).append(node_id)

        # Link similar vulnerabilities across chains
        all_nodes = list(chain_nodes.values())
        for i, chain_a in enumerate(all_nodes):
            for chain_b in all_nodes[i + 1:]:
                for node_a in chain_a:
                    for node_b in chain_b:
                        node_a_data = self._nodes[node_a].properties
                        node_b_data = self._nodes[node_b].properties
                        if node_a_data.get("category") == node_b_data.get("category"):
                            self.add_edge(GraphEdge(
                                source=node_a, target=node_b,
                                edge_type="similar_to",
                                weight=0.7,
                                properties={"cross_chain": True},
                            ))

        return {
            "chains_analyzed": len(chain_nodes),
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "cross_chain_links": sum(1 for e in self._edges if e.properties.get("cross_chain")),
        }

    def status(self) -> dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": list({n.node_type for n in self._nodes.values()}),
        }


_graph: VulnerabilityGraph | None = None


def get_vuln_graph() -> VulnerabilityGraph:
    global _graph
    if _graph is None:
        _graph = VulnerabilityGraph()
    return _graph
