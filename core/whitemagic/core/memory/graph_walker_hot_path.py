"""Graph Walker Hot Path - Polyglot-Accelerated Implementation
Backend priority: Zig SIMD > Rust > NumPy > Python
Target: 10-50x speedup for multi-hop graph traversal semantic scoring
"""
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Polyglot backend detection (Zig SIMD > Rust > NumPy)
# ---------------------------------------------------------------------------
_ZIG_BATCH_COSINE = None
_RUST_RRF = None
_BACKEND = "numpy"

_JULIA_RRF = None
_JULIA_PAGERANK = None

# Title-boosted vector search for LoCoMo 100%
_TITLE_BOOSTED_SEARCH = None

# Zig graph transitions for batch probability computation
_ZIG_GRAPH_TRANSITIONS = None

def _init_backends():
    """Detect and cache the fastest available acceleration backend."""
    global _ZIG_BATCH_COSINE, _RUST_RRF, _JULIA_RRF, _JULIA_PAGERANK
    global _BACKEND, _TITLE_BOOSTED_SEARCH, _ZIG_GRAPH_TRANSITIONS
    # Zig SIMD — fastest for batch cosine (lane_width=8 AVX2)
    try:
        from whitemagic.core.acceleration.simd_cosine import batch_cosine, simd_status
        status = simd_status()
        if status["has_zig_simd"]:
            _ZIG_BATCH_COSINE = batch_cosine
            _BACKEND = "zig_simd"
            logger.info("graph_walker_hot_path: Zig SIMD active (lane_width=%d)",
                        status["lane_width"])
    except Exception:
        pass
    # Rust RRF fusion
    try:
        import whitemagic_rs
        if hasattr(whitemagic_rs, "rrf_fuse"):
            _RUST_RRF = whitemagic_rs.rrf_fuse
            if _BACKEND == "numpy":
                _BACKEND = "rust"
    except Exception:
        pass
    # Julia — RRF fusion + PageRank (subprocess, used for multi-list merges)
    try:
        from whitemagic.core.acceleration.julia_bridge import (
            julia_pagerank,
            julia_rrf_fuse,
        )
        _JULIA_RRF = julia_rrf_fuse
        _JULIA_PAGERANK = julia_pagerank
        logger.info("graph_walker_hot_path: Julia RRF + PageRank available")
    except Exception:
        pass
    # Title-boosted vector search for LoCoMo 100%
    try:
        from whitemagic.core.search.title_boosted_vector import (
            hybrid_search_with_dedup,
            search_title_boosted,
        )
        _TITLE_BOOSTED_SEARCH = {
            "search_title_boosted": search_title_boosted,
            "hybrid_search_with_dedup": hybrid_search_with_dedup
        }
        logger.info("graph_walker_hot_path: Title-boosted vector search available")
    except Exception as e:
        logger.debug("graph_walker_hot_path: Title-boosted search not available: %s", e)

    # Zig SIMD graph transitions for batch probability computation
    try:
        from whitemagic.core.acceleration.graph_transitions import (
            graph_transitions_status,
            transition_batch,
        )
        if graph_transitions_status()["has_zig_simd"]:
            _ZIG_GRAPH_TRANSITIONS = transition_batch
            logger.info("graph_walker_hot_path: Zig graph transitions active")
    except Exception as e:
        logger.debug("graph_walker_hot_path: Zig graph transitions not available: %s", e)

    if _BACKEND == "numpy":
        logger.debug("graph_walker_hot_path: using NumPy fallback")

_init_backends()

@dataclass
class WalkPath:
    """Optimized WalkPath for hot path operations."""
    nodes: list[str]
    edge_weights: list[float]
    relation_types: list[str]
    total_score: float = 0.0
    depth: int = 0

@dataclass
class WalkResult:
    """Optimized WalkResult for hot path operations."""
    seed_ids: list[str]
    hops: int
    paths_explored: int = 0
    unique_nodes_visited: int = 0
    paths: list[WalkPath] = None
    duration_ms: float = 0.0

    def __post_init__(self):
        if self.paths is None:
            self.paths = []

# Hot path: Fast transition probability computation
def compute_transition_probability(
    semantic_sim: float,
    galactic_gravity: float,
    recency: float,
    staleness: float,
    weights: dict[str, float] = None
) -> float:
    """
    Compute edge transition probability from 4 signals.
    Hot path: Vectorized computation for batch processing.
    """
    if weights is None:
        weights = {"semantic": 0.4, "gravity": 0.3, "recency": 0.2, "staleness": 0.1}

    # Vectorized weighted sum
    prob = (
        weights["semantic"] * semantic_sim +
        weights["gravity"] * galactic_gravity +
        weights["recency"] * recency +
        weights["staleness"] * (1.0 - staleness)  # Lower staleness = higher prob
    )

    return max(0.0, min(1.0, prob))

# Hot path: Batch transition probability computation
def batch_compute_probabilities(
    edges: list[dict[str, float]],
    weights: dict[str, float] = None
) -> list[float]:
    """
    Compute probabilities for batch of edges.
    Hot path: Zig SIMD for semantic channel when vectors available,
    NumPy vectorization otherwise.
    """
    if not edges:
        return []

    w = weights or {"semantic": 0.4, "gravity": 0.3, "recency": 0.2, "staleness": 0.1}

    if len(edges) < 8:
        # Small batch: sequential
        return [compute_transition_probability(
            e.get("semantic_sim", 0.0),
            e.get("galactic_gravity", 0.0),
            e.get("recency", 0.0),
            e.get("staleness", 0.0),
            weights
        ) for e in edges]

    # Hot path: Try Zig SIMD batch transitions first (if available and no vectors)
    if _ZIG_GRAPH_TRANSITIONS is not None and not any(e.get("query_vec") for e in edges):
        try:
            semantic = [e.get("semantic_sim", 0.0) for e in edges]
            gravity = [e.get("galactic_gravity", 0.0) for e in edges]
            recency = [e.get("recency", 0.0) for e in edges]
            staleness = [e.get("staleness", 0.0) for e in edges]
            weights_tuple = (w["semantic"], w["gravity"], w["recency"], w["staleness"])
            return _ZIG_GRAPH_TRANSITIONS(semantic, gravity, recency, staleness, weights_tuple)
        except Exception as e:
            logger.debug("Zig graph transitions failed, falling back to NumPy: %s", e)

    # Hot path: vectorized NumPy baseline (with Zig SIMD for semantic channel if vectors present)
    semantic = np.array([e.get("semantic_sim", 0.0) for e in edges], dtype=np.float32)

    # If raw embedding vectors are attached, use Zig SIMD batch cosine
    # (edges can carry {"query_vec": [...], "target_vec": [...]} for live scoring)
    if _ZIG_BATCH_COSINE is not None:
        query_vecs = [e.get("query_vec") for e in edges]
        target_vecs = [e.get("target_vec") for e in edges]
        if all(v is not None for v in query_vecs) and all(v is not None for v in target_vecs):
            # Use first query vec as reference (all from same query in a walk step)
            q = query_vecs[0]
            zig_scores = _ZIG_BATCH_COSINE(q, target_vecs)
            semantic = np.array(zig_scores, dtype=np.float32)

    gravity = np.array([e.get("galactic_gravity", 0.0) for e in edges], dtype=np.float32)
    recency = np.array([e.get("recency", 0.0) for e in edges], dtype=np.float32)
    staleness = np.array([e.get("staleness", 0.0) for e in edges], dtype=np.float32)

    probs = (
        w["semantic"] * semantic +
        w["gravity"] * gravity +
        w["recency"] * recency +
        w["staleness"] * (1.0 - staleness)
    )

    return np.clip(probs, 0.0, 1.0).tolist()

# Hot path: Parallel BFS traversal
def parallel_bfs_walk(
    seed_ids: list[str],
    neighbors_fn,
    hops: int = 2,
    top_k: int = 5,
    max_parallel: int = 4
) -> WalkResult:
    """
    Parallel BFS graph walk with weighted traversal.
    Hot path: Multi-threaded for 4+ seeds.
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    start_time = time.time()

    result = WalkResult(seed_ids=seed_ids, hops=hops)
    all_paths: list[WalkPath] = []
    visited: set[str] = set(seed_ids)

    # Small seed set: sequential
    if len(seed_ids) < max_parallel:
        for seed in seed_ids:
            paths = _walk_from_seed(seed, neighbors_fn, hops, top_k, visited)
            all_paths.extend(paths)
    else:
        # Hot path: Parallel walk for multiple seeds
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {
                executor.submit(_walk_from_seed, seed, neighbors_fn, hops, top_k, visited): seed
                for seed in seed_ids
            }

            for future in as_completed(futures):
                seed = futures[future]
                try:
                    paths = future.result()
                    all_paths.extend(paths)
                except Exception as e:
                    print(f"Walk failed for seed {seed}: {e}")

    # Sort by score and take top_k
    all_paths.sort(key=lambda p: p.total_score, reverse=True)
    result.paths = all_paths[:top_k]
    result.paths_explored = len(all_paths)
    result.unique_nodes_visited = len(visited) - len(seed_ids)
    result.duration_ms = (time.time() - start_time) * 1000

    return result

def _walk_from_seed(
    seed: str,
    neighbors_fn,
    hops: int,
    top_k: int,
    visited: set[str],
    weights: dict[str, float] = None
) -> list[WalkPath]:
    """Walk from a single seed node with SIMD-accelerated batch transitions."""
    paths = []
    w = weights or {"semantic": 0.4, "gravity": 0.3, "recency": 0.2, "staleness": 0.1}

    # BFS with weighted traversal using batch probability computation
    current_level = [(seed, WalkPath(nodes=[seed], edge_weights=[], relation_types=[], total_score=1.0, depth=0))]

    for hop in range(hops):
        next_level = []

        for node_id, path in current_level:
            # Get neighbors
            neighbors = neighbors_fn(node_id)
            if not neighbors:
                continue

            # Prepare batch data for all unvisited neighbors
            batch_edges = []
            batch_neighbors = []

            for neighbor_id, edge_data in neighbors:
                if neighbor_id in visited:
                    continue
                batch_edges.append({
                    "semantic_sim": edge_data.get("semantic_sim", 0.0),
                    "galactic_gravity": edge_data.get("galactic_gravity", 0.0),
                    "recency": edge_data.get("recency", 0.0),
                    "staleness": edge_data.get("staleness", 0.0),
                    "relation_type": edge_data.get("relation_type", "associated"),
                    "neighbor_id": neighbor_id
                })
                batch_neighbors.append((neighbor_id, edge_data))

            if not batch_edges:
                continue

            # Hot path: Batch compute transition probabilities using Zig SIMD
            probs = batch_compute_probabilities(batch_edges, w)

            # Create paths with computed probabilities
            for i, (neighbor_id, edge_data) in enumerate(batch_neighbors):
                prob = probs[i]

                new_path = WalkPath(
                    nodes=path.nodes + [neighbor_id],
                    edge_weights=path.edge_weights + [prob],
                    relation_types=path.relation_types + [edge_data.get("relation_type", "associated")],
                    total_score=path.total_score * prob,
                    depth=hop + 1
                )

                next_level.append((neighbor_id, new_path))
                visited.add(neighbor_id)

        current_level = next_level
        paths.extend([p for _, p in current_level])

    return paths

def hot_path_status() -> dict[str, Any]:
    """Return current acceleration backend status."""
    return {
        "backend": _BACKEND,
        "zig_simd": _ZIG_BATCH_COSINE is not None,
        "zig_graph_transitions": _ZIG_GRAPH_TRANSITIONS is not None,
        "rust_rrf": _RUST_RRF is not None,
        "julia_rrf": _JULIA_RRF is not None,
        "julia_pagerank": _JULIA_PAGERANK is not None,
        "title_boosted_search": _TITLE_BOOSTED_SEARCH is not None,
        "batch_cosine_fn": _ZIG_BATCH_COSINE.__module__ if _ZIG_BATCH_COSINE else "numpy",
    }


# Hot path: Monkey-patch for seamless integration
def install_hot_paths():
    """Install polyglot-accelerated hot paths into graph_walker module.

    Backend priority: Zig SIMD > Rust > NumPy.
    Adds fast_compute_probability, batch_compute_probabilities,
    parallel_bfs_walk, and hot_path_status to the graph_walker module.
    """
    try:
        from whitemagic.core.memory import graph_walker

        graph_walker.fast_compute_probability = compute_transition_probability
        graph_walker.batch_compute_probabilities = batch_compute_probabilities
        graph_walker.parallel_bfs_walk = parallel_bfs_walk
        graph_walker.hot_path_status = hot_path_status
        graph_walker.WalkResult = WalkResult
        graph_walker.WalkPath = WalkPath
        # Julia backends (subprocess — used for multi-list RRF and PageRank)
        if _JULIA_RRF is not None:
            graph_walker.julia_rrf_fuse = _JULIA_RRF
        if _JULIA_PAGERANK is not None:
            graph_walker.julia_pagerank = _JULIA_PAGERANK
        # Title-boosted vector search for LoCoMo 100%
        if _TITLE_BOOSTED_SEARCH is not None:
            graph_walker.search_title_boosted = _TITLE_BOOSTED_SEARCH["search_title_boosted"]
            graph_walker.hybrid_search_with_dedup = _TITLE_BOOSTED_SEARCH["hybrid_search_with_dedup"]

        status = hot_path_status()
        logger.info(
            "[graph_walker_hot_path] installed: backend=%s zig=%s zig_graph=%s rust=%s title_boosted=%s",
            status["backend"], status["zig_simd"], status["zig_graph_transitions"],
            status["rust_rrf"], status["title_boosted_search"],
        )
        return True

    except Exception as e:
        logger.debug("[graph_walker_hot_path] install failed: %s", e)
        return False


# Auto-install on import
install_hot_paths()
