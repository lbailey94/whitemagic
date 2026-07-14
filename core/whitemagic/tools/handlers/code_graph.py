"""Handler functions for code structure graph MCP tools.

These handlers wrap the CodeStructureGraph class for dispatch table integration.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def handle_code_graph(**kwargs: Any) -> dict[str, Any]:
    """Build or rebuild the code structure graph."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    project_root = kwargs.get("project_root") or os.environ.get("WM_ROOT", ".")
    incremental = kwargs.get("incremental", True)
    max_files = kwargs.get("max_files", 50000)

    graph = get_code_structure_graph()
    return graph.build(project_root, incremental=incremental, max_files=max_files)


def handle_code_query(**kwargs: Any) -> dict[str, Any]:
    """Natural language query against the code graph."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    query = kwargs.get("query", "")
    limit = kwargs.get("limit", 20)

    graph = get_code_structure_graph()
    return graph.query(query, limit=limit)


def handle_code_path(**kwargs: Any) -> dict[str, Any]:
    """Trace path between two symbols."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    symbol_a = kwargs.get("symbol_a", "")
    symbol_b = kwargs.get("symbol_b", "")
    max_hops = kwargs.get("max_hops", 5)

    graph = get_code_structure_graph()
    return graph.path(symbol_a, symbol_b, max_hops=max_hops)


def handle_code_explain(**kwargs: Any) -> dict[str, Any]:
    """Explain a symbol's role."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    symbol = kwargs.get("symbol", "")

    graph = get_code_structure_graph()
    return graph.explain(symbol)


def handle_code_communities(**kwargs: Any) -> dict[str, Any]:
    """Detect communities in the code graph."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    graph = get_code_structure_graph()
    return {"status": "success", "communities": graph.communities()}


def handle_code_god_nodes(**kwargs: Any) -> dict[str, Any]:
    """List most-connected symbols."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    limit = kwargs.get("limit", 10)

    graph = get_code_structure_graph()
    return {"status": "success", "god_nodes": graph.god_nodes(limit=limit)}


def handle_code_subgraph(**kwargs: Any) -> dict[str, Any]:
    """Extract neighborhood around a symbol."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    symbol = kwargs.get("symbol", "")
    depth = kwargs.get("depth", 2)

    graph = get_code_structure_graph()
    return graph.subgraph(symbol, depth=depth)


def handle_code_export(**kwargs: Any) -> dict[str, Any]:
    """Export graph to JSON."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    path = kwargs.get("path", "")

    graph = get_code_structure_graph()
    return graph.export_json(path)


def handle_code_stats(**kwargs: Any) -> dict[str, Any]:
    """Get graph statistics."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    graph = get_code_structure_graph()
    return {"status": "success", **graph.stats()}


def handle_code_import(**kwargs: Any) -> dict[str, Any]:
    """Import a Graphify-compatible graph.json file."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    path = kwargs.get("path", "")

    graph = get_code_structure_graph()
    return graph.import_json(path)


def handle_code_affected_by(**kwargs: Any) -> dict[str, Any]:
    """Find all symbols affected by a change to the given symbol."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    symbol = kwargs.get("symbol", "")
    max_depth = kwargs.get("max_depth", 3)

    graph = get_code_structure_graph()
    return graph.affected_by(symbol, max_depth=max_depth)


def handle_code_correlate(**kwargs: Any) -> dict[str, Any]:
    """Find memories that discuss a given code symbol."""
    from whitemagic.core.intelligence.code_structure_graph import get_code_structure_graph

    symbol = kwargs.get("symbol", "")

    graph = get_code_structure_graph()
    return graph.correlate_memories(symbol)


def handle_code_cross_repo_query(**kwargs: Any) -> dict[str, Any]:
    """Query across multiple repos in a cross-repo graph."""
    from whitemagic.core.intelligence.cross_repo_graph import CrossRepoGraph

    query = kwargs.get("query", "")
    limit = kwargs.get("limit", 20)

    crg = CrossRepoGraph()
    return crg.cross_repo_query(query, limit=limit)
