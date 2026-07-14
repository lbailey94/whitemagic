"""Code Structure Graph — Tree-sitter AST extraction with Python fallback.

Extracts nodes (functions, classes, files, modules) and edges
(calls, imports, inherits, defines, references) from source code.
Feeds into the existing GraphEngine for centrality, community
detection, and bridge node analysis.

Layers:
  1. Rust PyO3 (wm_codegraph) — fastest, 36 languages via tree-sitter
  2. Python ast — Python-only fallback (reuses STRATA FileIndex patterns)
  3. Regex — last-resort fallback for unsupported languages
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Rust acceleration attempt
try:
    import whitemagic_rust as _wr
    _rust_codegraph: Any = getattr(_wr, "codegraph", None)
    _RUST_AVAILABLE = _rust_codegraph is not None
except (ImportError, AttributeError):
    _rust_codegraph = None
    _RUST_AVAILABLE = False

# Language → file extension mapping
LANG_EXTS: dict[str, list[str]] = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "rust": [".rs"],
    "go": [".go"],
    "java": [".java"],
    "kotlin": [".kt"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
    "ruby": [".rb"],
    "lua": [".lua"],
    "zig": [".zig"],
}

EXT_TO_LANG: dict[str, str] = {}
for lang, exts in LANG_EXTS.items():
    for ext in exts:
        EXT_TO_LANG[ext] = lang

# Skip directories (reuse STRATA FileIndex pattern)
SKIP_NAMES: set[str] = {
    ".venv", "venv", "node_modules", "target", "dist", "build",
    "build-modern", ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", "release", "external", "_deps", "vendor", "third_party",
    "thirdparty", "deps", "lib", "libs", "site-packages", "packages",
    "out", "cmake-build", "oldFiles", "archive", "archives",
    ".hypothesis", ".strata-cache",
}


@dataclass
class CodeNode:
    """A node in the code structure graph."""
    id: str
    node_type: str  # function, class, file, module, interface, variable
    name: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "language": self.language,
            "content_hash": self.content_hash,
            "metadata": json.dumps(self.metadata),
        }


@dataclass
class CodeEdge:
    """An edge in the code structure graph."""
    id: str
    source_id: str
    target_id: str
    edge_type: str  # calls, imports, inherits, defines, references
    confidence: str  # EXTRACTED, INFERRED
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "confidence": self.confidence,
            "weight": self.weight,
            "metadata": json.dumps(self.metadata),
            "created_at": datetime.now(UTC).isoformat(),
        }


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _make_node_id(file_path: str, name: str, node_type: str) -> str:
    return f"{file_path}::{name}" if node_type != "file" else file_path


def _make_edge_id(source: str, target: str, edge_type: str) -> str:
    return f"{source}->{target}:{edge_type}"


class CodeStructureGraph:
    """Code structure graph backed by AST extraction.

    Extracts nodes (functions, classes, files, modules) and edges
    (calls, imports, inherits, defines, references) from source code.
    Persists to SQLite for incremental rebuilds.
    """

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS code_nodes (
        id TEXT PRIMARY KEY,
        node_type TEXT NOT NULL,
        name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        line_start INTEGER,
        line_end INTEGER,
        language TEXT NOT NULL,
        content_hash TEXT,
        metadata TEXT DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_code_nodes_file ON code_nodes(file_path);
    CREATE INDEX IF NOT EXISTS idx_code_nodes_type ON code_nodes(node_type);
    CREATE INDEX IF NOT EXISTS idx_code_nodes_name ON code_nodes(name);

    CREATE TABLE IF NOT EXISTS code_edges (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        confidence TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        metadata TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES code_nodes(id),
        FOREIGN KEY (target_id) REFERENCES code_nodes(id)
    );
    CREATE INDEX IF NOT EXISTS idx_code_edges_source ON code_edges(source_id);
    CREATE INDEX IF NOT EXISTS idx_code_edges_target ON code_edges(target_id);
    CREATE INDEX IF NOT EXISTS idx_code_edges_type ON code_edges(edge_type);

    CREATE TABLE IF NOT EXISTS code_graph_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = str(db_path) if db_path else None
        self._lock = threading.RLock()
        self._nodes: dict[str, CodeNode] = {}
        self._edges: dict[str, CodeEdge] = {}
        self._file_hashes: dict[str, str] = {}
        self._project_root: str = ""
        self._last_build: float = 0.0
        self._init_db()

    def _init_db(self) -> None:
        if self._db_path is None:
            return
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(self.SCHEMA_SQL)
            conn.commit()

    def _get_db_conn(self) -> sqlite3.Connection:
        if self._db_path is None:
            raise RuntimeError("No database path configured")
        return sqlite3.connect(self._db_path)

    # ── Public API ──────────────────────────────────────────────

    def build(
        self,
        project_path: str | Path,
        incremental: bool = True,
        max_files: int = 50000,
    ) -> dict[str, Any]:
        """Parse all source files, extract nodes + edges, persist to SQLite.

        Args:
            project_path: Root directory to scan.
            incremental: If True, only reparse files whose content hash changed.
            max_files: Maximum number of files to process.

        Returns:
            Summary dict with node_count, edge_count, files_processed, duration_ms.
        """
        start = time.perf_counter()
        project = Path(project_path).resolve()
        self._project_root = str(project)

        # Try Rust first
        if _RUST_AVAILABLE:
            try:
                result = _rust_codegraph.build(
                    str(project), self._db_path or "", incremental, max_files
                )
                if result and result.get("status") == "success":
                    self._load_from_db()
                    self._last_build = time.time()
                    elapsed = (time.perf_counter() - start) * 1000
                    result["duration_ms"] = round(elapsed, 2)
                    return result
            except Exception as e:
                logger.debug("Rust codegraph build failed, falling back: %s", e)

        # Python fallback
        files = self._discover_files(project, max_files)
        files_processed = 0
        files_skipped = 0

        # Load existing hashes for incremental
        if incremental:
            self._load_file_hashes()

        new_nodes: list[CodeNode] = []
        new_edges: list[CodeEdge] = []
        new_file_hashes: dict[str, str] = {}

        for fpath in files:
            rel = str(fpath.relative_to(project))
            ext = fpath.suffix.lower()
            lang = EXT_TO_LANG.get(ext)
            if lang is None:
                continue

            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            content_hash = _hash_content(text)

            # Incremental skip
            if incremental and rel in self._file_hashes:
                if self._file_hashes[rel] == content_hash:
                    new_file_hashes[rel] = content_hash
                    files_skipped += 1
                    continue

            new_file_hashes[rel] = content_hash
            files_processed += 1

            # Extract nodes + edges
            nodes, edges = self._extract(rel, text, lang, content_hash)
            new_nodes.extend(nodes)
            new_edges.extend(edges)

        # Persist to SQLite
        self._persist(new_nodes, new_edges, new_file_hashes, str(project), incremental)

        # Update in-memory cache
        self._nodes = {n.id: n for n in new_nodes}
        self._edges = {e.id: e for e in new_edges}
        self._file_hashes = new_file_hashes
        self._last_build = time.time()

        # Load full graph from DB if incremental (merge old + new)
        if incremental:
            self._load_from_db()

        elapsed = (time.perf_counter() - start) * 1000
        return {
            "status": "success",
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "files_processed": files_processed,
            "files_skipped": files_skipped,
            "files_discovered": len(files),
            "duration_ms": round(elapsed, 2),
            "parser": "python-ast-regex",
        }

    def query(self, natural_language: str, limit: int = 20) -> dict[str, Any]:
        """Natural language query against the code graph.

        Maps common query patterns to graph operations.
        """
        q = natural_language.lower().strip()

        # Pattern: "what calls X" / "who calls X"
        if "what calls" in q or "who calls" in q:
            symbol = natural_language.split("calls")[-1].strip()
            return self._callers(symbol, limit)

        # Pattern: "what does X call" / "calls from X"
        if "what does" in q and "call" in q:
            parts = natural_language.split("what does")
            if len(parts) > 1:
                symbol = parts[1].split("call")[0].strip()
                return self._callees(symbol, limit)

        # Pattern: "path from X to Y"
        if "path from" in q and "to" in q:
            parts = q.split("path from")[-1].split("to")
            if len(parts) >= 2:
                return self.path(parts[0].strip(), parts[1].strip())

        # Pattern: "explain X"
        if q.startswith("explain "):
            symbol = natural_language[8:].strip()
            return self.explain(symbol)

        # Pattern: "communities" / "subsystems"
        if "communit" in q or "subsystem" in q:
            return {"communities": self.communities()}

        # Pattern: "god nodes" / "most connected" / "hub"
        if "god" in q or "most connected" in q or "hub" in q:
            return {"god_nodes": self.god_nodes(limit)}

        # Default: search for symbol by name
        return self._search_by_name(natural_language, limit)

    def path(self, symbol_a: str, symbol_b: str, max_hops: int = 5) -> dict[str, Any]:
        """Trace the path between two symbols (A → B).

        Uses BFS on the in-memory edge graph.
        """
        node_a = self._find_node(symbol_a)
        node_b = self._find_node(symbol_b)
        if not node_a:
            return {"status": "error", "error": f"Symbol not found: {symbol_a}"}
        if not node_b:
            return {"status": "error", "error": f"Symbol not found: {symbol_b}"}

        # BFS
        adj = self._build_adjacency()
        visited = {node_a.id}
        queue = [(node_a.id, [node_a.id])]
        while queue:
            current, path = queue.pop(0)
            if current == node_b.id:
                return {
                    "status": "success",
                    "path": [self._nodes[n].name if n in self._nodes else n for n in path],
                    "path_ids": path,
                    "hops": len(path) - 1,
                }
            if len(path) > max_hops:
                continue
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return {"status": "no_path", "message": f"No path found between {symbol_a} and {symbol_b} in {max_hops} hops"}

    def explain(self, symbol: str) -> dict[str, Any]:
        """Explain a symbol's role: degree, edges, source location."""
        node = self._find_node(symbol)
        if not node:
            return {"status": "error", "error": f"Symbol not found: {symbol}"}

        self._build_adjacency()
        in_edges = [e for e in self._edges.values() if e.target_id == node.id]
        out_edges = [e for e in self._edges.values() if e.source_id == node.id]

        return {
            "status": "success",
            "symbol": node.name,
            "node_type": node.node_type,
            "file": node.file_path,
            "lines": f"{node.line_start}-{node.line_end}",
            "language": node.language,
            "degree": len(in_edges) + len(out_edges),
            "in_degree": len(in_edges),
            "out_degree": len(out_edges),
            "incoming": [
                {
                    "from": self._nodes[e.source_id].name if e.source_id in self._nodes else e.source_id,
                    "type": e.edge_type,
                    "confidence": e.confidence,
                }
                for e in in_edges[:20]
            ],
            "outgoing": [
                {
                    "to": self._nodes[e.target_id].name if e.target_id in self._nodes else e.target_id,
                    "type": e.edge_type,
                    "confidence": e.confidence,
                }
                for e in out_edges[:20]
            ],
        }

    def communities(self) -> list[dict[str, Any]]:
        """Detect communities (subsystems) in the code graph.

        Uses simple connected components as a fallback when networkx is unavailable.
        """
        try:
            import networkx as nx
            G = nx.DiGraph()
            for nid, node in self._nodes.items():
                G.add_node(nid, name=node.name, type=node.node_type, file=node.file_path)
            for eid, edge in self._edges.items():
                G.add_edge(edge.source_id, edge.target_id, type=edge.edge_type)

            UG = G.to_undirected()
            try:
                comms = nx.community.louvain_communities(UG)
            except (AttributeError, Exception):
                comms = [set(c) for c in nx.connected_components(UG) if len(c) >= 2]

            result = []
            for i, comm in enumerate(comms):
                members = sorted(comm)
                # Get common file paths
                files = set()
                names = []
                for mid in members:
                    if mid in self._nodes:
                        files.add(self._nodes[mid].file_path)
                        names.append(self._nodes[mid].name)
                result.append({
                    "community_id": i,
                    "size": len(members),
                    "members": names[:20],
                    "files": sorted(files)[:10],
                })
            result.sort(key=lambda c: c["size"], reverse=True)
            return result
        except ImportError:
            # Fallback: simple connected components via BFS
            adj = self._build_adjacency()
            visited: set[str] = set()
            communities_list = []
            for nid in self._nodes:
                if nid in visited:
                    continue
                component: set[str] = set()
                queue = [nid]
                while queue:
                    current = queue.pop(0)
                    if current in visited:
                        continue
                    visited.add(current)
                    component.add(current)
                    for neighbor in adj.get(current, []):
                        if neighbor not in visited:
                            queue.append(neighbor)
                if len(component) >= 2:
                    names = [self._nodes[n].name for n in component if n in self._nodes]
                    files = set(
                        self._nodes[n].file_path for n in component if n in self._nodes
                    )
                    communities_list.append({
                        "community_id": len(communities_list),
                        "size": len(component),
                        "members": sorted(names)[:20],
                        "files": sorted(files)[:10],
                    })
            communities_list.sort(key=lambda c: c["size"], reverse=True)
            return communities_list

    def god_nodes(self, limit: int = 10) -> list[dict[str, Any]]:
        """List the most-connected concepts (highest degree centrality)."""
        self._build_adjacency()
        degrees = {}
        for nid in self._nodes:
            in_deg = sum(1 for e in self._edges.values() if e.target_id == nid)
            out_deg = sum(1 for e in self._edges.values() if e.source_id == nid)
            degrees[nid] = in_deg + out_deg

        top = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:limit]
        result = []
        for nid, degree in top:
            node = self._nodes.get(nid)
            if node:
                result.append({
                    "name": node.name,
                    "node_type": node.node_type,
                    "file": node.file_path,
                    "degree": degree,
                    "lines": f"{node.line_start}-{node.line_end}",
                })
        return result

    def subgraph(self, symbol: str, depth: int = 2) -> dict[str, Any]:
        """Extract neighborhood around a symbol."""
        node = self._find_node(symbol)
        if not node:
            return {"status": "error", "error": f"Symbol not found: {symbol}"}

        adj = self._build_adjacency()
        visited = {node.id}
        current_frontier = {node.id}
        all_nodes = {node.id}
        all_edges = set()

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in current_frontier:
                for neighbor in adj.get(nid, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
                    # Track edge
                    for eid, edge in self._edges.items():
                        if (edge.source_id == nid and edge.target_id == neighbor) or \
                           (edge.source_id == neighbor and edge.target_id == nid):
                            all_edges.add(eid)
            all_nodes.update(next_frontier)
            current_frontier = next_frontier
            if not current_frontier:
                break

        return {
            "status": "success",
            "center": node.name,
            "depth": depth,
            "node_count": len(all_nodes),
            "edge_count": len(all_edges),
            "nodes": [
                {
                    "name": self._nodes[n].name,
                    "type": self._nodes[n].node_type,
                    "file": self._nodes[n].file_path,
                }
                for n in all_nodes if n in self._nodes
            ][:50],
        }

    def export_json(self, path: str | Path) -> dict[str, Any]:
        """Export to Graphify-compatible graph.json format."""
        nodes_json = []
        for node in self._nodes.values():
            nodes_json.append({
                "id": node.id,
                "type": node.node_type,
                "name": node.name,
                "file": node.file_path,
                "line_start": node.line_start,
                "line_end": node.line_end,
                "language": node.language,
            })

        edges_json = []
        for edge in self._edges.values():
            edges_json.append({
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type,
                "confidence": edge.confidence,
            })

        graph_data = {
            "version": "1.0",
            "generator": "whitemagic-code-structure-graph",
            "project_root": self._project_root,
            "nodes": nodes_json,
            "edges": edges_json,
            "metadata": {
                "node_count": len(nodes_json),
                "edge_count": len(edges_json),
                "exported_at": datetime.now(UTC).isoformat(),
            },
        }

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
        return {
            "status": "success",
            "path": str(out_path),
            "node_count": len(nodes_json),
            "edge_count": len(edges_json),
        }

    def import_json(self, path: str | Path) -> dict[str, Any]:
        """Import from a Graphify-compatible graph.json."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes = []
        for n in data.get("nodes", []):
            node = CodeNode(
                id=n["id"],
                node_type=n.get("type", "function"),
                name=n["name"],
                file_path=n.get("file", ""),
                line_start=n.get("line_start", 0),
                line_end=n.get("line_end", 0),
                language=n.get("language", "unknown"),
            )
            nodes.append(node)

        edges = []
        for e in data.get("edges", []):
            edge = CodeEdge(
                id=_make_edge_id(e["source"], e["target"], e["type"]),
                source_id=e["source"],
                target_id=e["target"],
                edge_type=e["type"],
                confidence=e.get("confidence", "EXTRACTED"),
            )
            edges.append(edge)

        self._nodes = {n.id: n for n in nodes}
        self._edges = {e.id: e for e in edges}
        self._persist(nodes, edges, {}, data.get("project_root", ""), incremental=False)

        return {
            "status": "success",
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        type_counts: dict[str, int] = {}
        for node in self._nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        edge_type_counts: dict[str, int] = {}
        for edge in self._edges.values():
            edge_type_counts[edge.edge_type] = edge_type_counts.get(edge.edge_type, 0) + 1

        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "last_build": self._last_build,
            "project_root": self._project_root,
            "rust_available": _RUST_AVAILABLE,
        }

    # ── GraphEngine Integration ─────────────────────────────────

    def inject_into_graph_engine(self, graph_engine: Any) -> dict[str, Any]:
        """Inject code graph nodes + edges into an existing GraphEngine's networkx graph.

        This enables unified centrality and community analysis across both
        the memory association graph and the code structure graph.

        Args:
            graph_engine: A GraphEngine instance with a built networkx graph.

        Returns:
            Summary of injected nodes and edges.
        """
        try:
            import networkx as nx
        except ImportError:
            return {"status": "error", "error": "networkx not available"}

        G = getattr(graph_engine, "_graph", None)
        if G is None:
            return {"status": "error", "error": "GraphEngine has no built graph"}

        injected_nodes = 0
        injected_edges = 0

        # Add code nodes
        for node_id, node in self._nodes.items():
            if not G.has_node(node_id):
                G.add_node(
                    node_id,
                    name=node.name,
                    type=node.node_type,
                    file=node.file_path,
                    graph_source="code",
                )
                injected_nodes += 1
            else:
                # Enrich existing node with code metadata
                G.nodes[node_id]["code_type"] = node.node_type
                G.nodes[node_id]["code_file"] = node.file_path

        # Add code edges
        for edge_id, edge in self._edges.items():
            if not G.has_edge(edge.source_id, edge.target_id):
                G.add_edge(
                    edge.source_id,
                    edge.target_id,
                    type=edge.edge_type,
                    confidence=edge.confidence,
                    graph_source="code",
                )
                injected_edges += 1

        return {
            "status": "success",
            "injected_nodes": injected_nodes,
            "injected_edges": injected_edges,
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
        }

    def unified_centrality(self, graph_engine: Any, limit: int = 20) -> dict[str, Any]:
        """Compute unified centrality across code + memory graphs.

        Combines code graph degree with memory graph centrality to identify
        symbols that are both structurally important (many code connections)
        and semantically important (many memory associations).

        Args:
            graph_engine: A GraphEngine instance with a built networkx graph.
            limit: Maximum number of results.

        Returns:
            Top symbols by unified centrality score.
        """
        try:
            import networkx as nx
        except ImportError:
            return {"status": "error", "error": "networkx not available"}

        G = getattr(graph_engine, "_graph", None)
        if G is None:
            return {"status": "error", "error": "GraphEngine has no built graph"}

        # Compute centrality on the unified graph
        try:
            pagerank = nx.pagerank(G, max_iter=200)
        except Exception:
            pagerank = {}

        # Compute code-only degree
        code_degree = {}
        for nid in self._nodes:
            in_deg = sum(1 for e in self._edges.values() if e.target_id == nid)
            out_deg = sum(1 for e in self._edges.values() if e.source_id == nid)
            code_degree[nid] = in_deg + out_deg

        # Unified score = normalized code degree + normalized pagerank
        max_code_deg = max(code_degree.values()) if code_degree else 1
        max_pr = max(pagerank.values()) if pagerank else 1

        unified = {}
        for nid in self._nodes:
            code_score = code_degree.get(nid, 0) / max_code_deg if max_code_deg > 0 else 0
            pr_score = pagerank.get(nid, 0) / max_pr if max_pr > 0 else 0
            unified[nid] = code_score * 0.5 + pr_score * 0.5

        top = sorted(unified.items(), key=lambda x: x[1], reverse=True)[:limit]
        result = []
        for nid, score in top:
            node = self._nodes.get(nid)
            if node:
                result.append({
                    "name": node.name,
                    "node_type": node.node_type,
                    "file": node.file_path,
                    "unified_score": round(score, 4),
                    "code_degree": code_degree.get(nid, 0),
                    "pagerank": round(pagerank.get(nid, 0), 6),
                })

        return {
            "status": "success",
            "top_symbols": result,
            "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges(),
        }

    def link_memory(self, symbol: str, memory_id: str, context: str = "") -> dict[str, Any]:
        """Create a 'discussed_in' edge from a code symbol to a memory.

        This enables correlating code structures with memories that discuss them,
        enabling queries like "what memories discuss this function?"

        Args:
            symbol: Code symbol name.
            memory_id: Memory ID from the galactic memory system.
            context: Optional context string (e.g., "bug fix", "design discussion").

        Returns:
            Status dict.
        """
        node = self._find_node(symbol)
        if not node:
            return {"status": "error", "error": f"Symbol not found: {symbol}"}

        edge_id = _make_edge_id(node.id, f"memory:{memory_id}", "discussed_in")
        edge = CodeEdge(
            id=edge_id,
            source_id=node.id,
            target_id=f"memory:{memory_id}",
            edge_type="discussed_in",
            confidence="INFERRED",
            metadata={"context": context} if context else {},
        )
        self._edges[edge_id] = edge

        # Persist
        if self._db_path is not None:
            now = datetime.now(UTC).isoformat()
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO code_edges
                    (id, source_id, target_id, edge_type, confidence,
                     weight, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (edge.id, edge.source_id, edge.target_id, edge.edge_type,
                     edge.confidence, edge.weight, json.dumps(edge.metadata), now),
                )
                conn.commit()

        return {
            "status": "success",
            "edge_id": edge_id,
            "symbol": node.name,
            "memory_id": memory_id,
        }

    def memories_for_symbol(self, symbol: str) -> dict[str, Any]:
        """Find all memories that discuss a given code symbol.

        Args:
            symbol: Code symbol name.

        Returns:
            List of memory IDs and contexts.
        """
        node = self._find_node(symbol)
        if not node:
            return {"status": "error", "error": f"Symbol not found: {symbol}"}

        memories = []
        for edge in self._edges.values():
            if edge.edge_type == "discussed_in" and edge.source_id == node.id:
                mem_id = edge.target_id.replace("memory:", "")
                memories.append({
                    "memory_id": mem_id,
                    "context": edge.metadata.get("context", ""),
                })

        return {
            "status": "success",
            "symbol": node.name,
            "memory_count": len(memories),
            "memories": memories,
        }

    def affected_by(self, symbol: str, max_depth: int = 3) -> dict[str, Any]:
        """Find all symbols that would be affected if the given symbol changes.

        Performs reverse traversal: finds all symbols that call, import, or
        reference the given symbol, transitively up to max_depth hops.
        If multiple nodes share the same name, all are analyzed.

        Args:
            symbol: Name of the symbol to analyze.
            max_depth: Maximum traversal depth (default 3).

        Returns:
            Dict with affected symbols grouped by hop distance.
        """
        # Find ALL nodes matching the symbol name
        matching_nodes = [n for n in self._nodes.values() if n.name == symbol]
        if not matching_nodes:
            # Try partial match
            symbol_lower = symbol.lower()
            matching_nodes = [n for n in self._nodes.values() if n.name.lower() == symbol_lower]
        if not matching_nodes:
            return {"status": "error", "error": f"Symbol '{symbol}' not found"}

        # Build reverse adjacency: who points TO this node?
        reverse_adj: dict[str, list[str]] = {}
        for edge in self._edges.values():
            reverse_adj.setdefault(edge.target_id, []).append(edge.source_id)

        affected: dict[int, list[dict[str, Any]]] = {}
        visited: set[str] = set()
        current_hop: set[str] = set()

        # Start from all matching nodes
        for node in matching_nodes:
            visited.add(node.id)
            current_hop.add(node.id)

        for hop in range(1, max_depth + 1):
            next_hop: set[str] = set()
            for nid in current_hop:
                for source_id in reverse_adj.get(nid, []):
                    if source_id in visited:
                        continue
                    visited.add(source_id)
                    next_hop.add(source_id)
                    node = self._nodes.get(source_id)
                    if node:
                        affected.setdefault(hop, []).append({
                            "id": source_id,
                            "name": node.name,
                            "type": node.node_type,
                            "file": node.file_path,
                            "lines": f"{node.line_start}-{node.line_end}",
                            "language": node.language,
                        })
            current_hop = next_hop
            if not current_hop:
                break

        total = sum(len(v) for v in affected.values())
        return {
            "status": "success",
            "symbol": symbol,
            "total_affected": total,
            "by_hop": affected,
        }

    def correlate_memories(self, symbol: str) -> dict[str, Any]:
        """Find memories that discuss a given code symbol.

        Searches for discussed_in edges and also does a semantic search
        on the codex galaxy for memories mentioning the symbol name.

        Args:
            symbol: Name of the code symbol to correlate.

        Returns:
            Dict with linked memories and semantically matched memories.
        """
        # First get directly linked memories via discussed_in edges
        linked = self.memories_for_symbol(symbol)

        # Also try semantic search on codex galaxy
        semantic_matches: list[dict[str, Any]] = []
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            results = um.search(query=symbol, galaxy="codex", limit=5)
            for r in results:
                semantic_matches.append({
                    "memory_id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "content_preview": r.get("content", "")[:200],
                    "score": r.get("score", 0.0),
                    "source": "semantic_search",
                })
        except Exception:
            logger.debug("Ignored Exception in code_structure_graph.py:966")

        return {
            "status": "success",
            "symbol": symbol,
            "linked_memories": linked.get("memories", []),
            "linked_count": linked.get("memory_count", 0),
            "semantic_matches": semantic_matches,
            "semantic_count": len(semantic_matches),
        }

    def diff_graphs(self, old_graph: dict[str, Any] | None = None) -> dict[str, Any]:
        """Compute diff between current graph and a previous snapshot.

        Args:
            old_graph: Previous graph snapshot (dict with 'nodes' and 'edges'
                       keys, as produced by export_json). If None, compares
                       against the last persisted state in SQLite.

        Returns:
            Dict with added/removed/changed nodes and edges.
        """
        current_nodes = {n_id: n.to_dict() for n_id, n in self._nodes.items()}
        current_edges = {e_id: e.to_dict() for e_id, e in self._edges.items()}

        if old_graph is None:
            # Load from SQLite as the "old" state
            old_nodes: dict[str, dict] = {}
            old_edges: dict[str, dict] = {}
            try:
                with self._db.connect() as conn:
                    rows = conn.execute("SELECT id, node_type, name, file_path, line_start, line_end, language, content_hash, metadata FROM code_nodes").fetchall()
                    for row in rows:
                        old_nodes[row[0]] = {
                            "id": row[0], "node_type": row[1], "name": row[2],
                            "file": row[3], "line_start": row[4], "line_end": row[5],
                            "language": row[6], "content_hash": row[7], "metadata": row[8],
                        }
                    rows = conn.execute("SELECT id, source_id, target_id, edge_type, confidence, weight, metadata FROM code_edges").fetchall()
                    for row in rows:
                        old_edges[row[0]] = {
                            "id": row[0], "source": row[1], "target": row[2],
                            "type": row[3], "confidence": row[4], "weight": row[5],
                            "metadata": row[6],
                        }
            except Exception:
                logger.debug("Ignored Exception in code_structure_graph.py:1012")
        else:
            old_nodes = {n["id"]: n for n in old_graph.get("nodes", [])}
            old_edges = {e["id"]: e for e in old_graph.get("edges", [])}

        added_nodes = [n for n_id, n in current_nodes.items() if n_id not in old_nodes]
        removed_nodes = [n for n_id, n in old_nodes.items() if n_id not in current_nodes]
        changed_nodes = []
        for n_id, n in current_nodes.items():
            if n_id in old_nodes:
                old = old_nodes[n_id]
                if n.get("content_hash") != old.get("content_hash"):
                    changed_nodes.append({
                        "id": n_id,
                        "name": n.get("name", ""),
                        "old_hash": old.get("content_hash"),
                        "new_hash": n.get("content_hash"),
                    })

        added_edges = [e for e_id, e in current_edges.items() if e_id not in old_edges]
        removed_edges = [e for e_id, e in old_edges.items() if e_id not in current_edges]

        return {
            "status": "success",
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "changed_nodes": changed_nodes,
            "added_edges": added_edges,
            "removed_edges": removed_edges,
            "summary": {
                "nodes_added": len(added_nodes),
                "nodes_removed": len(removed_nodes),
                "nodes_changed": len(changed_nodes),
                "edges_added": len(added_edges),
                "edges_removed": len(removed_edges),
            },
        }

    # ── Internal: File Discovery ────────────────────────────────

    def _discover_files(self, project: Path, max_files: int) -> list[Path]:
        """Walk project tree and collect source files."""
        results: list[Path] = []
        for p in project.rglob("*"):
            if len(results) >= max_files:
                break
            if p.is_dir():
                continue
            if any(part in SKIP_NAMES for part in p.parts):
                continue
            ext = p.suffix.lower()
            if ext in EXT_TO_LANG:
                results.append(p)
        return results

    # ── Internal: Extraction ────────────────────────────────────

    def _extract(
        self,
        rel_path: str,
        text: str,
        language: str,
        content_hash: str,
    ) -> tuple[list[CodeNode], list[CodeEdge]]:
        """Extract nodes + edges from a source file."""
        if language == "python":
            return self._extract_python(rel_path, text, content_hash)
        else:
            return self._extract_regex(rel_path, text, language, content_hash)

    def _extract_python(
        self, rel_path: str, text: str, content_hash: str,
    ) -> tuple[list[CodeNode], list[CodeEdge]]:
        """Extract nodes + edges from Python source using ast."""
        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []

        # File node
        file_id = rel_path
        file_node = CodeNode(
            id=file_id,
            node_type="file",
            name=Path(rel_path).name,
            file_path=rel_path,
            line_start=1,
            line_end=text.count("\n") + 1,
            language="python",
            content_hash=content_hash,
        )
        nodes.append(file_node)

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return nodes, edges

        # Collect all defined names for reference resolution
        defined_names: dict[str, str] = {}  # name → node_id

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node_id = _make_node_id(rel_path, node.name, "function")
                func_node = CodeNode(
                    id=node_id,
                    node_type="function",
                    name=node.name,
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    language="python",
                    content_hash=content_hash,
                    metadata={
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args": [a.arg for a in node.args.args],
                    },
                )
                nodes.append(func_node)
                defined_names[node.name] = node_id

                # defines edge: file → function
                edges.append(CodeEdge(
                    id=_make_edge_id(file_id, node_id, "defines"),
                    source_id=file_id,
                    target_id=node_id,
                    edge_type="defines",
                    confidence="EXTRACTED",
                ))

                # Extract calls within this function
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        call_name = self._get_call_name(child.func)
                        if call_name:
                            edges.append(CodeEdge(
                                id=_make_edge_id(node_id, f"call:{call_name}", "calls"),
                                source_id=node_id,
                                target_id=f"call:{call_name}",
                                edge_type="calls",
                                confidence="EXTRACTED",
                                metadata={"line": child.lineno, "target_name": call_name},
                            ))

            elif isinstance(node, ast.ClassDef):
                node_id = _make_node_id(rel_path, node.name, "class")
                class_node = CodeNode(
                    id=node_id,
                    node_type="class",
                    name=node.name,
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    language="python",
                    content_hash=content_hash,
                    metadata={
                        "bases": [self._get_base_name(b) for b in node.bases],
                        "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    },
                )
                nodes.append(class_node)
                defined_names[node.name] = node_id

                # defines edge: file → class
                edges.append(CodeEdge(
                    id=_make_edge_id(file_id, node_id, "defines"),
                    source_id=file_id,
                    target_id=node_id,
                    edge_type="defines",
                    confidence="EXTRACTED",
                ))

                # inherits edges
                for base in node.bases:
                    base_name = self._get_base_name(base)
                    if base_name:
                        target_id = f"class:{base_name}"
                        edges.append(CodeEdge(
                            id=_make_edge_id(node_id, target_id, "inherits"),
                            source_id=node_id,
                            target_id=target_id,
                            edge_type="inherits",
                            confidence="EXTRACTED",
                            metadata={"base": base_name},
                        ))

        # Extract imports
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target_id = f"module:{alias.name}"
                    edges.append(CodeEdge(
                        id=_make_edge_id(file_id, target_id, "imports"),
                        source_id=file_id,
                        target_id=target_id,
                        edge_type="imports",
                        confidence="EXTRACTED",
                        metadata={"module": alias.name, "line": node.lineno},
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    target_id = f"module:{module}.{alias.name}" if module else f"module:{alias.name}"
                    edges.append(CodeEdge(
                        id=_make_edge_id(file_id, target_id, "imports"),
                        source_id=file_id,
                        target_id=target_id,
                        edge_type="imports",
                        confidence="EXTRACTED",
                        metadata={
                            "module": module,
                            "name": alias.name,
                            "line": node.lineno,
                        },
                    ))

        # Resolve call targets to defined names where possible
        resolved_edges: list[CodeEdge] = []
        for edge in edges:
            if edge.edge_type == "calls" and edge.target_id.startswith("call:"):
                call_name = edge.target_id[5:]
                if call_name in defined_names:
                    edge.target_id = defined_names[call_name]
                    edge.id = _make_edge_id(edge.source_id, edge.target_id, "calls")
            resolved_edges.append(edge)

        return nodes, resolved_edges

    def _extract_regex(
        self, rel_path: str, text: str, language: str, content_hash: str,
    ) -> tuple[list[CodeNode], list[CodeEdge]]:
        """Extract nodes + edges from non-Python source using regex."""
        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []
        lines = text.splitlines()

        file_id = rel_path
        file_node = CodeNode(
            id=file_id,
            node_type="file",
            name=Path(rel_path).name,
            file_path=rel_path,
            line_start=1,
            line_end=len(lines),
            language=language,
            content_hash=content_hash,
        )
        nodes.append(file_node)

        patterns = self._get_regex_patterns(language)
        if not patterns:
            return nodes, edges

        # Separate node patterns from import-only patterns
        node_patterns = [p for p in patterns if p.get("regex") and p["regex"].pattern]
        import_patterns = [p for p in patterns if p.get("import_regex")]

        for i, line in enumerate(lines, 1):
            # Check node-extraction patterns
            for pat in node_patterns:
                m = pat["regex"].search(line)
                if m and m.groups():
                    name = m.group(1)
                    node_type = pat["type"]
                    node_id = _make_node_id(rel_path, name, node_type)
                    node = CodeNode(
                        id=node_id,
                        node_type=node_type,
                        name=name,
                        file_path=rel_path,
                        line_start=i,
                        line_end=i,
                        language=language,
                        content_hash=content_hash,
                    )
                    # Avoid duplicates
                    if node_id not in {n.id for n in nodes}:
                        nodes.append(node)
                        edges.append(CodeEdge(
                            id=_make_edge_id(file_id, node_id, "defines"),
                            source_id=file_id,
                            target_id=node_id,
                            edge_type="defines",
                            confidence="EXTRACTED",
                        ))

                    # Check for inherits/implements
                    if pat.get("inherit_group") and pat["inherit_group"] <= len(m.groups()):
                        parent = m.group(pat["inherit_group"])
                        if parent:
                            target_id = f"{pat['inherit_type']}:{parent}"
                            edges.append(CodeEdge(
                                id=_make_edge_id(node_id, target_id, "inherits"),
                                source_id=node_id,
                                target_id=target_id,
                                edge_type="inherits",
                                confidence="EXTRACTED",
                            ))

            # Check import patterns
            for pat in import_patterns:
                im = pat["import_regex"].search(line)
                if im and im.groups():
                    target = im.group(1)
                    target_id = f"module:{target}"
                    edges.append(CodeEdge(
                        id=_make_edge_id(file_id, target_id, "imports"),
                        source_id=file_id,
                        target_id=target_id,
                        edge_type="imports",
                        confidence="EXTRACTED",
                        metadata={"line": i},
                    ))

        return nodes, edges

    def _get_regex_patterns(self, language: str) -> list[dict[str, Any]]:
        """Get regex patterns for node extraction per language."""
        patterns: list[dict[str, Any]] = []

        if language in ("typescript", "javascript"):
            patterns.append({
                "regex": re.compile(r"\bfunction\s+(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r"\bclass\s+(\w+)"),
                "type": "class",
                "inherit_group": 0,
                "inherit_type": "class",
            })
            patterns.append({
                "regex": re.compile(r"\binterface\s+(\w+)"),
                "type": "interface",
            })
            patterns.append({
                "regex": re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\("),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))"""),
            })
        elif language == "rust":
            patterns.append({
                "regex": re.compile(r"\bfn\s+(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r"\bstruct\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r"\btrait\s+(\w+)"),
                "type": "interface",
            })
            patterns.append({
                "regex": re.compile(r"\bimpl\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r"\buse\s+([\w:]+)"),
            })
        elif language == "go":
            patterns.append({
                "regex": re.compile(r"\bfunc\s+(?:\([^)]+\)\s+)?(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r"\btype\s+(\w+)\s+struct"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r"\btype\s+(\w+)\s+interface"),
                "type": "interface",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r'"([^"]+)"'),
            })
        elif language in ("c", "cpp"):
            patterns.append({
                "regex": re.compile(r"\b(?:class|struct)\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r'#include\s+[<"]([^>"]+)[>"]'),
            })
        elif language == "java":
            patterns.append({
                "regex": re.compile(r"\bclass\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r"\binterface\s+(\w+)"),
                "type": "interface",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r"\bimport\s+([\w.]+);"),
            })
        elif language == "kotlin":
            patterns.append({
                "regex": re.compile(r"\bfun\s+(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r"\bclass\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r"\binterface\s+(\w+)"),
                "type": "interface",
            })
        elif language == "ruby":
            patterns.append({
                "regex": re.compile(r"\bdef\s+(?:\w+[.:])?(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r"\bclass\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r"\bmodule\s+(\w+)"),
                "type": "module",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r"""\brequire\s+['\"]([^'\"]+)['\"]"""),
            })
        elif language == "lua":
            patterns.append({
                "regex": re.compile(r"\bfunction\s+(?:\w+[.:])?(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r"""\brequire\s*[\(['\"]+([\w.]+)"""),
            })
        elif language == "zig":
            patterns.append({
                "regex": re.compile(r"\bfn\s+(\w+)"),
                "type": "function",
            })
            patterns.append({
                "regex": re.compile(r"\b(?:struct|union|enum|opaque)\s+(\w+)"),
                "type": "class",
            })
            patterns.append({
                "regex": re.compile(r""),
                "type": "function",
                "import_regex": re.compile(r'@import\("([^"]+)"\)'),
            })

        return patterns

    # ── Internal: AST Helpers ───────────────────────────────────

    @staticmethod
    def _get_call_name(func: ast.expr) -> str:
        """Extract function name from a Call node's func attribute."""
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return func.attr
        elif isinstance(func, ast.Call):
            return CodeStructureGraph._get_call_name(func.func)
        return ""

    @staticmethod
    def _get_base_name(base: ast.expr) -> str:
        """Extract base class name from a ClassDef bases entry."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return ""

    @staticmethod
    def _get_decorator_name(dec: ast.expr) -> str:
        """Extract decorator name."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Attribute):
            return dec.attr
        elif isinstance(dec, ast.Call):
            return CodeStructureGraph._get_decorator_name(dec.func)
        return ""

    # ── Internal: Graph Helpers ─────────────────────────────────

    def _build_adjacency(self) -> dict[str, list[str]]:
        """Build adjacency list from edges."""
        adj: dict[str, list[str]] = {}
        for edge in self._edges.values():
            adj.setdefault(edge.source_id, []).append(edge.target_id)
            # Also add reverse for undirected operations
            adj.setdefault(edge.target_id, [])
        return adj

    def _find_node(self, symbol: str) -> CodeNode | None:
        """Find a node by name (exact or partial match)."""
        # Exact match
        for node in self._nodes.values():
            if node.name == symbol:
                return node
        # Partial match (case-insensitive)
        symbol_lower = symbol.lower()
        for node in self._nodes.values():
            if node.name.lower() == symbol_lower:
                return node
        # Substring match
        matches = [n for n in self._nodes.values() if symbol_lower in n.name.lower()]
        return matches[0] if matches else None

    def _callers(self, symbol: str, limit: int) -> dict[str, Any]:
        """Find all functions that call the given symbol."""
        node = self._find_node(symbol)
        if not node:
            return {"status": "error", "error": f"Symbol not found: {symbol}"}
        callers = []
        for edge in self._edges.values():
            if edge.edge_type == "calls" and edge.target_id == node.id:
                caller = self._nodes.get(edge.source_id)
                if caller:
                    callers.append({
                        "name": caller.name,
                        "file": caller.file_path,
                        "line": caller.line_start,
                    })
        return {"status": "success", "symbol": node.name, "callers": callers[:limit]}

    def _callees(self, symbol: str, limit: int) -> dict[str, Any]:
        """Find all functions called by the given symbol."""
        node = self._find_node(symbol)
        if not node:
            return {"status": "error", "error": f"Symbol not found: {symbol}"}
        callees = []
        for edge in self._edges.values():
            if edge.edge_type == "calls" and edge.source_id == node.id:
                callee = self._nodes.get(edge.target_id)
                if callee:
                    callees.append({
                        "name": callee.name,
                        "file": callee.file_path,
                        "line": callee.line_start,
                    })
        return {"status": "success", "symbol": node.name, "callees": callees[:limit]}

    def _search_by_name(self, query: str, limit: int) -> dict[str, Any]:
        """Search for nodes by name."""
        query_lower = query.lower()
        results = []
        for node in self._nodes.values():
            if query_lower in node.name.lower():
                results.append({
                    "name": node.name,
                    "type": node.node_type,
                    "file": node.file_path,
                    "lines": f"{node.line_start}-{node.line_end}",
                    "language": node.language,
                })
                if len(results) >= limit:
                    break
        return {"status": "success", "query": query, "results": results}

    # ── Internal: Persistence ───────────────────────────────────

    def _load_file_hashes(self) -> None:
        """Load file hashes from SQLite meta table."""
        if self._db_path is None:
            return
        try:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT key, value FROM code_graph_meta WHERE key LIKE 'hash:%'"
                ).fetchall()
                self._file_hashes = {row[0][5:]: row[1] for row in rows}
        except sqlite3.OperationalError:
            self._file_hashes = {}

    def _persist(
        self,
        nodes: list[CodeNode],
        edges: list[CodeEdge],
        file_hashes: dict[str, str],
        project_root: str,
        incremental: bool,
    ) -> None:
        """Persist nodes + edges to SQLite."""
        if self._db_path is None:
            return

        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(self.SCHEMA_SQL)

            if not incremental:
                conn.execute("DELETE FROM code_nodes")
                conn.execute("DELETE FROM code_edges")
                conn.execute("DELETE FROM code_graph_meta")

            # Insert/replace nodes
            for node in nodes:
                conn.execute(
                    """INSERT OR REPLACE INTO code_nodes
                    (id, node_type, name, file_path, line_start, line_end,
                     language, content_hash, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (node.id, node.node_type, node.name, node.file_path,
                     node.line_start, node.line_end, node.language,
                     node.content_hash, json.dumps(node.metadata)),
                )

            # Insert/replace edges
            now = datetime.now(UTC).isoformat()
            for edge in edges:
                conn.execute(
                    """INSERT OR REPLACE INTO code_edges
                    (id, source_id, target_id, edge_type, confidence,
                     weight, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (edge.id, edge.source_id, edge.target_id, edge.edge_type,
                     edge.confidence, edge.weight, json.dumps(edge.metadata), now),
                )

            # Update file hashes
            for rel, h in file_hashes.items():
                conn.execute(
                    "INSERT OR REPLACE INTO code_graph_meta (key, value) VALUES (?, ?)",
                    (f"hash:{rel}", h),
                )

            # Update meta
            conn.execute(
                "INSERT OR REPLACE INTO code_graph_meta (key, value) VALUES (?, ?)",
                ("project_root", project_root),
            )
            conn.execute(
                "INSERT OR REPLACE INTO code_graph_meta (key, value) VALUES (?, ?)",
                ("last_build", now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO code_graph_meta (key, value) VALUES (?, ?)",
                ("node_count", str(len(nodes))),
            )
            conn.execute(
                "INSERT OR REPLACE INTO code_graph_meta (key, value) VALUES (?, ?)",
                ("edge_count", str(len(edges))),
            )
            conn.execute(
                "INSERT OR REPLACE INTO code_graph_meta (key, value) VALUES (?, ?)",
                ("parser_version", "1.0"),
            )

            conn.commit()

    def _load_from_db(self) -> None:
        """Load all nodes + edges from SQLite into memory."""
        if self._db_path is None:
            return
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM code_nodes").fetchall()
                self._nodes = {}
                for row in rows:
                    try:
                        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    self._nodes[row["id"]] = CodeNode(
                        id=row["id"],
                        node_type=row["node_type"],
                        name=row["name"],
                        file_path=row["file_path"],
                        line_start=row["line_start"] or 0,
                        line_end=row["line_end"] or 0,
                        language=row["language"],
                        content_hash=row["content_hash"] or "",
                        metadata=metadata,
                    )

                rows = conn.execute("SELECT * FROM code_edges").fetchall()
                self._edges = {}
                for row in rows:
                    try:
                        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    self._edges[row["id"]] = CodeEdge(
                        id=row["id"],
                        source_id=row["source_id"],
                        target_id=row["target_id"],
                        edge_type=row["edge_type"],
                        confidence=row["confidence"],
                        weight=row["weight"] or 1.0,
                        metadata=metadata,
                    )
        except sqlite3.OperationalError:
            logger.debug("Ignored Exception in code_structure_graph.py:1719")


# ── Singleton ───────────────────────────────────────────────────

_graph: CodeStructureGraph | None = None
_graph_lock = threading.RLock()


def get_code_structure_graph(db_path: str | Path | None = None) -> CodeStructureGraph:
    """Get the singleton CodeStructureGraph instance."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                if db_path is None:
                    db_path = os.path.expanduser(
                        os.environ.get(
                            "WM_CODE_GRAPH_DB",
                            "~/.whitemagic/data/code_graph.db",
                        )
                    )
                _graph = CodeStructureGraph(db_path=db_path)
    return _graph
