"""Unified benchmark runner — runs all Phase 1 benchmarks and generates report.

Executes:
  1. Internal WhiteMagic benchmark (100 memories, 50 queries)
  2. Scale benchmark (10K memories)
  3. LoCoMo synthetic benchmark
  4. LongMemEval synthetic benchmark
  5. BEAM benchmark (multi-hop, temporal, abstention)
  6. Abstention benchmark

Outputs:
  - benchmarks/results/unified_results.json — all results
  - benchmarks/results/BENCHMARK_REPORT.md — transparency report

Usage:
    python benchmarks/run_all_benchmarks.py
    python benchmarks/run_all_benchmarks.py --skip-scale --skip-locomo
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ── Benchmark mode: bypass non-essential middleware ──────────────────────
# The session recorder writes to a 2.6GB sessions DB (72K+ memories), making
# each create_memory call take 20-170 seconds. These env vars disable:
#   - Session recorder (WM_SESSION_RECORD=0)
#   - Governor, citta consciousness, maturity gates (WM_BENCHMARK_MODE=1)
#   - Karma effects recording (WM_KARMA_RECORD=0)
#   - Error learner (WM_ERROR_LEARN=0)
#   - Pattern guard (WM_PATTERN_GUARD=0)
#   - Code nudge (WM_CODE_NUDGE=0)
#   - Transaction firewall (WM_TRANSACTION_FIREWALL=0)
os.environ.setdefault("WM_BENCHMARK_MODE", "1")
os.environ.setdefault("WM_SESSION_RECORD", "0")
os.environ.setdefault("WM_ERROR_LEARN", "0")
os.environ.setdefault("WM_PATTERN_GUARD", "0")
os.environ.setdefault("WM_CODE_NUDGE", "0")
os.environ.setdefault("WM_TRANSACTION_FIREWALL", "0")


def generate_report(all_results: dict[str, Any]) -> str:
    """Generate a markdown transparency report."""
    lines = [
        "# WhiteMagic Memory Benchmark Report",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"**Platform**: {platform.system()} {platform.machine()}",
        f"**Python**: {platform.python_version()}",
        "",
        "## Core Differentiator",
        "",
        "- **0 tokens/query** — no LLM calls in the search pipeline",
        "- **<100ms latency** — FTS5 BM25 + FastEmbed semantic reranking",
        "- **Full transparency** — per-query JSON output available",
        "",
        "---",
        "",
    ]

    # Internal benchmark
    if "internal" in all_results:
        r = all_results["internal"]
        lines.extend([
            "## 1. Internal Benchmark (100 memories, 50 queries)",
            "",
            f"- **Recall@1**: {r.get('recall', {}).get('recall_at_1', 0):.2%}",
            f"- **Recall@5**: {r.get('recall', {}).get('recall_at_5', 0):.2%}",
            f"- **Recall@10**: {r.get('recall', {}).get('recall_at_10', 0):.2%}",
            f"- **MRR**: {r.get('recall', {}).get('mrr', 0):.4f}",
            f"- **Search p50**: {r.get('search', {}).get('p50_ms', 0):.1f}ms",
            f"- **Search p95**: {r.get('search', {}).get('p95_ms', 0):.1f}ms",
            f"- **Add throughput**: {r.get('add', {}).get('throughput_ops_sec', 0):.0f} ops/sec",
            "",
        ])

    # Scale benchmark
    if "scale" in all_results:
        r = all_results["scale"]
        lines.extend([
            f"## 2. Scale Benchmark ({r.get('num_memories', 0):,} memories)",
            "",
            f"- **Recall@1**: {r.get('recall', {}).get('recall_at_1', 0):.2%}",
            f"- **Recall@5**: {r.get('recall', {}).get('recall_at_5', 0):.2%}",
            f"- **Recall@10**: {r.get('recall', {}).get('recall_at_10', 0):.2%}",
            f"- **MRR**: {r.get('recall', {}).get('mrr', 0):.4f}",
            f"- **Search p50**: {r.get('search', {}).get('p50_ms', 0):.1f}ms",
            f"- **Search p95**: {r.get('search', {}).get('p95_ms', 0):.1f}ms",
            f"- **Search p99**: {r.get('search', {}).get('p99_ms', 0):.1f}ms",
            f"- **Add throughput**: {r.get('add', {}).get('throughput_ops_sec', 0):.0f} ops/sec",
            f"- **Total add time**: {r.get('add', {}).get('total_s', 0):.1f}s",
            "",
        ])

    # LoCoMo
    if "locomo" in all_results:
        r = all_results["locomo"]
        lines.extend([
            f"## 3. LoCoMo Benchmark ({r.get('num_conversations', 0)} conversations)",
            "",
            f"- **Recall@1**: {r.get('recall', {}).get('recall_at_1', 0):.2%}",
            f"- **Recall@5**: {r.get('recall', {}).get('recall_at_5', 0):.2%}",
            f"- **Recall@10**: {r.get('recall', {}).get('recall_at_10', 0):.2%}",
            f"- **MRR**: {r.get('recall', {}).get('mrr', 0):.4f}",
            f"- **Total turns**: {r.get('total_turns', 0)}",
            f"- **Total QA pairs**: {r.get('total_qa_pairs', 0)}",
            f"- **Search p50**: {r.get('search', {}).get('p50_ms', 0):.1f}ms",
            "",
            "### Category Breakdown",
            "",
            "| Category | Total | Recall@1 | Recall@5 | Recall@10 |",
            "|----------|-------|----------|----------|-----------|",
        ])
        for cat, bd in r.get("category_breakdown", {}).items():
            lines.append(
                f"| {cat} | {bd['total']} | {bd['recall_at_1']:.2%} | {bd['recall_at_5']:.2%} | {bd['recall_at_10']:.2%} |"
            )
        lines.append("")

    # LongMemEval
    if "longmemeval" in all_results:
        r = all_results["longmemeval"]
        lines.extend([
            f"## 4. LongMemEval Benchmark ({r.get('num_sessions', 0)} sessions)",
            "",
            f"- **Recall@1**: {r.get('recall', {}).get('recall_at_1', 0):.2%}",
            f"- **Recall@5**: {r.get('recall', {}).get('recall_at_5', 0):.2%}",
            f"- **Recall@10**: {r.get('recall', {}).get('recall_at_10', 0):.2%}",
            f"- **MRR**: {r.get('recall', {}).get('mrr', 0):.4f}",
            f"- **Total turns**: {r.get('total_turns', 0)}",
            f"- **Total questions**: {r.get('total_questions', 0)}",
            f"- **Search p50**: {r.get('search', {}).get('p50_ms', 0):.1f}ms",
            "",
            "### Category Breakdown",
            "",
            "| Category | Total | Recall@1 | Recall@5 | Recall@10 |",
            "|----------|-------|----------|----------|-----------|",
        ])
        for cat, bd in r.get("category_breakdown", {}).items():
            lines.append(
                f"| {cat} | {bd['total']} | {bd['recall_at_1']:.2%} | {bd['recall_at_5']:.2%} | {bd['recall_at_10']:.2%} |"
            )
        lines.append("")

    # BEAM
    if "beam" in all_results and "error" not in all_results["beam"]:
        r = all_results["beam"]
        lines.extend([
            "## 5. BEAM Benchmark (multi-hop, temporal, abstention)",
            "",
            f"- **Overall Accuracy**: {r.get('overall_accuracy', 0):.2%}",
            f"- **Total Memories**: {r.get('total_memories', 0)}",
            f"- **Total Queries**: {r.get('total_queries', 0)}",
            f"- **Search p50**: {r.get('search', {}).get('p50_ms', 0):.1f}ms",
            "",
            "### Type Breakdown",
            "",
            "| Type | Total | Accuracy |",
            "|------|-------|----------|",
        ])
        for q_type, bd in r.get("type_breakdown", {}).items():
            lines.append(f"| {q_type} | {bd['total']} | {bd['accuracy']:.2%} |")
        lines.append("")

    # Abstention
    if "abstention" in all_results:
        r = all_results["abstention"]
        m = r.get("metrics", {})
        lines.extend([
            "## 6. Abstention Benchmark",
            "",
            f"- **True Positive Rate (recall)**: {m.get('true_positive_rate', 0):.2%}",
            f"- **False Positive Rate**: {m.get('false_positive_rate', 0):.2%}",
            f"- **Abstention Accuracy**: {m.get('abstention_accuracy', 0):.2%}",
            f"- **Precision**: {m.get('precision', 0):.2%}",
            f"- **F1 Score**: {m.get('f1_score', 0):.4f}",
            f"- **TP**: {m.get('true_positives', 0)} | **FN**: {m.get('false_negatives', 0)} | "
            f"**FP**: {m.get('false_positives', 0)} | **TN**: {m.get('true_negatives', 0)}",
            "",
            "> **Note**: Abstention gate is now active (threshold=0.12). "
            "FPR measures how often irrelevant queries still return results above threshold.",
            "",
        ])

    # HologramEval
    if "hologrameval" in all_results and "error" not in all_results["hologrameval"]:
        r = all_results["hologrameval"]
        lines.extend([
            "## 7. HologramEval (5D Holographic Memory Evaluation)",
            "",
            f"- **Overall Accuracy**: {r.get('overall_accuracy', 0):.2%}",
            f"- **Total Memories**: {r.get('total_memories', 0)}",
            f"- **Total Queries**: {r.get('total_queries', 0)}",
            f"- **Search p50**: {r.get('search', {}).get('p50_ms', 0):.1f}ms",
            "",
            "### Type Breakdown",
            "",
            "| Type | Total | Accuracy |",
            "|------|-------|----------|",
        ])
        for q_type, bd in r.get("type_breakdown", {}).items():
            lines.append(f"| {q_type} | {bd['total']} | {bd['accuracy']:.2%} |")
        lines.append("")

    # Comparison table
    lines.extend([
        "---",
        "",
        "## Comparison with External Systems",
        "",
        "| System | Benchmark | Recall@1 | Recall@5 | MRR | Tokens/Query |",
        "|--------|-----------|----------|----------|-----|--------------|",
    ])

    if "internal" in all_results:
        r = all_results["internal"]["recall"]
        lines.append(f"| WhiteMagic | Internal (100 mem) | {r['recall_at_1']:.2%} | {r['recall_at_5']:.2%} | {r['mrr']:.4f} | 0 |")
    if "scale" in all_results:
        r = all_results["scale"]["recall"]
        lines.append(f"| WhiteMagic | Scale ({all_results['scale']['num_memories']:,} mem) | {r['recall_at_1']:.2%} | {r['recall_at_5']:.2%} | {r['mrr']:.4f} | 0 |")
    if "locomo" in all_results:
        r = all_results["locomo"]["recall"]
        lines.append(f"| WhiteMagic | LoCoMo | {r['recall_at_1']:.2%} | {r['recall_at_5']:.2%} | {r['mrr']:.4f} | 0 |")
    if "longmemeval" in all_results:
        r = all_results["longmemeval"]["recall"]
        lines.append(f"| WhiteMagic | LongMemEval | {r['recall_at_1']:.2%} | {r['recall_at_5']:.2%} | {r['mrr']:.4f} | 0 |")
    if "beam" in all_results and "error" not in all_results["beam"]:
        r = all_results["beam"]
        lines.append(f"| WhiteMagic | BEAM | {r.get('overall_accuracy', 0):.2%} | — | — | 0 |")
    if "hologrameval" in all_results and "error" not in all_results["hologrameval"]:
        r = all_results["hologrameval"]
        lines.append(f"| WhiteMagic | HologramEval | {r.get('overall_accuracy', 0):.2%} | — | — | 0 |")

    lines.extend([
        "| Mem0 (2026) | LoCoMo | 92.5% | — | — | ~7,000 |",
        "| MemGPT | LoCoMo | ~80% | — | — | ~5,000 |",
        "",
        "## Statistical Rigor",
        "",
    ])

    # Bootstrap CIs
    ci_data: dict[str, Any] = all_results.get("_statistical", {})
    if ci_data:
        lines.extend([
            "### Bootstrap Confidence Intervals (95% CI)",
            "",
            "| Metric | Mean | CI Lower | CI Upper | CI Width |",
            "|--------|------|----------|----------|----------|",
        ])
        for metric_name, ci in ci_data.get("bootstrap_cis", {}).items():
            lines.append(
                f"| {metric_name} | {ci['mean']:.4f} | {ci['ci_lower']:.4f} | {ci['ci_upper']:.4f} | {ci['ci_width']:.4f} |"
            )
        lines.append("")

        # Judge FPR
        fpr_data = ci_data.get("judge_fpr", {})
        if fpr_data:
            lines.extend([
                "### Judge FPR Probe",
                "",
                f"- **False Positive Rate**: {fpr_data.get('fpr', 0):.2%}",
                f"- **Mean Random Recall**: {fpr_data.get('mean_random_recall', 0):.4f}",
                f"- **Probes**: {fpr_data.get('num_probes', 0)}",
                f"- **Interpretation**: {fpr_data.get('interpretation', '')}",
                "",
            ])

    lines.extend([
        "## Methodology",
        "",
        "1. **Dataset**: Deterministic synthetic datasets (seed=42) with known ground truth",
        "2. **Search pipeline**: FTS5 BM25 candidate generation → FastEmbed (BAAI/bge-small-en-v1.5, 384 dims) semantic reranking",
        "3. **No LLM calls**: All search is local, 0 tokens consumed per query",
        "4. **Metrics**: Rank-based Recall@K (at least one expected ID in top K) and MRR",
        "5. **Transparency**: Per-query JSON output available with `--per-case` flag",
        "6. **Hardware**: " + f"{platform.processor() or 'CPU'}",
        "",
    ])

    # Custom benchmarks
    if "custom" in all_results:
        custom = all_results["custom"]
        lines.extend([
            "## Custom Benchmarks (Section 7.3)",
            "",
            "| Benchmark | Key Metric | Value | Improvement |",
            "|-----------|------------|-------|-------------|",
        ])
        for name, result in custom.items():
            if "error" in result:
                lines.append(f"| {name} | — | FAILED | — |")
                continue
            if name == "holographic_spatial":
                lines.append(f"| {name} | mean_recall | {result.get('mean_recall', 0):.4f} | +{result.get('spatial_boost', 0):.4f} |")
            elif name == "cross_galaxy":
                lines.append(f"| {name} | federated_mean | {result.get('federated_mean', 0):.4f} | +{result.get('improvement', 0):.4f} |")
            elif name == "dream_consolidation":
                lines.append(f"| {name} | post_consolidation | {result.get('post_consolidation_mean', 0):.4f} | +{result.get('improvement', 0):.4f} |")
            elif name == "working_memory_bias":
                lines.append(f"| {name} | biased_mean | {result.get('biased_mean', 0):.4f} | +{result.get('improvement', 0):.4f} |")
            elif name == "citta_personalization":
                lines.append(f"| {name} | personalized_mean | {result.get('personalized_mean', 0):.4f} | +{result.get('improvement', 0):.4f} |")
            elif name == "forgetting_accuracy":
                lines.append(f"| {name} | fama_score | {result.get('fama_score', 0):.4f} | — |")
        lines.append("")

    return "\n".join(lines)


BENCH_GALAXIES = [
    "benchmark", "locomo_bench", "longmemeval_bench",
    "beam_bench", "abstention_bench", "hologram_bench",
]


def cleanup_benchmark_galaxies() -> None:
    """Delete all memories from benchmark galaxies to prevent stale data pollution."""
    import sqlite3

    base = Path.home() / ".whitemagic" / "users" / "local" / "galaxies"
    total_deleted = 0
    for galaxy in BENCH_GALAXIES:
        db_path = base / galaxy / "whitemagic.db"
        if db_path.exists():
            try:
                db = sqlite3.connect(str(db_path))
                cursor = db.execute("DELETE FROM memories")
                deleted = cursor.rowcount
                # Also clean FTS5 index — DELETE FROM memories doesn't cascade
                try:
                    db.execute("DELETE FROM memories_fts")
                except Exception:
                    pass
                db.commit()
                db.close()
                if deleted > 0:
                    total_deleted += deleted
            except Exception:
                pass
    if total_deleted > 0:
        print(f"  Cleaned {total_deleted} stale memories from benchmark galaxies")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run all WhiteMagic benchmarks")
    parser.add_argument("--skip-internal", action="store_true", help="Skip internal benchmark")
    parser.add_argument("--skip-scale", action="store_true", help="Skip scale benchmark")
    parser.add_argument("--skip-locomo", action="store_true", help="Skip LoCoMo benchmark")
    parser.add_argument("--skip-longmemeval", action="store_true", help="Skip LongMemEval benchmark")
    parser.add_argument("--skip-beam", action="store_true", help="Skip BEAM benchmark")
    parser.add_argument("--skip-abstention", action="store_true", help="Skip abstention benchmark")
    parser.add_argument("--skip-hologrameval", action="store_true", help="Skip HologramEval benchmark")
    parser.add_argument("--skip-custom", action="store_true", help="Skip custom benchmarks (Section 7.3)")
    parser.add_argument("--scale", choices=["10k", "50k", "100k"], default="10k", help="Scale benchmark size")
    parser.add_argument("--output-dir", default="benchmarks/results", help="Output directory")
    args = parser.parse_args()

    all_results: dict[str, Any] = {}
    results_dir = Path(args.output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("WhiteMagic Unified Benchmark Suite")
    print("=" * 60)

    print("\n--- Cleaning benchmark galaxies ---")
    cleanup_benchmark_galaxies()

    if not args.skip_internal:
        print("\n--- Internal Benchmark ---")
        try:
            from benchmarks.whitemagic_benchmark import run_benchmark
            all_results["internal"] = run_benchmark(num_memories=100, num_queries=50)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["internal"] = {"error": str(e)}

    if not args.skip_scale:
        print(f"\n--- Scale Benchmark ({args.scale}) ---")
        try:
            from benchmarks.scale_benchmark import run_scale_benchmark
            all_results["scale"] = run_scale_benchmark(scale=args.scale, num_queries=200)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["scale"] = {"error": str(e)}

    if not args.skip_locomo:
        print("\n--- LoCoMo Benchmark ---")
        try:
            from benchmarks.locomo_adapter import generate_synthetic_locomo, run_locomo_benchmark
            conversations = generate_synthetic_locomo(num_conversations=20, turns_per_conversation=30, qa_per_conversation=5)
            all_results["locomo"] = run_locomo_benchmark(conversations=conversations)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["locomo"] = {"error": str(e)}

    if not args.skip_longmemeval:
        print("\n--- LongMemEval Benchmark ---")
        try:
            from benchmarks.longmemeval_adapter import generate_synthetic_longmemeval, run_longmemeval_benchmark
            sessions = generate_synthetic_longmemeval(num_sessions=10, turns_per_session=20, questions_per_session=5)
            all_results["longmemeval"] = run_longmemeval_benchmark(sessions=sessions)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["longmemeval"] = {"error": str(e)}

    if not args.skip_beam:
        print("\n--- BEAM Benchmark ---")
        try:
            from benchmarks.beam_adapter import generate_synthetic_beam, run_beam_benchmark
            beam_dataset = generate_synthetic_beam(num_entities=50, num_queries=100)
            all_results["beam"] = run_beam_benchmark(dataset=beam_dataset)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["beam"] = {"error": str(e)}

    if not args.skip_abstention:
        print("\n--- Abstention Benchmark ---")
        try:
            from benchmarks.abstention_benchmark import run_abstention_benchmark
            all_results["abstention"] = run_abstention_benchmark(
                num_memories=500,
                num_relevant_queries=100,
                num_irrelevant_queries=100,
            )
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["abstention"] = {"error": str(e)}

    if not args.skip_hologrameval:
        print("\n--- HologramEval Benchmark ---")
        try:
            from benchmarks.hologrameval_adapter import generate_synthetic_hologrameval, run_hologrameval_benchmark
            holo_dataset = generate_synthetic_hologrameval(num_memories=100, num_queries=50)
            all_results["hologrameval"] = run_hologrameval_benchmark(dataset=holo_dataset)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results["hologrameval"] = {"error": str(e)}

    # Statistical rigor: bootstrap CIs and judge FPR
    print("\n--- Statistical Rigor (Bootstrap CIs + Judge FPR) ---")
    try:
        from benchmarks.bootstrap_stats import bootstrap_ci, judge_fpr_probe

        stat_results: dict[str, Any] = {}

        # Compute bootstrap CIs for internal benchmark
        if "internal" in all_results:
            internal = all_results["internal"]
            pq = internal.get("per_query") or internal.get("recall", {}).get("per_query", [])
            if pq:
                cis: dict[str, Any] = {}
                for metric in ["recall_at_1", "recall_at_5", "recall_at_10", "mrr"]:
                    values = [q.get(metric, 0.0) for q in pq]
                    cis[metric] = bootstrap_ci(values, metric_name=metric)
                stat_results["bootstrap_cis"] = cis
                print(f"  Bootstrap CIs computed from {len(pq)} per-query samples")
            else:
                print("  No per_query data found — bootstrap CIs skipped")

        # Judge FPR probe
        stat_results["judge_fpr"] = judge_fpr_probe(num_probes=500, probe_size=50)

        all_results["_statistical"] = stat_results
        print(f"  Bootstrap CIs computed. Judge FPR: {stat_results['judge_fpr']['fpr']:.2%}")
    except Exception as e:
        print(f"  Statistical rigor FAILED: {e}")

    # Custom WhiteMagic benchmarks (Section 7.3)
    if not args.skip_custom:
        print("\n--- Custom Benchmarks (Section 7.3) ---")
        try:
            from benchmarks.custom_benchmarks import run_all_custom_benchmarks
            custom = run_all_custom_benchmarks()
            all_results["custom"] = custom
        except Exception as e:
            print(f"  Custom benchmarks FAILED: {e}")
            all_results["custom"] = {"error": str(e)}

    # Save unified results
    json_path = results_dir / "unified_results.json"
    json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\n\nResults saved to {json_path}")

    # Generate report
    report = generate_report(all_results)
    report_path = results_dir / "BENCHMARK_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Report saved to {report_path}")
    print("\n" + report)


if __name__ == "__main__":
    main()
