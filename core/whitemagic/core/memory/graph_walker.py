"""Graph Walker — Multi-Hop Weighted Traversal of the Association Graph.
====================================================================
The #1 gap identified by 4 independent research teams: WhiteMagic has
19M associations that are created but NEVER walked. All retrieval is
stateless single-hop. This module changes that.

The GraphWalker loads neighbors from the associations table, computes
transition probabilities from four signals (semantic similarity, galactic
gravity, recency, and staleness), and performs k-hop weighted random walks
from anchor nodes.

Usage:
    from whitemagic.core.memory.graph_walker import get_graph_walker
    walker = get_graph_walker()

    # Walk 2 hops from a seed memory
    paths = walker.walk(seed_ids=["abc123"], hops=2, top_k=5)

    # Hybrid recall: anchor search + graph expansion
    results = walker.hybrid_recall(query="memory consolidation", hops=2)
"""

from __future__ import annotations

import logging
import math
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

logger = logging.getLogger(__name__)


@dataclass
class WalkPath:
    """A single traversal path through the association graph."""

    nodes: list[str]  # memory IDs in traversal order
    edge_weights: list[float]  # strength of each edge traversed
    relation_types: list[str]  # relation_type of each edge
    total_score: float = 0.0  # cumulative transition probability
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edge_weights": [round(w, 4) for w in self.edge_weights],
            "relation_types": self.relation_types,
            "total_score": round(self.total_score, 4),
            "depth": self.depth,
        }


@dataclass
class WalkResult:
    """Result of a graph walk operation."""

    seed_ids: list[str]
    hops: int
    paths_explored: int = 0
    unique_nodes_visited: int = 0
    paths: list[WalkPath] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_ids": self.seed_ids,
            "hops": self.hops,
            "paths_explored": self.paths_explored,
            "unique_nodes_visited": self.unique_nodes_visited,
            "duration_ms": round(self.duration_ms, 1),
            "paths": [p.to_dict() for p in self.paths],
        }

    def discovered_ids(self) -> set[str]:
        """All unique memory IDs discovered (excluding seeds)."""
        seeds = set(self.seed_ids)
        all_nodes: set[str] = set()
        for path in self.paths:
            all_nodes.update(path.nodes)
        return all_nodes - seeds

    def evidence_chains(self) -> dict[str, list[str]]:
        """Recover evidence chains for each discovered memory.

        For each discovered memory ID, returns the chain of memory IDs
        from a seed to that memory, representing the reasoning path.

        Returns:
            Dict mapping discovered_id → list of memory IDs forming the evidence chain.
        """
        chains: dict[str, list[str]] = {}
        seeds = set(self.seed_ids)
        # Sort paths by score (best first) so we keep the strongest evidence chain
        sorted_paths = sorted(self.paths, key=lambda p: p.total_score, reverse=True)
        for path in sorted_paths:
            for node_id in path.nodes:
                if node_id in seeds:
                    continue
                if node_id not in chains:
                    chains[node_id] = list(path.nodes)
        return chains


@dataclass
class Neighbor:
    """A neighbor node in the association graph."""

    memory_id: str
    strength: float
    direction: str
    relation_type: str
    edge_type: str
    traversal_count: int
    created_at: str | None
    last_traversed_at: str | None
    neuro_score: float = 1.0  # Hebbian strength of target memory


class GraphWalker:
    """Multi-hop weighted graph traversal engine.

    Transition probability for edge (u → v):
        P(v|u) ∝ SemanticSim^σ × Strength × FusedGravity^α × Recency × (1 - Staleness)^β

    Where:
        - SemanticSim: cosine(query_embedding, neighbor_embedding) — semantic steering
        - Strength: association edge weight [0, 1]
        - FusedGravity: weighted blend of galactic proximity + neuro_score + pagerank
        - Recency: 1 / (1 + days_since_edge_creation)
        - Staleness: traversal_count / max_traversals (penalize over-walked paths)
    """

    def __init__(
        self,
        gravity_alpha: float = 0.5,
        staleness_beta: float = 0.3,
        semantic_sigma: float = 1.0,
        max_paths_per_hop: int = 10,
        min_edge_strength: float = 0.05,
        gravity_weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
    ) -> None:
        self._gravity_alpha = gravity_alpha
        self._staleness_beta = staleness_beta
        self._semantic_sigma = semantic_sigma
        self._max_paths = max_paths_per_hop
        self._min_strength = min_edge_strength
        self._gravity_weights = gravity_weights  # (galactic, neuro_score, pagerank)
        self._lock = threading.RLock()
        self._total_walks = 0
        self._total_nodes_visited = 0
        self._pagerank_cache: dict[str, float] = {}
        self._pagerank_cache_time: float = 0.0

    def _get_neighbors(self, memory_id: str, pool: Any) -> list[Neighbor]:
        """Load all outgoing association edges for a memory, including target neuro_score.

        Routes to the correct per-galaxy DB. The default pool may connect to
        a different galaxy than where the memory's associations are stored,
        so we try the default pool first, then fall back to scanning galaxy DBs.
        """
        rows = self._query_neighbors(memory_id, pool)
        if rows:
            return rows
        # Fallback: try per-galaxy DBs
        return self._get_neighbors_from_galaxies(memory_id)

    def _query_neighbors(self, memory_id: str, pool: Any) -> list[Neighbor]:
        """Query neighbors from a specific connection pool."""
        try:
            with pool.connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """SELECT a.target_id, a.strength,
                              COALESCE(a.direction, 'undirected') as direction,
                              COALESCE(a.relation_type, 'associated_with') as relation_type,
                              COALESCE(a.edge_type, 'semantic') as edge_type,
                              COALESCE(a.traversal_count, 0) as traversal_count,
                              a.created_at, a.last_traversed_at,
                              COALESCE(m.neuro_score, 1.0) as neuro_score
                       FROM associations a
                       LEFT JOIN memories m ON a.target_id = m.id
                       WHERE a.source_id = ? AND a.strength >= ?
                       ORDER BY a.strength DESC
                       LIMIT 50""",
                    (memory_id, self._min_strength),
                ).fetchall()
                return [
                    Neighbor(
                        memory_id=row["target_id"],
                        strength=row["strength"],
                        direction=row["direction"],
                        relation_type=row["relation_type"],
                        edge_type=row["edge_type"],
                        traversal_count=row["traversal_count"],
                        created_at=row["created_at"],
                        last_traversed_at=row["last_traversed_at"],
                        neuro_score=row["neuro_score"],
                    )
                    for row in rows
                ]
        except Exception as e:  # noqa: BLE001
            logger.debug("GraphWalker: failed to load neighbors for %s: %s", memory_id, e)
            return []

    def _get_neighbors_from_galaxies(self, memory_id: str) -> list[Neighbor]:
        """Fallback: scan per-galaxy DBs for this memory's associations."""
        try:
            from pathlib import Path

            from whitemagic.config.paths import get_state_root
            galaxies_dir = Path(get_state_root()) / "users" / "local" / "galaxies"
            if not galaxies_dir.exists():
                return []
            for galaxy_dir in galaxies_dir.iterdir():
                if not galaxy_dir.is_dir():
                    continue
                db_path = galaxy_dir / "whitemagic.db"
                if not db_path.exists():
                    continue
                from whitemagic.core.memory.db_manager import safe_connect
                conn = safe_connect(str(db_path), timeout=5)
                conn.row_factory = sqlite3.Row
                try:
                    rows = conn.execute(
                        """SELECT a.target_id, a.strength,
                                  COALESCE(a.direction, 'undirected') as direction,
                                  COALESCE(a.relation_type, 'associated_with') as relation_type,
                                  COALESCE(a.edge_type, 'semantic') as edge_type,
                                  COALESCE(a.traversal_count, 0) as traversal_count,
                                  a.created_at, a.last_traversed_at,
                                  COALESCE(m.neuro_score, 1.0) as neuro_score
                           FROM associations a
                           LEFT JOIN memories m ON a.target_id = m.id
                           WHERE a.source_id = ? AND a.strength >= ?
                           ORDER BY a.strength DESC
                           LIMIT 50""",
                        (memory_id, self._min_strength),
                    ).fetchall()
                    if rows:
                        return [
                            Neighbor(
                                memory_id=row["target_id"],
                                strength=row["strength"],
                                direction=row["direction"],
                                relation_type=row["relation_type"],
                                edge_type=row["edge_type"],
                                traversal_count=row["traversal_count"],
                                created_at=row["created_at"],
                                last_traversed_at=row["last_traversed_at"],
                                neuro_score=row["neuro_score"],
                            )
                            for row in rows
                        ]
                finally:
                    conn.close()
        except Exception as e:  # noqa: BLE001
            logger.debug("GraphWalker: galaxy fallback failed for %s: %s", memory_id, e)
        return []

    def _get_galactic_distance(self, memory_id: str, pool: Any) -> float:
        """Get galactic distance for gravity calculation."""
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    "SELECT galactic_distance FROM memories WHERE id = ?",
                    (memory_id,),
                ).fetchone()
                if row:
                    return row[0] or 0.5
        except Exception:  # noqa: BLE001
            logger.debug("Swallowed exception", exc_info=True)
        return 0.5

    def _get_embedding(self, memory_id: str) -> list[float] | None:
        """Load a cached embedding for a memory from the embedding DB."""
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            db = engine._get_db()
            if db is None:
                return None
            row = db.execute(
                "SELECT embedding FROM memory_embeddings WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row and row[0]:
                from whitemagic.core.memory.embedding_similarity import unpack_embedding
                return cast(list[float] | None, unpack_embedding(row[0]))
        except Exception:  # noqa: BLE001
            logger.debug("Swallowed exception", exc_info=True)
        return None

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        try:
            import whitemagic_rust as rs
            rust_cosine_similarity = getattr(rs, "rust_cosine_similarity", None)
            if rust_cosine_similarity:
                return cast(float, rust_cosine_similarity(a, b))
        except (ImportError, AttributeError):
            logger.debug("Optional dependency unavailable: ImportError")

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _get_pagerank(self, memory_id: str) -> float:
        """Get cached PageRank for a memory (refreshed every 5 min)."""
        now = time.monotonic()
        if not self._pagerank_cache or (now - self._pagerank_cache_time) > 300:
            try:
                from whitemagic.core.memory.graph_engine import get_graph_engine
                engine = get_graph_engine()
                self._pagerank_cache = engine.pagerank()
                self._pagerank_cache_time = now
            except Exception:  # noqa: BLE001
                logger.debug("Swallowed exception", exc_info=True)
        return self._pagerank_cache.get(memory_id, 0.01)

    def _fused_gravity(
        self, galactic_dist: float, neuro_score: float, memory_id: str,
    ) -> float:
        """Fused gravity signal: galactic proximity + neuro_score + pagerank.

        Gravity = w_g × (1 - galactic_dist) + w_n × neuro_score + w_p × pagerank
        """
        w_g, w_n, w_p = self._gravity_weights
        galactic_proximity = 1.0 / (1.0 + galactic_dist)
        pagerank = self._get_pagerank(memory_id)
        # Normalize pagerank to [0, 1] range (typical values are very small)
        pr_normalized = min(1.0, pagerank * 100)
        return w_g * galactic_proximity + w_n * neuro_score + w_p * pr_normalized

    def _get_neighbor_count(self, memory_id: str, pool: Any) -> int:
        """Get the number of outgoing edges for a memory (degree)."""
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM associations WHERE source_id = ? AND strength >= ?",
                    (memory_id, self._min_strength),
                ).fetchone()
                return row[0] if row else 0
        except Exception:  # noqa: BLE001
            return 0

    def _hub_penalty(self, neighbor: Neighbor, pool: Any) -> float:
        """Query-aware hub node downweighting.

        Nodes with many connections (hubs) are generic and less informative
        for specific queries. Penalize them proportionally to their degree.

        Returns a multiplier in [0.5, 1.0]:
          - degree 0-5: 1.0 (no penalty)
          - degree 5-20: linear decay from 1.0 to 0.8
          - degree 20+: linear decay from 0.8 to 0.5 (floor)
        """
        try:
            degree = self._get_neighbor_count(neighbor.memory_id, pool)
        except Exception:  # noqa: BLE001
            return 1.0
        if degree <= 5:
            return 1.0
        if degree <= 20:
            return 1.0 - 0.2 * (degree - 5) / 15.0
        return max(0.5, 0.8 - 0.3 * min(1.0, (degree - 20) / 50.0))

    def _transition_score(
        self,
        neighbor: Neighbor,
        target_galactic_dist: float,
        max_traversals: int,
        query_embedding: list[float] | None = None,
        neighbor_embedding: list[float] | None = None,
        prev_created_at: str | None = None,
        enforce_causality: bool = False,
        pool: Any = None,
    ) -> float:
        """Compute transition probability for an edge.

        P(v|u) ∝ SemanticSim^σ × Strength × FusedGravity^α × Recency × (1 - Staleness)^β
        """
        # Causality enforcement: skip edges that go backward in time
        if enforce_causality and prev_created_at and neighbor.created_at:
            try:
                prev_t = datetime.fromisoformat(prev_created_at)
                curr_t = datetime.fromisoformat(neighbor.created_at)
                if curr_t < prev_t:
                    return 0.0  # Violates temporal ordering
            except Exception:  # noqa: BLE001
                logger.debug("Swallowed exception", exc_info=True)

        # Semantic similarity: steer walk toward query-relevant neighbors
        # v15.2: HRR look-ahead projection — if relation type is known, project
        # the query embedding through that relation for a more targeted comparison.
        # "What should the next hop look like if we follow this relation?"
        semantic_sim = 1.0
        if query_embedding and neighbor_embedding:
            effective_query = query_embedding
            # HRR projection: use relation-aware look-ahead when possible
            if neighbor.relation_type and neighbor.relation_type != "associated_with":
                try:
                    from whitemagic.core.memory.hrr import get_hrr_engine
                    hrr = get_hrr_engine(dim=len(query_embedding))
                    projected = hrr.project(query_embedding, neighbor.relation_type)
                    effective_query = projected.tolist()
                except Exception:  # noqa: BLE001
                    logger.debug("Ignored Exception in graph_walker.py:290")
            raw_sim = self._cosine_similarity(effective_query, neighbor_embedding)
            # Map from [-1, 1] to [0.1, 2.0] — never zero, reward alignment
            semantic_sim = max(0.1, 0.5 + raw_sim * 1.5)

        # Strength: raw edge weight
        strength = max(0.001, neighbor.strength)

        # Fused gravity: galactic proximity + neuro_score + pagerank
        gravity = self._fused_gravity(
            target_galactic_dist, neighbor.neuro_score, neighbor.memory_id,
        )

        # Recency: favor recently created edges
        recency = 1.0
        if neighbor.created_at:
            try:
                created = datetime.fromisoformat(neighbor.created_at)
                days_old = max(0.0, (datetime.now() - created).total_seconds() / 86400.0)
                recency = 1.0 / (1.0 + days_old * 0.01)  # gentle decay
            except Exception:  # noqa: BLE001
                logger.debug("Swallowed exception", exc_info=True)

        # Staleness: penalize over-traversed paths (encourage exploration)
        staleness = 0.0
        if max_traversals > 0 and neighbor.traversal_count > 0:
            staleness = min(1.0, neighbor.traversal_count / max(1, max_traversals))

        # Hub penalty: downweight generic hub nodes (query-aware)
        hub_mult = 1.0
        if pool is not None:
            hub_mult = self._hub_penalty(neighbor, pool)

        score = (
            (semantic_sim ** self._semantic_sigma)
            * strength
            * (gravity ** self._gravity_alpha)
            * recency
            * ((1.0 - staleness) ** self._staleness_beta)
            * hub_mult
        )
        return float(max(0.0001, score))

    def walk(
        self,
        seed_ids: list[str],
        hops: int = 2,
        top_k: int = 5,
        allowed_relations: set[str] | None = None,
        allowed_directions: set[str] | None = None,
        query_embedding: list[float] | None = None,
        enforce_causality: bool = False,
    ) -> WalkResult:
        """Perform weighted random walk from seed nodes.

        Args:
            seed_ids: Starting memory IDs for the walk.
            hops: Number of hops to traverse.
            top_k: Return the top-K highest-scoring paths.
            allowed_relations: If set, only traverse these relation types.
            allowed_directions: If set, only traverse these directions.
            query_embedding: If provided, steers walk toward semantically
                relevant neighbors (cosine similarity weighting).
            enforce_causality: If True, only traverse edges where
                t(current) <= t(neighbor) (temporal ordering).

        Returns:
            WalkResult with discovered paths and nodes.
        """
        start = time.perf_counter()
        result = WalkResult(seed_ids=seed_ids, hops=hops)

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            pool = um.pool
        except Exception as e:  # noqa: BLE001
            logger.error("GraphWalker: could not access memory system: %s", e)
            result.duration_ms = (time.perf_counter() - start) * 1000
            return result

        visited: set[str] = set()
        all_paths: list[WalkPath] = []

        max_traversals = self._get_max_traversals(pool)

        frontier: list[WalkPath] = []
        for sid in seed_ids:
            frontier.append(WalkPath(
                nodes=[sid],
                edge_weights=[],
                relation_types=[],
                total_score=1.0,
                depth=0,
            ))
            visited.add(sid)

        for hop in range(hops):
            next_frontier: list[WalkPath] = []

            for path in frontier:
                current_id = path.nodes[-1]
                neighbors = self._get_neighbors(current_id, pool)

                if not neighbors:
                    continue

                # Filter by allowed relations/directions
                if allowed_relations:
                    neighbors = [n for n in neighbors if n.relation_type in allowed_relations]
                if allowed_directions:
                    neighbors = [n for n in neighbors if n.direction in allowed_directions]

                if not neighbors:
                    continue

                prev_created = None
                if enforce_causality and len(path.nodes) >= 2:
                    # Use the current node's edge creation time from the path
                    prev_created = self._get_edge_created_at(
                        path.nodes[-2], current_id, pool,
                    )

                # Compute transition scores with semantic steering
                scored: list[tuple[Neighbor, float]] = []
                for n in neighbors:
                    gdist = self._get_galactic_distance(n.memory_id, pool)
                    n_embed = None
                    if query_embedding:
                        n_embed = self._get_embedding(n.memory_id)
                    score = self._transition_score(
                        n, gdist, max_traversals,
                        query_embedding=query_embedding,
                        neighbor_embedding=n_embed,
                        prev_created_at=prev_created,
                        enforce_causality=enforce_causality,
                        pool=pool,
                    )
                    if score > 0:
                        scored.append((n, score))

                # Normalize to probabilities
                total_score = sum(s for _, s in scored)
                if total_score <= 0:
                    continue

                # Born-rule sampling: amplitude = sqrt(score), prob ∝ |amp|² = score
                # This replaces deterministic sort with quantum measurement postulate,
                # favoring high-scoring neighbors while preserving exploration.
                from whitemagic.core.acceleration.quantum_bridge import born_rule_select

                scores = [max(0.0, s) for _, s in scored]
                amplitudes = [math.sqrt(s) if s > 0 else 0.0 for s in scores]
                n_select = min(self._max_paths, len(scored))
                selected_indices = born_rule_select(amplitudes, n_select, seed=42 + hop * 100 + len(next_frontier))
                selected = [scored[idx] for idx in selected_indices if idx < len(scored)]

                for neighbor, score in selected:
                    prob = score / total_score
                    new_path = WalkPath(
                        nodes=path.nodes + [neighbor.memory_id],
                        edge_weights=path.edge_weights + [neighbor.strength],
                        relation_types=path.relation_types + [neighbor.relation_type],
                        total_score=path.total_score * prob,
                        depth=hop + 1,
                    )
                    next_frontier.append(new_path)
                    visited.add(neighbor.memory_id)
                    result.paths_explored += 1

                    # Record traversal for staleness tracking
                    self._record_traversal(current_id, neighbor.memory_id, pool)

            # Keep best paths for next hop
            next_frontier.sort(key=lambda p: p.total_score, reverse=True)
            frontier = next_frontier[:self._max_paths * len(seed_ids)]
            all_paths.extend(frontier)

        # Select top-K paths by score
        all_paths.sort(key=lambda p: p.total_score, reverse=True)
        result.paths = all_paths[:top_k]
        result.unique_nodes_visited = len(visited)

        elapsed = (time.perf_counter() - start) * 1000
        result.duration_ms = elapsed

        with self._lock:
            self._total_walks += 1
            self._total_nodes_visited += len(visited)

        logger.info(
            "🔍 Graph walk: %s seeds × %s hops → "
            "%s nodes, %s edges traversed (%.0fms)",
         len(seed_ids), hops, len(visited), result.paths_explored, elapsed)
        return result

    def hybrid_recall(
        self,
        query: str,
        hops: int = 2,
        anchor_limit: int = 5,
        walk_top_k: int = 10,
        final_limit: int = 10,
        enforce_causality: bool = False,
        use_quantum: bool = False,
    ) -> list[dict[str, Any]]:
        """Anchor search + graph walk expansion.

        1. Find anchor memories via hybrid search (BM25 + embedding)
        2. Encode query for semantic walk steering
        3. Walk the association graph from anchors
        4. Hydrate discovered memories
        5. Return ranked results with reasoning paths

        Args:
            query: Search query text.
            hops: Graph walk depth.
            anchor_limit: Number of anchor results from initial search.
            walk_top_k: Top-K paths to keep from graph walk.
            final_limit: Maximum results to return.
            enforce_causality: If True, enforce temporal ordering in walks.
            use_quantum: If True, use quantum-inspired superposition walk
                for parallel path exploration. Falls back to classical
                if quantum module unavailable.

        Returns:
            List of dicts with memory data + walk metadata.
        """
        start = time.perf_counter()

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
        except Exception as e:  # noqa: BLE001
            logger.error("hybrid_recall: could not access memory system: %s", e)
            return []

        anchors = um.search_hybrid(query=query, limit=anchor_limit)
        if not anchors:
            anchors = um.search(query=query, limit=anchor_limit)
        if not anchors:
            return []

        query_embedding: list[float] | None = None
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            if engine.available():
                query_embedding = engine.encode(query)
        except Exception:  # noqa: BLE001
            logger.debug("Ignored Exception in graph_walker.py:533")

        anchor_ids = [m.id for m in anchors]

        quantum_nodes: list[Any] = []
        if use_quantum:
            try:
                from whitemagic.core.intelligence.quantum import QuantumGraphAdapter
                adapter = QuantumGraphAdapter(classical_walker=self)

                # Build neighbor function for quantum superposition walk
                def _get_neighbors_q(mid: str) -> list[dict]:
                    try:
                        pool = um.pool
                        neighbors = self._get_neighbors(mid, pool)
                        return [
                            {"target_id": n.memory_id, "strength": n.strength}
                            for n in neighbors
                            if n.strength >= self._min_strength
                        ]
                    except Exception:  # noqa: BLE001
                        return []

                quantum_nodes = adapter.quantum_enhanced_walk(
                    seed_ids=anchor_ids,
                    hops=hops,
                    top_k=walk_top_k,
                    query_embedding=query_embedding,
                    get_neighbors_func=_get_neighbors_q,
                )
                logger.info(
                    "⚛️ Quantum walk: %d nodes in superposition from %d anchors",
                    len(quantum_nodes), len(anchor_ids),
                )
            except (ImportError, ModuleNotFoundError, Exception) as e:  # noqa: BLE001
                logger.debug("Quantum walk unavailable, falling back to classical: %s", e)
                quantum_nodes = []

        if quantum_nodes:
            discovered_ids = {n.id for n in quantum_nodes if n.id not in set(anchor_ids)}
            # Build a synthetic WalkResult for downstream compatibility
            walk_result = WalkResult(seed_ids=anchor_ids, hops=hops)
            walk_result.paths_explored = len(quantum_nodes)
            walk_result.unique_nodes_visited = len(discovered_ids) + len(anchor_ids)
            # Create synthetic paths from quantum amplitudes
            for qn in quantum_nodes[:walk_top_k]:
                walk_result.paths.append(WalkPath(
                    nodes=[anchor_ids[0], qn.id] if anchor_ids else [qn.id],
                    edge_weights=[qn.amplitude ** 2],
                    relation_types=["quantum_superposition"],
                    total_score=qn.amplitude ** 2,
                    depth=1,
                ))
        else:
            walk_result = self.walk(
                seed_ids=anchor_ids,
                hops=hops,
                top_k=walk_top_k,
                query_embedding=query_embedding,
                enforce_causality=enforce_causality,
            )
            discovered_ids = walk_result.discovered_ids()

        discovered_map: dict[str, Any] = {}
        for mid in discovered_ids:
            try:
                mem = um.recall(mid)
                if mem:
                    discovered_map[mid] = mem
            except Exception:  # noqa: BLE001
                logger.debug("Swallowed exception", exc_info=True)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        # Anchors (direct search hits)
        for mem in anchors:
            results.append({
                "memory_id": mem.id,
                "title": mem.title,
                "content": str(mem.content)[:500],
                "importance": mem.importance,
                "source": "anchor",
                "rrf_score": mem.metadata.get("rrf_score", 0.0),
                "walk_paths": [],
            })
            seen.add(mem.id)

        # Graph-discovered (with reasoning paths)
        # Score by: number of paths reaching this node × path scores
        node_scores: dict[str, float] = {}
        node_paths: dict[str, list[dict]] = {}
        for path in walk_result.paths:
            for node_id in path.nodes:
                if node_id not in seen and node_id in discovered_map:
                    node_scores[node_id] = node_scores.get(node_id, 0.0) + path.total_score
                    if node_id not in node_paths:
                        node_paths[node_id] = []
                    node_paths[node_id].append(path.to_dict())

        # Sort graph-discovered by aggregate score
        sorted_discovered = sorted(node_scores.keys(), key=lambda x: node_scores[x], reverse=True)

        for mid in sorted_discovered:
            if len(results) >= final_limit:
                break
            if mid in seen:
                continue
            mem = discovered_map.get(mid)
            if not mem:
                continue

            results.append({
                "memory_id": mem.id,
                "title": mem.title,
                "content": str(mem.content)[:500],
                "importance": mem.importance,
                "source": "graph_walk",
                "graph_score": round(node_scores[mid], 4),
                "walk_paths": node_paths.get(mid, [])[:3],  # top 3 paths
            })
            seen.add(mid)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "🧠 Hybrid recall: '%s' → %s anchors + "
            "%s graph-discovered = %s results (%.0fms)",
         query[:50], len(anchors), len(discovered_ids), len(results), elapsed)
        return results

    def compress_walk_context(
        self,
        results: list[dict[str, Any]],
        query: str,
        max_text_items: int = 5,
    ) -> dict[str, Any]:
        """Compress graph walk results using VSA HRR superposition.

        When a walk discovers many nodes, the full result set can exceed
        token budgets. This method compresses the results into a compact
        HRR vector representation plus a text summary of the top items,
        preserving semantic relevance to the query.

        Returns a dict with:
            - summary: compressed text representation
            - vector: HRR superposition vector (if embeddings available)
            - original_count: number of input results
            - compressed_tokens: estimated tokens in summary
            - original_tokens: estimated tokens in full results
            - compression_ratio: original / compressed
        """
        if not results:
            return {
                "summary": "",
                "vector": None,
                "original_count": 0,
                "compressed_tokens": 0,
                "original_tokens": 0,
                "compression_ratio": 1.0,
            }

        try:
            from whitemagic.ai.vsa_context_compressor import get_vsa_context_compressor
            compressor = get_vsa_context_compressor()
        except Exception:  # noqa: BLE001
            compressor = None

        # Build items for compression
        items = []
        for r in results:
            content = r.get("content", "")
            title = r.get("title", "")
            source = r.get("source", "graph_walk")
            mid = r.get("memory_id", "")
            text = f"{title}: {content}" if title else content
            items.append({"content": text, "source": source, "id": mid})

        # Estimate original tokens
        full_text = "\n".join(i["content"] for i in items)
        original_tokens = len(full_text) // 4

        if compressor is not None:
            result = compressor.compress(items, query=query, max_text_items=max_text_items)
            compressed_tokens = len(result.summary) // 4
            ratio = original_tokens / max(1, compressed_tokens)
            return {
                "summary": result.summary,
                "vector": result.vector if hasattr(result, "vector") else None,
                "original_count": len(results),
                "compressed_tokens": compressed_tokens,
                "original_tokens": original_tokens,
                "compression_ratio": round(ratio, 1),
                "method": result.method,
            }
        else:
            # Fallback: keep top items by score
            sorted_items = sorted(items, key=lambda x: 0, reverse=True)[:max_text_items]
            summary = "\n".join(f"- [{i['source']}] {i['content'][:200]}" for i in sorted_items)
            compressed_tokens = len(summary) // 4
            ratio = original_tokens / max(1, compressed_tokens)
            return {
                "summary": summary,
                "vector": None,
                "original_count": len(results),
                "compressed_tokens": compressed_tokens,
                "original_tokens": original_tokens,
                "compression_ratio": round(ratio, 1),
                "method": "truncation_fallback",
            }

    def hybrid_recall_compressed(
        self,
        query: str,
        hops: int = 2,
        anchor_limit: int = 5,
        walk_top_k: int = 10,
        final_limit: int = 10,
        enforce_causality: bool = False,
        max_text_items: int = 5,
    ) -> dict[str, Any]:
        """Hybrid recall with VSA context compression.

        Same as hybrid_recall but returns a compressed context suitable
        for token-constrained downstream consumers (e.g., inference router).

        Returns dict with:
            - results: full result list (for reference)
            - compressed: VSA-compressed summary
        """
        results = self.hybrid_recall(
            query=query,
            hops=hops,
            anchor_limit=anchor_limit,
            walk_top_k=walk_top_k,
            final_limit=final_limit,
            enforce_causality=enforce_causality,
        )

        compressed = self.compress_walk_context(results, query, max_text_items)

        return {
            "results": results,
            "compressed": compressed,
        }

    def _get_edge_created_at(
        self, source_id: str, target_id: str, pool: Any,
    ) -> str | None:
        """Get created_at timestamp for an edge (for causality enforcement)."""
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    "SELECT created_at FROM associations WHERE source_id = ? AND target_id = ?",
                    (source_id, target_id),
                ).fetchone()
                if row:
                    return str(row[0])
        except Exception:  # noqa: BLE001
            logger.debug("Swallowed exception", exc_info=True)
        return None

    def _get_max_traversals(self, pool: Any) -> int:
        """Get the maximum traversal_count for staleness normalization."""
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    "SELECT MAX(COALESCE(traversal_count, 0)) FROM associations",
                ).fetchone()
                if row and row[0]:
                    return int(row[0])
        except Exception:  # noqa: BLE001
            logger.debug("Swallowed exception", exc_info=True)
        return 10  # default

    def _record_traversal(self, source_id: str, target_id: str, pool: Any) -> None:
        """Record that an edge was traversed (for staleness tracking)."""
        try:
            with pool.connection() as conn:
                conn.execute(
                    """UPDATE associations
                       SET traversal_count = COALESCE(traversal_count, 0) + 1,
                           last_traversed_at = ?
                       WHERE source_id = ? AND target_id = ?""",
                    (datetime.now().isoformat(), source_id, target_id),
                )
        except Exception:  # noqa: BLE001
            logger.debug("Ignored Exception in graph_walker.py:819")

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_walks": self._total_walks,
                "total_nodes_visited": self._total_nodes_visited,
                "gravity_alpha": self._gravity_alpha,
                "staleness_beta": self._staleness_beta,
                "semantic_sigma": self._semantic_sigma,
                "min_edge_strength": self._min_strength,
                "gravity_weights": list(self._gravity_weights),
                "features": {
                    "semantic_projection": True,
                    "fused_gravity": True,
                    "causality_enforcement": True,
                    "hrr_look_ahead": True,
                },
            }


_walker: GraphWalker | None = None
_walker_lock = threading.RLock()


def get_graph_walker(**kwargs: Any) -> GraphWalker:
    """Get the global GraphWalker singleton."""
    global _walker
    if _walker is None:
        with _walker_lock:
            if _walker is None:
                _walker = GraphWalker(**kwargs)
    return _walker
