"""WhiteMagic benchmark — measures latency, throughput, and recall quality.

Uses the deterministic dataset from benchmarks/dataset.py.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from benchmarks.dataset import generate_dataset, generate_queries
from benchmarks.relevance_metrics import compute_query_metrics, aggregate_metrics, to_dict


def _call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    """Call a WhiteMagic tool."""
    from whitemagic.tools.unified_api import call_tool
    return call_tool(name, **kwargs)


def benchmark_add_memories(
    memories: list[dict[str, str]],
    galaxy: str = "benchmark",
) -> tuple[dict[str, float], dict[str, str]]:
    """Benchmark adding memories. Returns timing stats and ID mapping.

    Returns (stats, id_map) where id_map maps dataset IDs (mem_0000) to
    actual memory UUIDs returned by create_memory.
    """
    latencies = []
    id_map: dict[str, str] = {}

    for mem in memories:
        start = time.perf_counter()
        result = _call_tool(
            "create_memory",
            title=mem["id"],
            content=mem["content"],
            galaxy=galaxy,
            tags=mem["tags"],
        )
        latencies.append((time.perf_counter() - start) * 1000)

        actual_id = None
        if isinstance(result, dict):
            actual_id = result.get("memory_id") or result.get("details", {}).get("memory_id")
        if actual_id:
            id_map[mem["id"]] = actual_id

    latencies.sort()
    stats = {
        "count": len(latencies),
        "total_ms": sum(latencies),
        "p50_ms": latencies[len(latencies) // 2],
        "p95_ms": latencies[int(len(latencies) * 0.95)],
        "p99_ms": latencies[int(len(latencies) * 0.99)],
        "throughput_ops_sec": len(latencies) / (sum(latencies) / 1000) if sum(latencies) > 0 else 0,
    }
    return stats, id_map


def benchmark_search(
    queries: list[dict[str, str | list[str]]],
    galaxy: str = "benchmark",
    limit: int = 10,
) -> dict[str, float]:
    """Benchmark search. Returns timing stats."""
    latencies = []

    for q in queries:
        start = time.perf_counter()
        _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=limit,
        )
        latencies.append((time.perf_counter() - start) * 1000)

    latencies.sort()
    return {
        "count": len(latencies),
        "total_ms": sum(latencies),
        "p50_ms": latencies[len(latencies) // 2],
        "p95_ms": latencies[int(len(latencies) * 0.95)],
        "p99_ms": latencies[int(len(latencies) * 0.99)],
        "throughput_ops_sec": len(latencies) / (sum(latencies) / 1000) if sum(latencies) > 0 else 0,
    }


def benchmark_recall(
    queries: list[dict[str, Any]],
    galaxy: str = "benchmark",
    limit: int = 10,
    id_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Benchmark recall quality using label-based relevance.

    Uses relevance_labels (subject/category) for scale-invariant metrics.
    If id_map is provided, it's used to map retrieved UUIDs back to dataset IDs
    for label lookup.
    """
    # Build reverse map: actual UUID → dataset ID
    rev_map = {v: k for k, v in id_map.items()} if id_map else {}

    # Build dataset label index: dataset_id → labels
    dataset = generate_dataset()
    id_to_labels = {m["id"]: {"subject": m["subject"], "category": m["category"]} for m in dataset}

    query_results = []

    for q in queries:
        relevance_labels = q.get("relevance_labels")
        relevant_count = q.get("relevant_count", 0)
        if not relevance_labels or relevant_count == 0:
            continue

        result = _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=limit,
        )

        retrieved_ids = []
        if result.get("status") == "success":
            details = result.get("details", {})
            data = details.get("memories", details.get("data", details.get("results", [])))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        rid = item.get("id", item.get("memory_id", ""))
                        retrieved_ids.append(rid)

        # Map retrieved UUIDs back to dataset IDs for label lookup
        retrieved_labels = []
        for rid in retrieved_ids:
            ds_id = rev_map.get(rid, rid)
            retrieved_labels.append(id_to_labels.get(ds_id, {}))

        qr = compute_query_metrics(
            query_id=q["id"],
            query=q["query"],
            relevance_labels=relevance_labels,
            retrieved_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            relevant_count=relevant_count,
        )
        query_results.append(qr)

    agg = aggregate_metrics(query_results)
    return to_dict(agg)


def run_benchmark(
    num_memories: int = 100,
    num_queries: int = 50,
    galaxy: str = "benchmark",
) -> dict[str, Any]:
    """Run full WhiteMagic benchmark suite."""
    print(f"Generating dataset ({num_memories} memories, {num_queries} queries)...")
    memories = generate_dataset(num_memories=num_memories)
    queries = generate_queries(num_queries=num_queries)

    # Ensure the benchmark galaxy exists
    try:
        _call_tool("galaxy.create", name=galaxy)
        print(f"  Galaxy '{galaxy}' created/confirmed")
    except Exception:
        pass

    print("Benchmarking add_memories...")
    add_stats, id_map = benchmark_add_memories(memories, galaxy=galaxy)
    print(f"  {add_stats['count']} memories added in {add_stats['total_ms']:.1f}ms "
          f"({add_stats['throughput_ops_sec']:.1f} ops/sec)")
    print(f"  {len(id_map)}/{len(memories)} IDs mapped")

    print("Benchmarking search...")
    search_stats = benchmark_search(queries, galaxy=galaxy)
    print(f"  {search_stats['count']} searches in {search_stats['total_ms']:.1f}ms "
          f"({search_stats['throughput_ops_sec']:.1f} ops/sec)")

    print("Benchmarking recall quality...")
    recall_stats = benchmark_recall(queries, galaxy=galaxy, id_map=id_map)
    print(f"  recall@1: {recall_stats['recall_at_1']:.2%}")
    print(f"  recall@5: {recall_stats['recall_at_5']:.2%}")
    print(f"  recall@10: {recall_stats['recall_at_10']:.2%}")
    print(f"  MRR: {recall_stats['mrr']:.4f}")

    return {
        "system": "whitemagic",
        "add": add_stats,
        "search": search_stats,
        "recall": recall_stats,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WhiteMagic benchmark")
    parser.add_argument("--memories", type=int, default=100, help="Number of memories to add")
    parser.add_argument("--queries", type=int, default=50, help="Number of queries to search")
    parser.add_argument("--galaxy", default="benchmark", help="Galaxy to use")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    args = parser.parse_args()

    results = run_benchmark(
        num_memories=args.memories,
        num_queries=args.queries,
        galaxy=args.galaxy,
    )

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {args.output}")
