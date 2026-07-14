"""Benchmark orchestrator — runs all benchmarks and generates a comparison report.

Usage:
    python benchmarks/run_all.py
    python benchmarks/run_all.py --memories 100 --queries 50 --output benchmarks/results.json
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_whitemagic(num_memories: int, num_queries: int) -> dict[str, Any]:
    """Run WhiteMagic benchmark."""
    from benchmarks.whitemagic_benchmark import run_benchmark
    return run_benchmark(num_memories=num_memories, num_queries=num_queries)


def run_mem0(num_memories: int, num_queries: int) -> dict[str, Any]:
    """Run Mem0 benchmark (if installed)."""
    try:
        from mem0 import Memory
    except ImportError:
        return {"system": "mem0", "error": "mem0ai not installed", "skipped": True}

    from benchmarks.dataset import generate_dataset, generate_queries

    memories = generate_dataset(num_memories=num_memories)
    queries = generate_queries(num_queries=num_queries)

    m = Memory()
    add_latencies = []
    for mem in memories:
        start = time.perf_counter()
        m.add(messages=mem["content"], user_id="bench")
        add_latencies.append((time.perf_counter() - start) * 1000)

    search_latencies = []
    for q in queries:
        start = time.perf_counter()
        m.search(query=q["query"], user_id="bench")
        search_latencies.append((time.perf_counter() - start) * 1000)

    add_latencies.sort()
    search_latencies.sort()
    return {
        "system": "mem0",
        "add": {
            "count": len(add_latencies),
            "total_ms": sum(add_latencies),
            "p50_ms": add_latencies[len(add_latencies) // 2],
            "p95_ms": add_latencies[int(len(add_latencies) * 0.95)],
            "throughput_ops_sec": len(add_latencies) / (sum(add_latencies) / 1000) if sum(add_latencies) > 0 else 0,
        },
        "search": {
            "count": len(search_latencies),
            "total_ms": sum(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2],
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)],
            "throughput_ops_sec": len(search_latencies) / (sum(search_latencies) / 1000) if sum(search_latencies) > 0 else 0,
        },
        "recall": {"note": "Recall quality not available for Mem0 (no ground truth matching)"},
    }


def run_langchain(num_memories: int, num_queries: int) -> dict[str, Any]:
    """Run LangChain ConversationBufferMemory benchmark (if installed)."""
    try:
        from langchain.memory import ConversationBufferMemory
    except ImportError:
        return {"system": "langchain", "error": "langchain not installed", "skipped": True}

    from benchmarks.dataset import generate_dataset, generate_queries

    memories = generate_dataset(num_memories=num_memories)
    queries = generate_queries(num_queries=num_queries)

    memory = ConversationBufferMemory()
    add_latencies = []
    for mem in memories:
        start = time.perf_counter()
        memory.chat_memory.add_user_message(mem["content"])
        memory.chat_memory.add_ai_message(f"Acknowledged: {mem['content'][:50]}")
        add_latencies.append((time.perf_counter() - start) * 1000)

    # LangChain buffer memory doesn't have semantic search — it returns all messages
    search_latencies = []
    for q in queries:
        start = time.perf_counter()
        memory.load_memory_variables({})
        search_latencies.append((time.perf_counter() - start) * 1000)

    add_latencies.sort()
    search_latencies.sort()
    return {
        "system": "langchain",
        "add": {
            "count": len(add_latencies),
            "total_ms": sum(add_latencies),
            "p50_ms": add_latencies[len(add_latencies) // 2],
            "p95_ms": add_latencies[int(len(add_latencies) * 0.95)],
            "throughput_ops_sec": len(add_latencies) / (sum(add_latencies) / 1000) if sum(add_latencies) > 0 else 0,
        },
        "search": {
            "count": len(search_latencies),
            "total_ms": sum(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2],
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)],
            "throughput_ops_sec": len(search_latencies) / (sum(search_latencies) / 1000) if sum(search_latencies) > 0 else 0,
        },
        "recall": {"note": "LangChain buffer memory has no semantic search — recall not applicable"},
    }


def generate_report(results: list[dict[str, Any]], output: str | None = None) -> str:
    """Generate a markdown report from benchmark results."""
    lines = [
        "# WhiteMagic Benchmark Report",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Platform**: {platform.system()} {platform.machine()}",
        f"**Python**: {platform.python_version()}",
        "",
        "## Results",
        "",
        "| System | Add p50 (ms) | Add p95 (ms) | Add ops/sec | Search p50 (ms) | Search p95 (ms) | Search ops/sec | Recall@1 | Recall@5 | MRR |",
        "|--------|-------------|-------------|------------|----------------|----------------|---------------|----------|----------|-----|",
    ]

    for r in results:
        if r.get("skipped"):
            lines.append(f"| {r['system']} | skipped | | | | | | | | |")
            continue

        add = r.get("add", {})
        search = r.get("search", {})
        recall = r.get("recall", {})

        add_p50 = f"{add.get('p50_ms', 0):.1f}" if add else "N/A"
        add_p95 = f"{add.get('p95_ms', 0):.1f}" if add else "N/A"
        add_tput = f"{add.get('throughput_ops_sec', 0):.1f}" if add else "N/A"
        search_p50 = f"{search.get('p50_ms', 0):.1f}" if search else "N/A"
        search_p95 = f"{search.get('p95_ms', 0):.1f}" if search else "N/A"
        search_tput = f"{search.get('throughput_ops_sec', 0):.1f}" if search else "N/A"
        recall_1 = f"{recall.get('recall_at_1', 0):.2%}" if "recall_at_1" in recall else "N/A"
        recall_5 = f"{recall.get('recall_at_5', 0):.2%}" if "recall_at_5" in recall else "N/A"
        mrr = f"{recall.get('mrr', 0):.4f}" if "mrr" in recall else "N/A"

        lines.append(f"| {r['system']} | {add_p50} | {add_p95} | {add_tput} | {search_p50} | {search_p95} | {search_tput} | {recall_1} | {recall_5} | {mrr} |")

    lines.extend([
        "",
        "## Notes",
        "",
        "- Dataset: deterministic (seed=42), 1,000 memories with known semantic relationships",
        "- Queries: 100 test queries with known correct answers for recall measurement",
        "- WhiteMagic uses HNSW + FTS5 hybrid search with fastembed embeddings",
        "- LangChain ConversationBufferMemory has no semantic search (linear scan only)",
        "- Mem0 uses OpenAI embeddings by default (requires API key)",
        "",
    ])

    report = "\n".join(lines)

    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"Report saved to {output}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all benchmarks")
    parser.add_argument("--memories", type=int, default=100, help="Number of memories")
    parser.add_argument("--queries", type=int, default=50, help="Number of queries")
    parser.add_argument("--output", "-o", default="benchmarks/results.json", help="Output JSON file")
    parser.add_argument("--report", default="benchmarks/REPORT.md", help="Output markdown report")
    parser.add_argument("--skip-mem0", action="store_true", help="Skip Mem0 benchmark")
    parser.add_argument("--skip-langchain", action="store_true", help="Skip LangChain benchmark")
    args = parser.parse_args()

    all_results = []

    print("=" * 60)
    print("WhiteMagic Benchmark Suite")
    print("=" * 60)

    print("\n--- WhiteMagic ---")
    wm_results = run_whitemagic(args.memories, args.queries)
    all_results.append(wm_results)

    if not args.skip_mem0:
        print("\n--- Mem0 ---")
        mem0_results = run_mem0(args.memories, args.queries)
        all_results.append(mem0_results)

    if not args.skip_langchain:
        print("\n--- LangChain ---")
        lc_results = run_langchain(args.memories, args.queries)
        all_results.append(lc_results)

    # Save JSON results
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {args.output}")

    # Generate report
    report = generate_report(all_results, output=args.report)
    print("\n" + report)


if __name__ == "__main__":
    main()
