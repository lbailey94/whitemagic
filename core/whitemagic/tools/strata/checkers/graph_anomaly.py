"""Graph anomaly checker — uses code structure graph to detect architectural issues.

Detects:
- God classes (abnormally high degree)
- Circular dependencies (cycles in import graph)
- Dead code (unreachable nodes — zero in-degree, not an entry point)
- Bridge modules (high betweenness — single point of failure)
"""
from __future__ import annotations

from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_god_classes(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect classes/functions with abnormally high degree (god nodes)."""
    try:
        from whitemagic.core.intelligence.code_structure_graph import (
            get_code_structure_graph,
        )
        g = get_code_structure_graph()
        if g.stats()["node_count"] == 0:
            return
    except Exception:
        return

    god_nodes = g.god_nodes(limit=20)
    for node in god_nodes:
        if node["degree"] > 15:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category="graph_anomaly.god_class",
                file=node.get("file", ""),
                line=node.get("line", 0),
                message=f"God node: {node['name']} (degree {node['degree']}) — abnormally high connectivity, consider splitting into smaller units.",
                suggestion="Split into smaller units following single responsibility principle.",
            ))


@register
def check_circular_dependencies(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect circular dependencies in the import graph."""
    try:
        from whitemagic.core.intelligence.code_structure_graph import (
            get_code_structure_graph,
        )
        g = get_code_structure_graph()
        if g.stats()["node_count"] == 0:
            return
    except Exception:
        return

    # Build import-only adjacency
    import_adj: dict[str, set[str]] = {}
    for edge in g._edges.values():
        if edge.edge_type in ("imports", "depends_on"):
            import_adj.setdefault(edge.source_id, set()).add(edge.target_id)

    # Detect cycles using DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]):
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node) if node in path else 0
            cycle = path[cycle_start:] + [node]
            if len(cycle) > 1:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in import_adj.get(node, set()):
            dfs(neighbor, path)
        path.pop()
        rec_stack.discard(node)

    for node_id in import_adj:
        if node_id not in visited:
            dfs(node_id, [])

    # Report cycles (deduplicate by first node)
    seen_cycles: set[str] = set()
    for cycle in cycles[:10]:
        cycle_key = cycle[0]
        if cycle_key in seen_cycles:
            continue
        seen_cycles.add(cycle_key)

        node = g._nodes.get(cycle[0])
        file_path = node.file_path if node else ""
        line = node.line_start if node else 0

        cycle_names = []
        for nid in cycle:
            n = g._nodes.get(nid)
            if n:
                cycle_names.append(n.name)

        findings.append(Finding(
            severity=FindingSeverity.WARNING,
            category="graph_anomaly.circular_dependency",
            file=file_path,
            line=line,
            message=f"Circular dependency: {' → '.join(cycle_names[:5])} — {len(cycle)} symbols in cycle. This can cause import errors and tight coupling.",
            suggestion="Break the cycle by extracting shared logic into a separate module.",
        ))


@register
def check_dead_code(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect dead code — symbols with zero in-degree that aren't entry points."""
    try:
        from whitemagic.core.intelligence.code_structure_graph import (
            get_code_structure_graph,
        )
        g = get_code_structure_graph()
        if g.stats()["node_count"] == 0:
            return
    except Exception:
        return

    # Compute in-degree for each node
    in_degree: dict[str, int] = {}
    for edge in g._edges.values():
        if edge.edge_type in ("calls", "imports", "references", "defines"):
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

    # Entry point patterns — files that are typically called externally
    entry_patterns = {
        "main", "run", "cli", "app", "server", "start",
        "__main__", "setup", "conftest", "test_",
    }

    dead_count = 0
    for node_id, node in g._nodes.items():
        if node.node_type not in ("function", "class"):
            continue
        if in_degree.get(node_id, 0) > 0:
            continue
        # Check if it's an entry point
        name_lower = node.name.lower()
        is_entry = any(pat in name_lower for pat in entry_patterns)
        if is_entry:
            continue
        # Check if it's defined in a test file
        if "test" in node.file_path.lower():
            continue
        # Check if it's a dunder method (likely called by Python runtime)
        if node.name.startswith("__") and node.name.endswith("__"):
            continue

        findings.append(Finding(
            severity=FindingSeverity.INFO,
            category="graph_anomaly.dead_code",
            file=node.file_path,
            line=node.line_start,
            message=f"Potentially dead code: {node.name} in {node.file_path} has no incoming calls, imports, or references.",
            suggestion="Verify if this symbol is used externally. If not, consider removing it.",
        ))
        dead_count += 1
        if dead_count >= 20:
            break


@register
def check_bridge_modules(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect bridge modules — files with high betweenness centrality."""
    try:
        import networkx as nx

        from whitemagic.core.intelligence.code_structure_graph import (
            get_code_structure_graph,
        )
        g = get_code_structure_graph()
        if g.stats()["node_count"] == 0:
            return
    except Exception:
        return

    # Build networkx graph from code edges
    G = nx.DiGraph()
    for node_id, node in g._nodes.items():
        G.add_node(node_id, name=node.name, file=node.file_path, type=node.node_type)
    for edge in g._edges.values():
        if edge.edge_type in ("calls", "imports", "references"):
            G.add_edge(edge.source_id, edge.target_id)

    if G.number_of_nodes() < 3:
        return

    # Compute betweenness centrality
    try:
        bc = nx.betweenness_centrality(G, normalized=True)
    except Exception:
        return

    # Find nodes with high betweenness (top 5% or > 0.1)
    threshold = max(0.1, sorted(bc.values(), reverse=True)[min(5, len(bc) - 1)] if bc else 0.1)
    bridge_count = 0
    for node_id, centrality in sorted(bc.items(), key=lambda x: x[1], reverse=True):
        if centrality < threshold:
            break
        node = g._nodes.get(node_id)
        if not node or node.node_type != "file":
            continue
        findings.append(Finding(
            severity=FindingSeverity.INFO,
            category="graph_anomaly.bridge_module",
            file=node.file_path,
            line=node.line_start,
            message=f"Bridge module: {node.name} (betweenness {centrality:.3f}) — many code paths pass through this file, making it a single point of failure.",
            suggestion="Consider splitting bridge modules or reducing coupling to minimize blast radius.",
        ))
        bridge_count += 1
        if bridge_count >= 10:
            break
