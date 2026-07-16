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
    queries: list[dict[str, str | list[str]]],
    galaxy: str = "benchmark",
    limit: int = 10,
    id_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Benchmark recall quality. Returns recall@K, MRR, and per-query data.

    If id_map is provided, expected dataset IDs (mem_0000) are translated to
    actual memory UUIDs before matching against search results.
    """
    recall_at_1 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    mrr_sum = 0.0
    total = 0
    per_query: list[dict[str, float]] = []

    for q in queries:
        expected_ds = set(q.get("expected_ids", []))
        if not expected_ds:
            continue

        # Translate dataset IDs to actual UUIDs if mapping available
        if id_map:
            expected = {id_map[ds_id] for ds_id in expected_ds if ds_id in id_map}
        else:
            expected = expected_ds
        if not expected:
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

        retrieved_set = set(retrieved_ids)
        # Recall@K: at least one expected ID appears in top K results
        match_ranks = [i + 1 for i, rid in enumerate(retrieved_ids) if rid in expected]
        q_r1 = 1.0 if any(r <= 1 for r in match_ranks) else 0.0
        q_r5 = 1.0 if any(r <= 5 for r in match_ranks) else 0.0
        q_r10 = 1.0 if match_ranks else 0.0
        q_mrr = 0.0
        for rank, rid in enumerate(retrieved_ids, 1):
            if rid in expected:
                q_mrr = 1.0 / rank
                break

        recall_at_1 += q_r1
        recall_at_5 += q_r5
        recall_at_10 += q_r10
        mrr_sum += q_mrr
        per_query.append({
            "recall_at_1": q_r1,
            "recall_at_5": q_r5,
            "recall_at_10": q_r10,
            "mrr": q_mrr,
        })

        total += 1

    return {
        "total_queries": total,
        "recall_at_1": recall_at_1 / total if total > 0 else 0,
        "recall_at_5": recall_at_5 / total if total > 0 else 0,
        "recall_at_10": recall_at_10 / total if total > 0 else 0,
        "mrr": mrr_sum / total if total > 0 else 0,
        "per_query": per_query,
    }


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
