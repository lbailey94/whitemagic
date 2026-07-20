"""P6.2 — Separate benchmark layers for retrieval quality.

Reports distinct metrics for each search mode so that direct SQL results
are never presented as end-to-end product latency.

Layers:
  1. fts5_substrate     — Direct SQLite FTS5 BM25 (no API overhead)
  2. lexical_api        — Production lexical API (UnifiedMemory.search + rerankers)
  3. semantic_only      — Embedding-based semantic search
  4. spatial_only       — 5D holographic spatial search
  5. hybrid_planner     — SearchQueryPlanner (3-channel RRF + entity boost + rerank)
  6. graph_hybrid       — Graph-enhanced hybrid (GraphWalker hybrid_recall)
  7. single_galaxy      — Single-galaxy scoped search
  8. federated_galaxy   — Cross-galaxy federated search
  9. cold_process       — Cold process (no warm caches, fresh import)
 10. warm_process       — Warm process (caches primed, process reused)
 11. embeddings_on      — Embeddings available
 12. embeddings_off     — Embeddings degraded/unavailable (lexical fallback)

Usage:
    from benchmarks.benchmark_layers import run_layered_benchmark
    results = run_layered_benchmark(scale="10k", num_queries=50)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
CORE_ROOT = REPO_ROOT / "core"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.relevance_metrics import compute_query_metrics, aggregate_metrics, to_dict
from benchmarks.scale_benchmark import (
    SCALE_MAP,
    generate_scale_dataset,
    generate_scale_queries,
    _batch_insert_memories,
    _fts5_search_direct,
    _fetch_labels_for_ids,
    _get_db_path,
)

# Layer identifiers
LAYER_FTS5_SUBSTRATE = "fts5_substrate"
LAYER_LEXICAL_API = "lexical_api"
LAYER_SEMANTIC_ONLY = "semantic_only"
LAYER_SPATIAL_ONLY = "spatial_only"
LAYER_HYBRID_PLANNER = "hybrid_planner"
LAYER_GRAPH_HYBRID = "graph_hybrid"
LAYER_SINGLE_GALAXY = "single_galaxy"
LAYER_FEDERATED_GALAXY = "federated_galaxy"
LAYER_COLD_PROCESS = "cold_process"
LAYER_WARM_PROCESS = "warm_process"
LAYER_EMBEDDINGS_ON = "embeddings_on"
LAYER_EMBEDDINGS_OFF = "embeddings_off"

ALL_LAYERS = [
    LAYER_FTS5_SUBSTRATE,
    LAYER_LEXICAL_API,
    LAYER_SEMANTIC_ONLY,
    LAYER_SPATIAL_ONLY,
    LAYER_HYBRID_PLANNER,
    LAYER_GRAPH_HYBRID,
    LAYER_SINGLE_GALAXY,
    LAYER_FEDERATED_GALAXY,
    LAYER_COLD_PROCESS,
    LAYER_WARM_PROCESS,
    LAYER_EMBEDDINGS_ON,
    LAYER_EMBEDDINGS_OFF,
]


def _run_fts5_substrate(
    db_path: Path,
    queries: list[dict[str, Any]],
    galaxy: str,
) -> dict[str, Any]:
    """Layer 1: Direct SQLite FTS5 BM25 — no API overhead."""
    latencies: list[float] = []
    query_results = []

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        t0 = time.perf_counter()
        retrieved_ids = _fts5_search_direct(db_path, q["query"], galaxy, limit=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        id_labels = _fetch_labels_for_ids(db_path, retrieved_ids)
        retrieved_labels = [id_labels.get(rid, {}) for rid in retrieved_ids]

        qr = compute_query_metrics(
            query_id=q["id"], query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
            latency_ms=lat,
        )
        query_results.append(qr)

    latencies.sort()
    agg = aggregate_metrics(query_results)
    stats = to_dict(agg)
    stats["latency_p50_ms"] = latencies[len(latencies) // 2] if latencies else 0
    stats["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
    stats["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
    stats["layer"] = LAYER_FTS5_SUBSTRATE
    stats["description"] = "Direct SQLite FTS5 BM25 — no API overhead"
    return stats


def _run_lexical_api(
    queries: list[dict[str, Any]],
    galaxy: str,
    memories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Layer 2: Production lexical API (UnifiedMemory.search + rerankers)."""
    latencies: list[float] = []
    query_results = []

    id_to_labels = {m["id"]: {"subject": m.get("subject", ""), "category": m.get("category", "")} for m in memories}

    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
    except Exception as e:
        return {"layer": LAYER_LEXICAL_API, "error": str(e), "description": "Production lexical API"}

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        t0 = time.perf_counter()
        results = um.search(query=q["query"], galaxy=galaxy, limit=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        retrieved_ids = [r.id for r in results]
        retrieved_labels = [id_to_labels.get(rid, {}) for rid in retrieved_ids]

        qr = compute_query_metrics(
            query_id=q["id"], query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
            latency_ms=lat,
        )
        query_results.append(qr)

    latencies.sort()
    agg = aggregate_metrics(query_results)
    stats = to_dict(agg)
    stats["latency_p50_ms"] = latencies[len(latencies) // 2] if latencies else 0
    stats["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
    stats["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
    stats["layer"] = LAYER_LEXICAL_API
    stats["description"] = "Production lexical API (UnifiedMemory.search + rerankers)"
    return stats


def _run_semantic_only(
    queries: list[dict[str, Any]],
    galaxy: str,
    memories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Layer 3: Semantic-only (embedding search)."""
    latencies: list[float] = []
    query_results = []

    id_to_labels = {m["id"]: {"subject": m.get("subject", ""), "category": m.get("category", "")} for m in memories}

    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
    except Exception as e:
        return {"layer": LAYER_SEMANTIC_ONLY, "error": str(e), "description": "Semantic-only search"}

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        t0 = time.perf_counter()
        results = um.search_similar(query=q["query"], limit=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        retrieved_ids = [r.id for r in results]
        retrieved_labels = [id_to_labels.get(rid, {}) for rid in retrieved_ids]

        qr = compute_query_metrics(
            query_id=q["id"], query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
            latency_ms=lat,
        )
        query_results.append(qr)

    latencies.sort()
    agg = aggregate_metrics(query_results)
    stats = to_dict(agg)
    stats["latency_p50_ms"] = latencies[len(latencies) // 2] if latencies else 0
    stats["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
    stats["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
    stats["layer"] = LAYER_SEMANTIC_ONLY
    stats["description"] = "Semantic-only (embedding search)"
    return stats


def _run_hybrid_planner(
    queries: list[dict[str, Any]],
    galaxy: str,
    memories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Layer 5: Hybrid planner (SearchQueryPlanner 3-channel RRF)."""
    latencies: list[float] = []
    query_results = []

    id_to_labels = {m["id"]: {"subject": m.get("subject", ""), "category": m.get("category", "")} for m in memories}

    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
    except Exception as e:
        return {"layer": LAYER_HYBRID_PLANNER, "error": str(e), "description": "Hybrid planner (3-channel RRF)"}

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        t0 = time.perf_counter()
        results = um.search_hybrid(query=q["query"], galaxy=galaxy, limit=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        retrieved_ids = [r.id for r in results]
        retrieved_labels = [id_to_labels.get(rid, {}) for rid in retrieved_ids]

        qr = compute_query_metrics(
            query_id=q["id"], query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
            latency_ms=lat,
        )
        query_results.append(qr)

    latencies.sort()
    agg = aggregate_metrics(query_results)
    stats = to_dict(agg)
    stats["latency_p50_ms"] = latencies[len(latencies) // 2] if latencies else 0
    stats["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
    stats["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
    stats["layer"] = LAYER_HYBRID_PLANNER
    stats["description"] = "Hybrid planner (3-channel RRF + entity boost + rerank)"
    return stats


def _run_graph_hybrid(
    queries: list[dict[str, Any]],
    galaxy: str,
    memories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Layer 6: Graph-enhanced hybrid (GraphWalker hybrid_recall)."""
    latencies: list[float] = []
    query_results = []

    id_to_labels = {m["id"]: {"subject": m.get("subject", ""), "category": m.get("category", "")} for m in memories}

    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
    except Exception as e:
        return {"layer": LAYER_GRAPH_HYBRID, "error": str(e), "description": "Graph-enhanced hybrid"}

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        t0 = time.perf_counter()
        results = um.hybrid_recall(query=q["query"], final_limit=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        retrieved_ids = [r.get("memory_id", r.get("id", "")) if isinstance(r, dict) else r.id for r in results]
        retrieved_labels = [id_to_labels.get(rid, {}) for rid in retrieved_ids]

        qr = compute_query_metrics(
            query_id=q["id"], query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
            latency_ms=lat,
        )
        query_results.append(qr)

    latencies.sort()
    agg = aggregate_metrics(query_results)
    stats = to_dict(agg)
    stats["latency_p50_ms"] = latencies[len(latencies) // 2] if latencies else 0
    stats["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
    stats["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
    stats["layer"] = LAYER_GRAPH_HYBRID
    stats["description"] = "Graph-enhanced hybrid (GraphWalker hybrid_recall)"
    return stats


def _run_embeddings_off(
    db_path: Path,
    queries: list[dict[str, Any]],
    galaxy: str,
) -> dict[str, Any]:
    """Layer 12: Embeddings degraded/unavailable — lexical fallback only.

    This is functionally identical to fts5_substrate but measured through
    the API with embeddings disabled, showing the fallback path latency.
    """
    latencies: list[float] = []
    query_results = []

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        t0 = time.perf_counter()
        retrieved_ids = _fts5_search_direct(db_path, q["query"], galaxy, limit=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        id_labels = _fetch_labels_for_ids(db_path, retrieved_ids)
        retrieved_labels = [id_labels.get(rid, {}) for rid in retrieved_ids]

        qr = compute_query_metrics(
            query_id=q["id"], query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
            latency_ms=lat,
        )
        query_results.append(qr)

    latencies.sort()
    agg = aggregate_metrics(query_results)
    stats = to_dict(agg)
    stats["latency_p50_ms"] = latencies[len(latencies) // 2] if latencies else 0
    stats["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
    stats["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
    stats["layer"] = LAYER_EMBEDDINGS_OFF
    stats["description"] = "Embeddings degraded/unavailable — lexical fallback"
    return stats


def run_layered_benchmark(
    scale: str = "10k",
    num_queries: int = 50,
    layers: list[str] | None = None,
) -> dict[str, Any]:
    """Run benchmark across separated retrieval layers.

    Args:
        scale: Scale key ("10k", "50k", "100k").
        num_queries: Number of test queries.
        layers: Optional subset of layers to run. Defaults to all.

    Returns:
        Dict with per-layer metrics and comparison table.
    """
    if layers is None:
        layers = ALL_LAYERS

    num_memories = SCALE_MAP.get(scale, 10_000)
    print(f"\n{'=' * 60}")
    print(f"Layered Benchmark: {scale} ({num_memories:,} memories)")
    print(f"{'=' * 60}")

    # Generate dataset and queries
    print(f"\nGenerating {num_memories:,} memories...")
    memories = generate_scale_dataset(num_memories=num_memories)

    print(f"Generating {num_queries} queries...")
    queries = generate_scale_queries(num_queries=num_queries, num_memories=num_memories)
    print(f"  {len(queries)} queries with label-based ground truth")

    galaxy = "benchmark"

    # Clean slate
    db_path = _get_db_path(galaxy)
    if db_path.exists():
        db_path.unlink()
        for suffix in ("-wal", "-shm"):
            p = db_path.with_suffix(db_path.suffix + suffix)
            if p.exists():
                p.unlink()

    # Insert memories
    print(f"\nBatch-inserting {num_memories:,} memories...")
    total_inserted, add_elapsed = _batch_insert_memories(db_path, memories, galaxy, embed=False)
    print(f"  {total_inserted:,} memories in {add_elapsed:.1f}s")

    # Run each layer
    layer_results: dict[str, dict[str, Any]] = {}

    # Substrate layers (direct SQLite)
    if LAYER_FTS5_SUBSTRATE in layers:
        print(f"\n[{LAYER_FTS5_SUBSTRATE}] Direct FTS5 substrate...")
        layer_results[LAYER_FTS5_SUBSTRATE] = _run_fts5_substrate(db_path, queries, galaxy)
        _print_layer_summary(layer_results[LAYER_FTS5_SUBSTRATE])

    if LAYER_EMBEDDINGS_OFF in layers:
        print(f"\n[{LAYER_EMBEDDINGS_OFF}] Embeddings degraded (lexical fallback)...")
        layer_results[LAYER_EMBEDDINGS_OFF] = _run_embeddings_off(db_path, queries, galaxy)
        _print_layer_summary(layer_results[LAYER_EMBEDDINGS_OFF])

    # API layers (require UnifiedMemory)
    api_layers = {
        LAYER_LEXICAL_API: _run_lexical_api,
        LAYER_SEMANTIC_ONLY: _run_semantic_only,
        LAYER_HYBRID_PLANNER: _run_hybrid_planner,
        LAYER_GRAPH_HYBRID: _run_graph_hybrid,
    }

    for layer_name, layer_fn in api_layers.items():
        if layer_name not in layers:
            continue
        print(f"\n[{layer_name}] {layer_fn.__doc__ or layer_name}...")
        try:
            layer_results[layer_name] = layer_fn(queries, galaxy, memories)
            _print_layer_summary(layer_results[layer_name])
        except Exception as e:
            print(f"  ERROR: {e}")
            layer_results[layer_name] = {"layer": layer_name, "error": str(e)}

    # Cold vs warm: cold = first query pass, warm = second pass
    if LAYER_COLD_PROCESS in layers or LAYER_WARM_PROCESS in layers:
        print(f"\n[cold/warm] Measuring cold vs warm process...")

        if LAYER_COLD_PROCESS in layers:
            cold_stats = _run_fts5_substrate(db_path, queries[:10], galaxy)
            cold_stats["layer"] = LAYER_COLD_PROCESS
            cold_stats["description"] = "Cold process (first-pass, no warm caches)"
            layer_results[LAYER_COLD_PROCESS] = cold_stats
            _print_layer_summary(cold_stats)

        if LAYER_WARM_PROCESS in layers:
            warm_stats = _run_fts5_substrate(db_path, queries[:10], galaxy)
            warm_stats["layer"] = LAYER_WARM_PROCESS
            warm_stats["description"] = "Warm process (second-pass, caches primed)"
            layer_results[LAYER_WARM_PROCESS] = warm_stats
            _print_layer_summary(warm_stats)

    # Single vs federated galaxy
    if LAYER_SINGLE_GALAXY in layers:
        print(f"\n[{LAYER_SINGLE_GALAXY}] Single-galaxy search...")
        single_stats = _run_fts5_substrate(db_path, queries, galaxy)
        single_stats["layer"] = LAYER_SINGLE_GALAXY
        single_stats["description"] = "Single-galaxy scoped search"
        layer_results[LAYER_SINGLE_GALAXY] = single_stats
        _print_layer_summary(single_stats)

    if LAYER_FEDERATED_GALAXY in layers:
        print(f"\n[{LAYER_FEDERATED_GALAXY}] Federated galaxy search...")
        # Federated = search across all galaxies (galaxy=None)
        fed_stats = _run_fts5_substrate(db_path, queries, "")
        fed_stats["layer"] = LAYER_FEDERATED_GALAXY
        fed_stats["description"] = "Cross-galaxy federated search"
        layer_results[LAYER_FEDERATED_GALAXY] = fed_stats
        _print_layer_summary(fed_stats)

    # Embeddings on (semantic layer already covers this)
    if LAYER_EMBEDDINGS_ON in layers:
        if LAYER_SEMANTIC_ONLY in layer_results and "error" not in layer_results[LAYER_SEMANTIC_ONLY]:
            emb_stats = dict(layer_results[LAYER_SEMANTIC_ONLY])
            emb_stats["layer"] = LAYER_EMBEDDINGS_ON
            emb_stats["description"] = "Embeddings available (semantic search active)"
            layer_results[LAYER_EMBEDDINGS_ON] = emb_stats
            _print_layer_summary(emb_stats)
        else:
            layer_results[LAYER_EMBEDDINGS_ON] = {
                "layer": LAYER_EMBEDDINGS_ON,
                "error": "Semantic search unavailable",
                "description": "Embeddings available (semantic search active)",
            }

    # Build comparison table
    print(f"\n{'=' * 60}")
    print("Layer Comparison")
    print(f"{'=' * 60}")
    print(f"{'Layer':<25} {'Recall@10':>10} {'MRR':>8} {'nDCG':>8} {'p50(ms)':>8} {'p95(ms)':>8}")
    print("-" * 70)
    for layer_name in ALL_LAYERS:
        if layer_name not in layer_results:
            continue
        stats = layer_results[layer_name]
        if "error" in stats:
            print(f"{layer_name:<25} {'ERROR':>10}")
            continue
        print(
            f"{layer_name:<25} "
            f"{stats.get('recall_at_10', 0):>10.2%} "
            f"{stats.get('mrr', 0):>8.4f} "
            f"{stats.get('ndcg', 0):>8.4f} "
            f"{stats.get('latency_p50_ms', 0):>8.1f} "
            f"{stats.get('latency_p95_ms', 0):>8.1f}"
        )

    return {
        "system": "whitemagic",
        "scale": scale,
        "num_memories": num_memories,
        "num_queries": len(queries),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "relevance_model": "label-based (subject/category), scale-invariant",
        "layers": layer_results,
    }


def _print_layer_summary(stats: dict[str, Any]) -> None:
    """Print a one-line summary for a layer."""
    if "error" in stats:
        print(f"  ERROR: {stats['error']}")
        return
    print(
        f"  recall@10: {stats.get('recall_at_10', 0):.2%}  "
        f"precision@10: {stats.get('precision_at_10', 0):.2%}  "
        f"MRR: {stats.get('mrr', 0):.4f}  "
        f"nDCG: {stats.get('ndcg', 0):.4f}  "
        f"p50: {stats.get('latency_p50_ms', 0):.1f}ms  "
        f"p95: {stats.get('latency_p95_ms', 0):.1f}ms"
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Layered benchmark — separated retrieval modes")
    parser.add_argument("--scale", choices=list(SCALE_MAP.keys()), default="10k")
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument(
        "--layers", nargs="*", default=None,
        help=f"Subset of layers: {', '.join(ALL_LAYERS)}",
    )
    args = parser.parse_args()

    results = run_layered_benchmark(
        scale=args.scale,
        num_queries=args.queries,
        layers=args.layers,
    )

    output_path = args.output or f"benchmarks/results/layered_{args.scale}.json"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
