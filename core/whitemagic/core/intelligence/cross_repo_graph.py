"""Cross-repo code structure graph merging.

Supports building graphs across multiple repositories and merging them
with repo-prefixed node IDs to avoid collisions.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from whitemagic.core.intelligence.code_structure_graph import (
    CodeEdge,
    CodeNode,
    CodeStructureGraph,
    _hash_content,
    _make_edge_id,
    _make_node_id,
)

logger = logging.getLogger(__name__)


class CrossRepoGraph:
    """Merge multiple per-repo code structure graphs into one unified graph.

    Node IDs are prefixed with the repo name to avoid collisions:
        repo_name:path/to/file.py::symbol_name

    This enables cross-repo queries like "what calls function X from repo Y?"
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._merged = CodeStructureGraph(db_path=db_path)
        self._repos: dict[str, dict[str, Any]] = {}

    def add_repo(
        self,
        repo_name: str,
        project_root: str | Path,
        incremental: bool = True,
        max_files: int = 50000,
    ) -> dict[str, Any]:
        """Build and merge a single repo's code graph.

        Args:
            repo_name: Short name for the repo (used as node ID prefix).
            project_root: Root directory of the repo.
            incremental: If True, only reparse changed files.
            max_files: Maximum files to process.

        Returns:
            Build summary dict.
        """
        repo_name = repo_name.replace("/", "_").replace("-", "_")
        project_root = Path(project_root)

        # Build a temporary per-repo graph
        repo_graph = CodeStructureGraph()
        result = repo_graph.build(project_root, incremental=incremental, max_files=max_files)

        if result["status"] != "success":
            return result

        # Merge nodes with repo-prefixed IDs
        merged_nodes = 0
        merged_edges = 0

        for node_id, node in repo_graph._nodes.items():
            prefixed_id = f"{repo_name}:{node_id}"
            prefixed_path = f"{repo_name}/{node.file_path}"

            new_node = CodeNode(
                id=prefixed_id,
                node_type=node.node_type,
                name=node.name,
                file_path=prefixed_path,
                line_start=node.line_start,
                line_end=node.line_end,
                language=node.language,
                content_hash=node.content_hash,
                metadata={**node.metadata, "repo": repo_name},
            )
            self._merged._nodes[prefixed_id] = new_node
            merged_nodes += 1

        for edge_id, edge in repo_graph._edges.items():
            prefixed_source = f"{repo_name}:{edge.source_id}"
            prefixed_target = f"{repo_name}:{edge.target_id}"

            # Skip edges to external targets (module:xxx) — keep them unprefixed
            if edge.target_id.startswith("module:"):
                prefixed_target = edge.target_id
            if edge.target_id.startswith("memory:"):
                prefixed_target = edge.target_id

            new_edge_id = _make_edge_id(prefixed_source, prefixed_target, edge.edge_type)
            new_edge = CodeEdge(
                id=new_edge_id,
                source_id=prefixed_source,
                target_id=prefixed_target,
                edge_type=edge.edge_type,
                confidence=edge.confidence,
                weight=edge.weight,
                metadata={**edge.metadata, "repo": repo_name},
            )
            self._merged._edges[new_edge_id] = new_edge
            merged_edges += 1

        self._repos[repo_name] = {
            "project_root": str(project_root),
            "node_count": merged_nodes,
            "edge_count": merged_edges,
        }

        return {
            "status": "success",
            "repo": repo_name,
            "merged_nodes": merged_nodes,
            "merged_edges": merged_edges,
            "total_nodes": len(self._merged._nodes),
            "total_edges": len(self._merged._edges),
        }

    def cross_repo_query(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Query across all merged repos.

        Args:
            query: Natural language query.
            limit: Maximum results.

        Returns:
            Query results with repo attribution.
        """
        results = self._merged.query(query, limit=limit)
        # Add repo info to results
        if "results" in results:
            for r in results["results"]:
                if "id" in r and ":" in str(r["id"]):
                    r["repo"] = str(r["id"]).split(":")[0]
        return results

    def cross_repo_path(
        self, symbol_a: str, symbol_b: str, max_hops: int = 5,
    ) -> dict[str, Any]:
        """Trace path between symbols across repos.

        Args:
            symbol_a: Starting symbol (can be repo-prefixed).
            symbol_b: Target symbol (can be repo-prefixed).
            max_hops: Maximum search depth.

        Returns:
            Path result with cross-repo hops.
        """
        result = self._merged.path(symbol_a, symbol_b, max_hops=max_hops)
        if result["status"] == "success" and "path" in result:
            for hop in result["path"]:
                if isinstance(hop, dict) and "id" in hop:
                    hop_id = str(hop["id"])
                    if ":" in hop_id:
                        hop["repo"] = hop_id.split(":")[0]
        return result

    def stats(self) -> dict[str, Any]:
        """Get cross-repo graph statistics."""
        base_stats = self._merged.stats()
        base_stats["repos"] = self._repos
        base_stats["repo_count"] = len(self._repos)
        return base_stats

    def export_json(self, path: str | Path) -> dict[str, Any]:
        """Export the merged cross-repo graph to JSON."""
        return self._merged.export_json(path)

    @property
    def merged_graph(self) -> CodeStructureGraph:
        """Access the underlying merged CodeStructureGraph."""
        return self._merged
