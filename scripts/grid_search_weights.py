#!/usr/bin/env python3
"""Grid search over fusion weights for WhiteMagic v5 hybrid recall.

Runs the LongMemEval-S benchmark with different BM25/vector/importance
weight combinations and prints a comparison table.

Requires a running llama-server with --embeddings for vector search.
Set WM_EMBEDDER_ENDPOINT before running.

Usage:
    export WM_EMBEDDER_ENDPOINT=http://localhost:8081
    python3 scripts/grid_search_weights.py --max-questions 10
    python3 scripts/grid_search_weights.py --max-questions 50 --output benchmarks/results/grid_search.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BENCH_SCRIPT = os.path.join(SCRIPT_DIR, "longmemeval_bench.py")
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "benchmarks", "results")

# Weight combinations to try
# Weights are normalized to sum to 1.0 by RecallConfig::from_env()
GRID = [
    {"bm25": 0.5, "vector": 0.3, "importance": 0.2, "label": "default"},
    {"bm25": 0.7, "vector": 0.2, "importance": 0.1, "label": "bm25-dominant"},
    {"bm25": 0.3, "vector": 0.5, "importance": 0.2, "label": "vector-dominant"},
    {"bm25": 0.4, "vector": 0.4, "importance": 0.2, "label": "balanced"},
    {"bm25": 0.6, "vector": 0.3, "importance": 0.1, "label": "bm25-heavy"},
    {"bm25": 0.2, "vector": 0.6, "importance": 0.2, "label": "vector-heavy"},
    {"bm25": 0.5, "vector": 0.5, "importance": 0.0, "label": "no-importance"},
]


def run_single(
    binary: str,
    dataset: str,
    max_questions: int,
    limit: int,
    weights: dict,
    output_path: str,
) -> dict:
    """Run the benchmark with specific fusion weights."""
    env = os.environ.copy()
    env["WM_RECALL_BM25_WEIGHT"] = str(weights["bm25"])
    env["WM_RECALL_VECTOR_WEIGHT"] = str(weights["vector"])
    env["WM_RECALL_IMPORTANCE_WEIGHT"] = str(weights["importance"])

    cmd = [
        sys.executable,
        BENCH_SCRIPT,
        "--binary", binary,
        "--dataset", dataset,
        "--max-questions", str(max_questions),
        "--limit", str(limit),
        "--output", output_path,
    ]

    print(f"\n{'='*70}")
    print(f"  Grid: {weights['label']}  (bm25={weights['bm25']} vector={weights['vector']} imp={weights['importance']})")
    print(f"{'='*70}")
    sys.stdout.flush()

    t0 = time.perf_counter()
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
    elapsed = time.perf_counter() - t0

    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        print(result.stderr[-500:])
        return {
            "label": weights["label"],
            "weights": weights,
            "status": "failed",
            "error": result.stderr[-500:],
            "elapsed_s": round(elapsed, 1),
        }

    # Parse the output JSON
    try:
        data = json.loads(Path(output_path).read_text())
        recall = data.get("recall", {})
        return {
            "label": weights["label"],
            "weights": weights,
            "status": "success",
            "recall_at_1": recall.get("recall_at_1", 0),
            "recall_at_5": recall.get("recall_at_5", 0),
            "recall_at_10": recall.get("recall_at_10", 0),
            "mrr": recall.get("mrr", 0),
            "total_elapsed_s": data.get("total_elapsed_s", 0),
            "search_p50_ms": data.get("search", {}).get("p50_ms", 0),
            "category_results": data.get("category_results", {}),
        }
    except Exception as e:
        print(f"  Parse error: {e}")
        return {
            "label": weights["label"],
            "weights": weights,
            "status": "parse_error",
            "error": str(e),
            "elapsed_s": round(elapsed, 1),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid search over fusion weights")
    parser.add_argument("--binary", default=None, help="Path to wm binary")
    parser.add_argument("--dataset", default=None, help="Path to LongMemEval-S dataset")
    parser.add_argument("--max-questions", type=int, default=10, help="Questions per run")
    parser.add_argument("--limit", type=int, default=10, help="Results per query")
    parser.add_argument("--output", default=None, help="Output JSON path for grid search results")
    parser.add_argument("--grid", default=None, help="Custom grid JSON file (overrides built-in grid)")
    args = parser.parse_args()

    # Find binary
    binary = args.binary
    if not binary:
        for profile in ("release", "debug"):
            candidate = os.path.join(REPO_ROOT, "target", profile, "wm")
            if os.path.isfile(candidate):
                binary = candidate
                break
    if not binary:
        print("Error: wm binary not found. Build it first or pass --binary.")
        sys.exit(1)

    dataset = args.dataset or "/home/lucas/Desktop/WHITEMAGIC/benchmarks/data/longmemeval_s"

    # Load grid
    grid = GRID
    if args.grid:
        grid = json.loads(Path(args.grid).read_text())

    # Check embedder endpoint
    if not os.environ.get("WM_EMBEDDER_ENDPOINT"):
        print("WARNING: WM_EMBEDDER_ENDPOINT not set. Vector search will not activate.")
        print("         The grid search will only test BM25-only paths.\n")

    os.makedirs(DEFAULT_OUTPUT, exist_ok=True)
    output_path = args.output or os.path.join(DEFAULT_OUTPUT, "grid_search_weights.json")

    results = []
    for weights in grid:
        single_output = os.path.join(
            DEFAULT_OUTPUT,
            f"grid_{weights['label']}_{args.max_questions}q.json",
        )
        result = run_single(binary, dataset, args.max_questions, args.limit, weights, single_output)
        results.append(result)

        if result["status"] == "success":
            print(f"  R@1={result['recall_at_1']:.2%} R@5={result['recall_at_5']:.2%} "
                  f"R@10={result['recall_at_10']:.2%} MRR={result['mrr']:.4f}")

    # Save combined results
    combined = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "max_questions": args.max_questions,
        "limit": args.limit,
        "embedder_endpoint": os.environ.get("WM_EMBEDDER_ENDPOINT", "(not set)"),
        "results": results,
    }
    Path(output_path).write_text(json.dumps(combined, indent=2), encoding="utf-8")

    # Print comparison table
    print(f"\n{'='*80}")
    print("Grid Search Results")
    print(f"{'='*80}")
    print(f"{'Label':<20} {'BM25':>5} {'Vec':>5} {'Imp':>5} {'R@1':>7} {'R@5':>7} {'R@10':>7} {'MRR':>7}")
    print("-" * 80)
    for r in results:
        if r["status"] == "success":
            w = r["weights"]
            print(f"{r['label']:<20} {w['bm25']:>5.1f} {w['vector']:>5.1f} {w['importance']:>5.1f} "
                  f"{r['recall_at_1']:>7.2%} {r['recall_at_5']:>7.2%} {r['recall_at_10']:>7.2%} "
                  f"{r['mrr']:>7.4f}")
        else:
            print(f"{r['label']:<20} {'FAILED':>40}")

    # Find best
    successful = [r for r in results if r["status"] == "success"]
    if successful:
        best_r1 = max(successful, key=lambda r: r["recall_at_1"])
        best_r5 = max(successful, key=lambda r: r["recall_at_5"])
        best_mrr = max(successful, key=lambda r: r["mrr"])
        print(f"\nBest R@1:  {best_r1['label']} ({best_r1['recall_at_1']:.2%})")
        print(f"Best R@5:  {best_r5['label']} ({best_r5['recall_at_5']:.2%})")
        print(f"Best MRR:  {best_mrr['label']} ({best_mrr['mrr']:.4f})")

    print(f"\nFull results saved to {output_path}")


if __name__ == "__main__":
    main()
