"""CODEX Pipeline v0.2.0 — Chunk → Embed → Graph

Five-stage pipeline that converts raw corpora (SD card transcripts, LIBRARY
documents, essay frameworks, session summaries, message board docs) into
semantic embeddings, graph clusters, and exportable knowledge artifacts.

Stages:
  1. extract  — Parse raw source files into normalized documents
  2. chunk    — Split documents into hierarchical chunks with speaker-turn preservation
  3. embed    — Generate vector embeddings for each chunk
  4. index    — Build graph, run Louvain clustering, detect communities
  5. export   — Produce sphere-nodes.json, Vaya Vida manifest, search indexes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


import logging
logger = logging.getLogger(__name__)

@dataclass
class CodexConfig:
    """Configuration for a CODEX pipeline run."""

    corpus_dir: Path
    output_dir: Path
    chunk_size: int = 512
    chunk_overlap: int = 64
    embedding_model: str = "default"
    louvain_resolution: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class CodexPipeline:
    """Orchestrates the five-stage CODEX pipeline.

    Each stage is a method that can be called independently or chained via
    :meth:`run_all`.
    """

    def __init__(self, config: CodexConfig) -> None:
        self.config = config

    def extract(self, source_dir: Path | None = None) -> list[dict[str, Any]]:
        """Parse raw source files into normalized documents.

        Supports Markdown, plain-text, and all code file extensions via the
        CodebaseScanner's extension set.  Uses Rust parallel walker when available.
        """
        src = source_dir or self.config.corpus_dir
        if not src.exists():
            raise FileNotFoundError(f"Corpus directory not found: {src}")

        # Use scanner's extension set for code files + docs
        from whitemagic.core.memory.codebase_scanner import SCAN_EXTENSIONS, NO_EXT_FILES, SKIP_DIRS

        docs: list[dict[str, Any]] = []

        # Try Rust parallel walker
        try:
            import whitemagic_rs

            rust_files = whitemagic_rs.walk_directory(str(src))
            for ext, paths in rust_files.items():
                if ext not in SCAN_EXTENSIONS:
                    continue
                for path_str in paths:
                    path = Path(path_str)
                    # Skip files in skip dirs
                    rel_parts = path.relative_to(src).parts
                    if any(p in SKIP_DIRS or p.startswith(".git") for p in rel_parts[:-1]):
                        continue
                    try:
                        text = path.read_text(encoding="utf-8", errors="replace")
                        docs.append({
                            "source_path": str(path.relative_to(src)),
                            "filename": path.name,
                            "text": text,
                            "word_count": len(text.split()),
                        })
                    except OSError:
                        continue
            return docs
        except (ImportError, AttributeError, Exception):
            logger.debug("Ignored ImportError, AttributeError, Exception in __init__.py:88")

        # Python fallback
        for path in src.rglob("*"):
            if path.is_file():
                ext = path.suffix.lower()
                if ext in SCAN_EXTENSIONS or path.name in NO_EXT_FILES:
                    # Skip files in skip dirs
                    rel_parts = path.relative_to(src).parts
                    if any(p in SKIP_DIRS or p.startswith(".git") for p in rel_parts[:-1]):
                        continue
                    try:
                        text = path.read_text(encoding="utf-8", errors="replace")
                        docs.append({
                            "source_path": str(path.relative_to(src)),
                            "filename": path.name,
                            "text": text,
                            "word_count": len(text.split()),
                        })
                    except OSError:
                        continue
        return docs

    def chunk(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Split documents into hierarchical chunks.

        Planned: Q3 2026.  Basic paragraph-level chunking is implemented
        as a fallback until semantic chunking is ready.
        """
        chunks: list[dict[str, Any]] = []
        for doc in docs:
            paragraphs = [p.strip() for p in doc["text"].split("\n\n") if p.strip()]
            for i, para in enumerate(paragraphs):
                chunks.append(
                    {
                        "source_path": doc["source_path"],
                        "chunk_index": i,
                        "text": para,
                        "word_count": len(para.split()),
                    }
                )
        return chunks

    def embed(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate vector embeddings for each chunk.

        Uses WhiteMagic's EmbeddingEngine (MiniLM-L6-v2, 384 dims) with
        batch encoding for throughput.  Falls back to hash-based pseudo
        embeddings if the model is unavailable.
        """
        if not chunks:
            return []

        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine

            engine = get_embedding_engine()
            if not engine.available():
                # Pseudo-embedding fallback: hash-based sparse vectors
                return self._pseudo_embed(chunks)

            batch_size = 64
            embedded: list[dict[str, Any]] = []

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                texts = [c["text"] for c in batch]

                vecs = engine.encode_batch(texts, batch_size=batch_size)
                if vecs is None:
                    # Pseudo-embed this batch
                    embedded.extend(self._pseudo_embed(batch))
                    continue

                for j, vec in enumerate(vecs):
                    chunk = batch[j]
                    chunk_id = f"{chunk['source_path']}#{chunk['chunk_index']}"
                    embedded.append({
                        **chunk,
                        "chunk_id": chunk_id,
                        "embedding": list(vec) if not isinstance(vec, list) else vec,
                        "embedding_model": "minilm-l6-v2",
                    })

            return embedded

        except ImportError:
            return self._pseudo_embed(chunks)

    def _pseudo_embed(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Hash-based pseudo-embedding fallback (384-dim, deterministic)."""
        import hashlib
        import math

        embedded: list[dict[str, Any]] = []
        for chunk in chunks:
            text = chunk["text"]
            h = hashlib.sha256(text.encode()).digest()
            # Expand 32 bytes → 384 dims via repeated hashing
            vec: list[float] = []
            seed = h
            while len(vec) < 384:
                seed = hashlib.sha256(seed).digest()
                for k in range(0, 32, 4):
                    if len(vec) >= 384:
                        break
                    # Use int interpretation and scale to [-1, 1] range
                    # This avoids NaN/inf from raw float interpretation
                    val = int.from_bytes(seed[k:k + 4], "little", signed=True)
                    vec.append(val / 2147483648.0)  # Normalize to [-1, 1]
            # Normalize to unit length
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0 and not math.isnan(norm) and not math.isinf(norm):
                vec = [v / norm for v in vec]
            else:
                # Fallback: use raw values if norm is degenerate
                vec = [max(-1.0, min(1.0, v)) for v in vec]

            chunk_id = f"{chunk['source_path']}#{chunk['chunk_index']}"
            embedded.append({
                **chunk,
                "chunk_id": chunk_id,
                "embedding": vec,
                "embedding_model": "pseudo-hash",
            })
        return embedded

    def index(self, embedded_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Build graph, run Louvain clustering, detect communities.

        Constructs a similarity graph from chunk embeddings (cosine similarity
        above threshold), then runs community detection.  Falls back to
        connected-components if networkx/louvain is unavailable.
        """
        if not embedded_chunks:
            return {"nodes": [], "edges": [], "communities": [], "stats": {}}

        # Build similarity graph
        threshold = 0.65
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        adjacency: dict[str, set[str]] = {}

        for chunk in embedded_chunks:
            cid = chunk["chunk_id"]
            nodes.append({
                "id": cid,
                "source_path": chunk["source_path"],
                "chunk_index": chunk["chunk_index"],
                "word_count": chunk.get("word_count", 0),
                "embedding_model": chunk.get("embedding_model", "unknown"),
            })
            adjacency[cid] = set()

        # O(N^2) pairwise similarity — fine for <5K chunks
        # For larger corpora, use HNSW for approximate k-NN graph
        n = len(embedded_chunks)
        if n > 5000:
            threshold = 0.75  # Higher threshold to reduce edge count

        for i in range(n):
            vec_i = embedded_chunks[i].get("embedding", [])
            if not vec_i:
                continue
            cid_i = embedded_chunks[i]["chunk_id"]

            for j in range(i + 1, n):
                vec_j = embedded_chunks[j].get("embedding", [])
                if not vec_j:
                    continue
                cid_j = embedded_chunks[j]["chunk_id"]

                # Cosine similarity (vectors are pre-normalized for real embeddings)
                dot = sum(a * b for a, b in zip(vec_i, vec_j))
                sim = dot  # Already normalized for minilm; for pseudo, also normalized

                if sim >= threshold:
                    edges.append({
                        "source": cid_i,
                        "target": cid_j,
                        "weight": round(sim, 4),
                    })
                    adjacency[cid_i].add(cid_j)
                    adjacency[cid_j].add(cid_i)

        # Community detection
        communities: list[list[str]] = []
        try:
            import networkx as nx

            graph = nx.Graph()
            graph.add_nodes_from([n["id"] for n in nodes])
            graph.add_edges_from([(e["source"], e["target"]) for e in edges])

            try:
                import community as community_louvain  # type: ignore

                partition = community_louvain.best_partition(
                    graph, resolution=self.config.louvain_resolution
                )
                # Group by community
                comm_map: dict[int, list[str]] = {}
                for node, comm_id in partition.items():
                    comm_map.setdefault(comm_id, []).append(node)
                communities = list(comm_map.values())
            except ImportError:
                # Fallback: connected components
                communities = [list(c) for c in nx.connected_components(graph)]

        except ImportError:
            # Fallback: simple BFS-based connected components
            visited: set[str] = set()
            for node_id in adjacency:
                if node_id in visited:
                    continue
                queue = [node_id]
                component: list[str] = []
                while queue:
                    current = queue.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    component.append(current)
                    queue.extend(adjacency[current] - visited)
                if component:
                    communities.append(component)

        return {
            "nodes": nodes,
            "edges": edges,
            "communities": communities,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "community_count": len(communities),
                "avg_degree": round(2 * len(edges) / max(len(nodes), 1), 2),
                "threshold": threshold,
            },
        }

    def export(self, graph_data: dict[str, Any]) -> Path:
        """Produce sphere-nodes.json, Vaya Vida manifest, search indexes.

        Writes three files to ``output_dir``:
        - ``sphere-nodes.json`` — graph nodes with community assignments
        - ``manifest.json`` — pipeline metadata and stats
        - ``search-index.json`` — flat chunk index for text search
        """
        import json

        out = self.config.output_dir
        out.mkdir(parents=True, exist_ok=True)

        # Assign community IDs to nodes
        comm_lookup: dict[str, int] = {}
        for comm_idx, members in enumerate(graph_data.get("communities", [])):
            for member in members:
                comm_lookup[member] = comm_idx

        sphere_nodes = []
        for node in graph_data.get("nodes", []):
            sphere_nodes.append({
                "id": node["id"],
                "source_path": node["source_path"],
                "chunk_index": node["chunk_index"],
                "word_count": node.get("word_count", 0),
                "community": comm_lookup.get(node["id"], -1),
            })

        (out / "sphere-nodes.json").write_text(
            json.dumps(sphere_nodes, indent=2), encoding="utf-8"
        )

        manifest = {
            "pipeline": "codex",
            "version": "0.2.0",
            "config": {
                "corpus_dir": str(self.config.corpus_dir),
                "chunk_size": self.config.chunk_size,
                "embedding_model": self.config.embedding_model,
                "louvain_resolution": self.config.louvain_resolution,
            },
            "stats": graph_data.get("stats", {}),
            "node_count": len(sphere_nodes),
            "edge_count": len(graph_data.get("edges", [])),
            "community_count": len(graph_data.get("communities", [])),
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Flat search index: node_id → source_path for quick lookup
        search_index = {
            node["id"]: {
                "source_path": node["source_path"],
                "chunk_index": node["chunk_index"],
            }
            for node in graph_data.get("nodes", [])
        }
        (out / "search-index.json").write_text(
            json.dumps(search_index, indent=2), encoding="utf-8"
        )

        return out / "manifest.json"

    def run_all(self) -> dict[str, Any]:
        """Run the full pipeline end-to-end.

        Returns a summary dict with stage outputs and metadata.
        """
        docs = self.extract()
        chunks = self.chunk(docs)
        embedded = self.embed(chunks)
        graph = self.index(embedded)
        output_path = self.export(graph)
        return {
            "config": {
                "corpus_dir": str(self.config.corpus_dir),
                "output_dir": str(self.config.output_dir),
            },
            "stats": {
                "documents": len(docs),
                "chunks": len(chunks),
            },
            "output_path": str(output_path),
        }
