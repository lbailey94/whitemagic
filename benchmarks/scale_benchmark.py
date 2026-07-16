"""Scale benchmark — tests search quality and latency at 10K/50K/100K memories.

Generates synthetic memories across multiple galaxies with known semantic
relationships, then measures:
  - Add throughput (ops/sec, p50/p95/p99 latency)
  - Search latency (p50/p95/p99)
  - Recall@1/5/10 and MRR
  - Per-query JSON output for full transparency

Zero LLM tokens consumed — all search via FTS5 + FastEmbed embeddings.

Usage:
    python benchmarks/scale_benchmark.py --scale 10k
    python benchmarks/scale_benchmark.py --scale 50k --output benchmarks/results/scale_50k.json
    python benchmarks/scale_benchmark.py --scale 100k --per-case
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCALE_MAP = {
    "10k": 10_000,
    "50k": 50_000,
    "100k": 100_000,
}

GALAXIES = [
    "codex", "research", "knowledge", "journals",
    "sessions", "universal", "citta", "aria",
]

# Rich subject pool — 200 subjects across 20 categories
CATEGORIES = [
    "programming", "science", "history", "literature", "philosophy",
    "mathematics", "biology", "chemistry", "physics", "geography",
    "art", "music", "cooking", "sports", "technology",
    "business", "psychology", "medicine", "law", "education",
]

SUBJECTS = [
    "quantum entanglement", "neural networks", "game theory", "entropy",
    "recursion", "metamorphosis", "photosynthesis", "dialectics",
    "topology", "algorithmic complexity", "cellular automata",
    "epigenetics", "cognitive dissonance", "supply and demand",
    "plate tectonics", "the social contract", "wave-particle duality",
    "organic synthesis", "statistical inference", "machine learning",
    "distributed systems", "graph theory", "cryptographic hashing",
    "natural selection", "cultural diffusion", "imperialism",
    "the Renaissance", "boolean algebra", "compiler design",
    "microbiome diversity", "climate feedback loops",
    "quantum computing", "CRISPR gene editing", "blockchain consensus",
    "edge computing", "federated learning", "transfer learning",
    "reinforcement learning", "attention mechanisms", "transformer architecture",
    "gradient descent", "backpropagation", "convolutional networks",
    "generative adversarial networks", "variational autoencoders",
    "word embeddings", "sentiment analysis", "named entity recognition",
    "machine translation", "speech recognition", "computer vision",
    "object detection", "semantic segmentation", "instance segmentation",
    "robotics", "autonomous vehicles", "swarm intelligence",
    "evolutionary algorithms", "genetic programming", "neuroevolution",
    "fluid dynamics", "thermodynamics", "electromagnetism",
    "special relativity", "general relativity", "string theory",
    "dark matter", "dark energy", "exoplanet detection",
    "stellar nucleosynthesis", "black hole thermodynamics",
    "carbon capture", "renewable energy", "battery technology",
    "nuclear fusion", "smart grids", "energy storage",
    "bioremediation", "synthetic biology", "biomimicry",
    "neuroplasticity", "consciousness studies", "dream analysis",
    "memory consolidation", "hippocampal replay", "cortical columns",
    "mirror neurons", "emotional regulation", "trauma therapy",
    "cognitive behavioral therapy", "mindfulness meditation",
    "stoic philosophy", "existentialism", "phenomenology",
    "pragmatism", "empiricism", "rationalism",
    "virtue ethics", "utilitarianism", "deontology",
    "social contract theory", "democratic theory", "power dynamics",
    "game theory strategies", "Nash equilibrium", "Pareto optimality",
    "market failures", "behavioral economics", "neuroeconomics",
    "supply chain optimization", "portfolio theory", "risk assessment",
    "cryptocurrency", "monetary policy", "fiscal policy",
    "trade agreements", "economic development", "poverty traps",
    "social mobility", "education policy", "healthcare economics",
    "epidemiology", "vaccine development", "drug discovery",
    "personalized medicine", "gene therapy", "stem cell research",
    "aging research", "cancer immunotherapy", "tumor suppressors",
    "oncogenes", "apoptosis", "autophagy",
    "circadian rhythms", "gut-brain axis", "microbiome therapy",
    "plant communication", "fungal networks", "coral reef ecology",
    "biodiversity hotspots", "conservation genetics", "rewilding",
    "permaculture", "regenerative agriculture", "vertical farming",
    "hydroponics", "aquaponics", "precision agriculture",
]

DETAILS = [
    "complex interactions between multiple variables",
    "emergent properties from simple rules",
    "trade-offs between efficiency and accuracy",
    "historical context shaping modern understanding",
    "practical applications in industry",
    "theoretical frameworks for future research",
    "interdisciplinary connections",
    "computational challenges at scale",
    "empirical evidence from controlled studies",
    "mathematical foundations and proofs",
    "open questions remaining in the field",
    "recent breakthroughs challenging prior assumptions",
    "methodological limitations of current approaches",
    "ethical implications for society",
    "environmental impact considerations",
]

TEMPLATES = [
    "{subject} is a fundamental concept in {category}.",
    "The key principle of {subject} involves {detail}.",
    "Research on {subject} has shown {detail}.",
    "In {category}, {subject} refers to {detail}.",
    "Understanding {subject} requires knowledge of {detail}.",
    "{subject} emerged from {category} in the early studies.",
    "The application of {subject} in {category} demonstrates {detail}.",
    "Historical analysis of {subject} reveals {detail}.",
    "{subject} plays a crucial role in {category}.",
    "Recent advances in {subject} include {detail}.",
    "A comprehensive review of {subject} highlights {detail}.",
    "The theoretical basis of {subject} rests on {detail}.",
    "Practical implementation of {subject} faces {detail}.",
    "Critics of {subject} argue that {detail}.",
    "The future of {subject} depends on {detail}.",
]


def generate_scale_dataset(
    num_memories: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate a deterministic large-scale dataset.

    Returns list of dicts with: id, content, category, tags, subject, galaxy.
    """
    rng = random.Random(seed)
    memories = []

    for i in range(num_memories):
        cat = rng.choice(CATEGORIES)
        subj = rng.choice(SUBJECTS)
        detail = rng.choice(DETAILS)
        template = rng.choice(TEMPLATES)
        galaxy = rng.choice(GALAXIES)

        content = template.format(subject=subj, category=cat, detail=detail)
        tags = [cat, subj.split()[0]]

        memories.append({
            "id": f"mem_{i:06d}",
            "content": content,
            "category": cat,
            "tags": tags,
            "subject": subj,
            "galaxy": galaxy,
        })

    return memories


def generate_scale_queries(
    num_queries: int = 200,
    seed: int = 43,
    dataset_seed: int = 42,
    num_memories: int = 10_000,
) -> list[dict[str, Any]]:
    """Generate test queries with known ground truth.

    Returns list of dicts with: id, query, expected_ids, expected_subject.
    """
    rng = random.Random(seed)
    dataset = generate_scale_dataset(num_memories=num_memories, seed=dataset_seed)

    # Build subject → memory IDs index
    subject_to_ids: dict[str, list[str]] = {}
    cat_to_ids: dict[str, list[str]] = {}
    for m in dataset:
        subject_to_ids.setdefault(m["subject"], []).append(m["id"])
        cat_to_ids.setdefault(m["category"], []).append(m["id"])

    query_templates = [
        ("Tell me about {subject}", "subject"),
        ("What is {subject}?", "subject"),
        ("Explain {subject}", "subject"),
        ("Research on {subject}", "subject"),
        ("{subject} in {category}", "subject"),
        ("{category} concepts about {subject}", "subject"),
        ("Recent advances in {subject}", "subject"),
        ("The theoretical basis of {subject}", "subject"),
        ("{category} fundamentals", "category"),
        ("Key principles in {category}", "category"),
    ]

    queries = []
    used_subjects: set[str] = set()

    for i in range(num_queries):
        template, match_key = rng.choice(query_templates)
        subj = rng.choice(SUBJECTS)
        cat = rng.choice(CATEGORIES)

        if match_key == "subject":
            # Ensure subject has at least 1 memory
            if subj not in subject_to_ids:
                continue
            query = template.format(subject=subj, category=cat)
            expected = subject_to_ids[subj][:20]
            expected_subject = subj
        else:
            if cat not in cat_to_ids:
                continue
            query = template.format(category=cat, subject=subj)
            expected = cat_to_ids[cat][:20]
            expected_subject = cat

        queries.append({
            "id": f"q_{i:04d}",
            "query": query,
            "expected_ids": expected,
            "expected_subject": expected_subject,
        })

    return queries


def _call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    """Call a WhiteMagic tool."""
    from whitemagic.tools.unified_api import call_tool
    return call_tool(name, **kwargs)


def run_scale_benchmark(
    scale: str = "10k",
    num_queries: int = 200,
    per_case: bool = False,
) -> dict[str, Any]:
    """Run scale benchmark.

    Args:
        scale: "10k", "50k", or "100k"
        num_queries: Number of test queries
        per_case: If True, include per-query results in output

    Returns:
        Results dict with add stats, search stats, recall stats.
    """
    num_memories = SCALE_MAP.get(scale, 10_000)
    print(f"\n{'=' * 60}")
    print(f"Scale Benchmark: {scale} ({num_memories:,} memories)")
    print(f"{'=' * 60}")

    # Generate dataset
    print(f"\nGenerating {num_memories:,} memories...")
    t0 = time.perf_counter()
    memories = generate_scale_dataset(num_memories=num_memories)
    print(f"  Generated in {time.perf_counter() - t0:.2f}s")

    print(f"Generating {num_queries} queries...")
    queries = generate_scale_queries(
        num_queries=num_queries,
        num_memories=num_memories,
    )
    print(f"  {len(queries)} queries with ground truth")

    # Ensure benchmark galaxy exists
    galaxy = "benchmark"
    try:
        _call_tool("galaxy.create", name=galaxy)
    except Exception:
        pass

    # Phase 1: Add memories (batch with progress)
    print(f"\nAdding {num_memories:,} memories to galaxy '{galaxy}'...")
    add_latencies: list[float] = []
    id_map: dict[str, str] = {}
    batch_size = 500
    t_start = time.perf_counter()

    for batch_start in range(0, len(memories), batch_size):
        batch = memories[batch_start:batch_start + batch_size]
        for mem in batch:
            t0 = time.perf_counter()
            result = _call_tool(
                "create_memory",
                title=mem["id"],
                content=mem["content"],
                galaxy=galaxy,
                tags=mem["tags"],
            )
            lat = (time.perf_counter() - t0) * 1000
            add_latencies.append(lat)

            actual_id = None
            if isinstance(result, dict):
                actual_id = result.get("memory_id") or result.get("details", {}).get("memory_id")
            if actual_id:
                id_map[mem["id"]] = actual_id

        elapsed = time.perf_counter() - t_start
        done = min(batch_start + batch_size, num_memories)
        rate = done / elapsed if elapsed > 0 else 0
        print(f"  {done:,}/{num_memories:,} ({rate:.0f} ops/sec, {elapsed:.1f}s)")

    add_latencies.sort()
    add_stats = {
        "count": len(add_latencies),
        "total_s": time.perf_counter() - t_start,
        "p50_ms": add_latencies[len(add_latencies) // 2],
        "p95_ms": add_latencies[int(len(add_latencies) * 0.95)],
        "p99_ms": add_latencies[int(len(add_latencies) * 0.99)],
        "throughput_ops_sec": len(add_latencies) / (sum(add_latencies) / 1000) if sum(add_latencies) > 0 else 0,
        "ids_mapped": len(id_map),
    }
    print(f"\nAdd complete: {add_stats['count']:,} memories in {add_stats['total_s']:.1f}s "
          f"({add_stats['throughput_ops_sec']:.0f} ops/sec)")
    print(f"  p50={add_stats['p50_ms']:.1f}ms  p95={add_stats['p95_ms']:.1f}ms  p99={add_stats['p99_ms']:.1f}ms")

    # Phase 2: Search latency benchmark
    print(f"\nBenchmarking search latency ({len(queries)} queries)...")
    search_latencies: list[float] = []
    for q in queries:
        t0 = time.perf_counter()
        _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=10,
        )
        search_latencies.append((time.perf_counter() - t0) * 1000)

    search_latencies.sort()
    search_stats = {
        "count": len(search_latencies),
        "total_ms": sum(search_latencies),
        "p50_ms": search_latencies[len(search_latencies) // 2],
        "p95_ms": search_latencies[int(len(search_latencies) * 0.95)],
        "p99_ms": search_latencies[int(len(search_latencies) * 0.99)],
        "throughput_ops_sec": len(search_latencies) / (sum(search_latencies) / 1000) if sum(search_latencies) > 0 else 0,
    }
    print(f"  p50={search_stats['p50_ms']:.1f}ms  p95={search_stats['p95_ms']:.1f}ms  p99={search_stats['p99_ms']:.1f}ms")

    # Phase 3: Recall quality
    print(f"\nMeasuring recall quality...")
    recall_at_1 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    mrr_sum = 0.0
    total = 0
    per_query_results: list[dict[str, Any]] = []

    for q in queries:
        expected_ds = set(q.get("expected_ids", []))
        if not expected_ds:
            continue

        expected = {id_map[ds_id] for ds_id in expected_ds if ds_id in id_map}
        if not expected:
            continue

        result = _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=10,
        )

        retrieved_ids: list[str] = []
        if result.get("status") == "success":
            details = result.get("details", {})
            data = details.get("memories", details.get("data", details.get("results", [])))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        rid = item.get("id", item.get("memory_id", ""))
                        retrieved_ids.append(rid)

        match_ranks = [i + 1 for i, rid in enumerate(retrieved_ids) if rid in expected]
        r1 = 1 if any(r <= 1 for r in match_ranks) else 0
        r5 = 1 if any(r <= 5 for r in match_ranks) else 0
        r10 = 1 if match_ranks else 0

        recall_at_1 += r1
        recall_at_5 += r5
        recall_at_10 += r10

        mrr = 0.0
        for rank, rid in enumerate(retrieved_ids, 1):
            if rid in expected:
                mrr = 1.0 / rank
                break
        mrr_sum += mrr

        total += 1

        if per_case:
            per_query_results.append({
                "query_id": q["id"],
                "query": q["query"],
                "expected_subject": q["expected_subject"],
                "expected_count": len(expected),
                "retrieved_count": len(retrieved_ids),
                "recall_at_1": r1,
                "recall_at_5": r5,
                "recall_at_10": r10,
                "mrr": round(mrr, 4),
                "first_match_rank": match_ranks[0] if match_ranks else None,
            })

    recall_stats = {
        "total_queries": total,
        "recall_at_1": recall_at_1 / total if total > 0 else 0,
        "recall_at_5": recall_at_5 / total if total > 0 else 0,
        "recall_at_10": recall_at_10 / total if total > 0 else 0,
        "mrr": mrr_sum / total if total > 0 else 0,
    }

    print(f"  recall@1: {recall_stats['recall_at_1']:.2%}")
    print(f"  recall@5: {recall_stats['recall_at_5']:.2%}")
    print(f"  recall@10: {recall_stats['recall_at_10']:.2%}")
    print(f"  MRR: {recall_stats['mrr']:.4f}")

    # Token usage
    token_stats = {
        "tokens_per_query": 0,
        "llm_calls": 0,
        "search_method": "FTS5 BM25 + FastEmbed semantic reranking",
        "embedding_model": "BAAI/bge-small-en-v1.5 (384 dims)",
    }

    results = {
        "system": "whitemagic",
        "scale": scale,
        "num_memories": num_memories,
        "num_queries": len(queries),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "add": add_stats,
        "search": search_stats,
        "recall": recall_stats,
        "tokens": token_stats,
    }

    if per_case:
        results["per_query"] = per_query_results

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="WhiteMagic scale benchmark")
    parser.add_argument("--scale", choices=list(SCALE_MAP.keys()), default="10k",
                        help="Scale: 10k, 50k, or 100k memories")
    parser.add_argument("--queries", type=int, default=200,
                        help="Number of test queries")
    parser.add_argument("--output", "-o", default=None,
                        help="Output JSON file")
    parser.add_argument("--per-case", action="store_true",
                        help="Include per-query results in output")
    args = parser.parse_args()

    results = run_scale_benchmark(
        scale=args.scale,
        num_queries=args.queries,
        per_case=args.per_case,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {args.output}")
    else:
        # Default output path
        default_path = Path(f"benchmarks/results/scale_{args.scale}.json")
        default_path.parent.mkdir(parents=True, exist_ok=True)
        default_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {default_path}")


if __name__ == "__main__":
    main()
