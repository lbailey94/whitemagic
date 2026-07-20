"""Abstention benchmark — measures precision and false positive rate.

Tests whether WhiteMagic can correctly identify when NO relevant memory
exists, rather than always returning the closest match regardless of
relevance. This is the "abstention detection" gap (Gap D).

Metrics:
  - True Positive Rate (TPR): relevant query → results returned
  - False Positive Rate (FPR): irrelevant query → results returned
  - Abstention Accuracy: correct abstention on irrelevant queries
  - F1 Score: harmonic mean of precision and recall
  - Per-query confidence scores (if available)

Usage:
    python benchmarks/abstention_benchmark.py --memories 500 --queries 200
    python benchmarks/abstention_benchmark.py --output benchmarks/results/abstention.json --per-case
"""

from __future__ import annotations

import json
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

# Domains for relevant memories
MEMORY_DOMAINS = [
    ("programming", ["Python", "Rust", "JavaScript", "compilers", "algorithms", "data structures", "debugging", "refactoring"]),
    ("science", ["quantum mechanics", "evolution", "photosynthesis", "neuroscience", "chemistry", "astronomy"]),
    ("history", ["World War II", "Roman Empire", "Renaissance", "Industrial Revolution", "Cold War"]),
    ("literature", ["Shakespeare", "magical realism", "stream of consciousness", "postmodernism"]),
    ("cooking", ["French cuisine", "sourdough baking", "fermentation", "knife skills", "stock making"]),
]

# Irrelevant query domains — topics NOT in stored memories
IRRELEVANT_TOPICS = [
    "underwater basket weaving techniques",
    "the mating habits of Mars rovers",
    "how to train a dragon to do taxes",
    "best practices for time travel tourism",
    "the political economy of Narnia",
    "comparative anatomy of unicorns and griffins",
    "recipe for invisible ink soup",
    "the history of telepathic telecommunications",
    "investment strategies for leprechaun gold",
    "sustainable farming on Mercury",
    "the linguistics of dolphin poetry",
    "advanced calculus for houseplants",
    "negotiating peace treaties with AI toasters",
    "the cultural significance of cloud shapes",
    "geological survey of Middle Earth",
    "constitutional law for penguin colonies",
    "the physics of cartoon gravity",
    "ethical implications of sentient furniture",
    "weather forecasting for alternate dimensions",
    "the sociology of imaginary friends",
]


def _call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.unified_api import call_tool
    return call_tool(name, **kwargs)


def generate_abstention_dataset(
    num_memories: int = 500,
    num_relevant_queries: int = 100,
    num_irrelevant_queries: int = 100,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate memories, relevant queries, and irrelevant queries.

    Returns (memories, relevant_queries, irrelevant_queries).
    """
    rng = random.Random(seed)

    # Generate memories from known domains
    memories = []
    for i in range(num_memories):
        domain, topics = rng.choice(MEMORY_DOMAINS)
        topic = rng.choice(topics)
        templates = [
            f"Key concepts in {topic}: fundamental principles and applications.",
            f"Understanding {topic} requires studying its theoretical foundations.",
            f"Recent research on {topic} has revealed new insights.",
            f"The practical application of {topic} in {domain} is well-documented.",
            f"Historical development of {topic} shows significant evolution.",
        ]
        content = rng.choice(templates)
        memories.append({
            "id": f"mem_{i:04d}",
            "content": content,
            "domain": domain,
            "topic": topic,
            "tags": [domain, topic.split()[0].lower()],
        })

    # Generate relevant queries (should match stored memories)
    relevant_queries = []
    for i in range(num_relevant_queries):
        domain, topics = rng.choice(MEMORY_DOMAINS)
        topic = rng.choice(topics)
        query_templates = [
            f"Tell me about {topic}",
            f"What is {topic}?",
            f"Explain {topic} in {domain}",
            f"Research on {topic}",
            f"Key concepts in {topic}",
        ]
        query = rng.choice(query_templates)
        # Expected: memories with same topic
        topic_count = sum(1 for m in memories if m["topic"] == topic)
        relevant_queries.append({
            "id": f"rq_{i:04d}",
            "query": query,
            "relevance_labels": {"topic": topic},
            "relevant_count": topic_count,
            "is_relevant": True,
            "topic": topic,
        })

    # Generate irrelevant queries (should NOT match any stored memory)
    irrelevant_queries = []
    for i in range(num_irrelevant_queries):
        topic = rng.choice(IRRELEVANT_TOPICS)
        query_templates = [
            f"Tell me about {topic}",
            f"What is {topic}?",
            f"Explain {topic}",
            f"Research on {topic}",
            f"How does {topic} work?",
        ]
        query = rng.choice(query_templates)
        iq_id = f"iq_{i:04d}"
        irrelevant_queries.append({
            "id": iq_id,
            "query": query,
            "relevance_labels": {},
            "relevant_count": 0,
            "is_relevant": False,
            "topic": topic,
        })

    return memories, relevant_queries, irrelevant_queries


def run_abstention_benchmark(
    num_memories: int = 500,
    num_relevant_queries: int = 100,
    num_irrelevant_queries: int = 100,
    galaxy: str = "abstention_bench",
    per_case: bool = False,
    abstention_threshold: float = 0.12,
) -> dict[str, Any]:
    """Run abstention benchmark.

    Measures:
    - TPR: % of relevant queries that return results
    - FPR: % of irrelevant queries that return results (should be LOW)
    - Abstension accuracy: % of irrelevant queries correctly abstained
    """
    print(f"\n{'=' * 60}")
    print(f"Abstention Benchmark — {num_memories} memories, "
          f"{num_relevant_queries} relevant + {num_irrelevant_queries} irrelevant queries")
    print(f"  (abstention_threshold={abstention_threshold})")
    print(f"{'=' * 60}")

    memories, rel_queries, irrel_queries = generate_abstention_dataset(
        num_memories=num_memories,
        num_relevant_queries=num_relevant_queries,
        num_irrelevant_queries=num_irrelevant_queries,
    )

    # Ensure galaxy exists
    try:
        _call_tool("galaxy.create", name=galaxy)
    except Exception:
        pass

    # Ingest memories
    print(f"\nIngesting {len(memories)} memories...")
    id_map: dict[str, str] = {}
    for mem in memories:
        result = _call_tool(
            "create_memory",
            title=mem["id"],
            content=mem["content"],
            galaxy=galaxy,
            tags=mem["tags"],
        )
        actual_id = None
        if isinstance(result, dict):
            actual_id = result.get("memory_id") or result.get("details", {}).get("memory_id")
        if actual_id:
            id_map[mem["id"]] = actual_id

    print(f"  {len(id_map)}/{len(memories)} IDs mapped")

    # Evaluate relevant queries
    print(f"\nEvaluating {len(rel_queries)} relevant queries...")
    tp = 0  # True positives: relevant query → results returned
    fn = 0  # False negatives: relevant query → no results
    search_latencies: list[float] = []
    per_query_results: list[dict[str, Any]] = []

    for q in rel_queries:
        t0 = time.perf_counter()
        result = _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=10,
            abstention_threshold=abstention_threshold,
        )
        lat = (time.perf_counter() - t0) * 1000
        search_latencies.append(lat)

        retrieved_ids: list[str] = []
        if result.get("status") == "success":
            details = result.get("details", {})
            data = details.get("memories", details.get("data", details.get("results", [])))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        rid = item.get("id", item.get("memory_id", ""))
                        retrieved_ids.append(rid)

        has_results = len(retrieved_ids) > 0
        if has_results:
            tp += 1
        else:
            fn += 1

        if per_case:
            per_query_results.append({
                "query_id": q["id"],
                "query": q["query"],
                "is_relevant": True,
                "has_results": has_results,
                "result_count": len(retrieved_ids),
                "latency_ms": round(lat, 2),
            })

    # Evaluate irrelevant queries
    print(f"Evaluating {len(irrel_queries)} irrelevant queries...")
    fp = 0  # False positives: irrelevant query → results returned
    tn = 0  # True negatives: irrelevant query → no results

    for q in irrel_queries:
        t0 = time.perf_counter()
        result = _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=10,
            abstention_threshold=abstention_threshold,
        )
        lat = (time.perf_counter() - t0) * 1000
        search_latencies.append(lat)

        retrieved_ids: list[str] = []
        if result.get("status") == "success":
            details = result.get("details", {})
            data = details.get("memories", details.get("data", details.get("results", [])))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        rid = item.get("id", item.get("memory_id", ""))
                        retrieved_ids.append(rid)

        has_results = len(retrieved_ids) > 0
        if has_results:
            fp += 1
        else:
            tn += 1

        if per_case:
            per_query_results.append({
                "query_id": q["id"],
                "query": q["query"],
                "is_relevant": False,
                "has_results": has_results,
                "result_count": len(retrieved_ids),
                "latency_ms": round(lat, 2),
            })

    search_latencies.sort()

    # Compute metrics
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0  # Sensitivity / Recall
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0  # False positive rate
    abstention_accuracy = tn / (fp + tn) if (fp + tn) > 0 else 0  # Specificity
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * precision * tpr / (precision + tpr) if (precision + tpr) > 0 else 0

    results = {
        "system": "whitemagic",
        "benchmark": "abstention",
        "num_memories": num_memories,
        "num_relevant_queries": len(rel_queries),
        "num_irrelevant_queries": len(irrel_queries),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metrics": {
            "true_positive_rate": round(tpr, 4),
            "false_positive_rate": round(fpr, 4),
            "abstention_accuracy": round(abstention_accuracy, 4),
            "precision": round(precision, 4),
            "f1_score": round(f1, 4),
            "true_positives": tp,
            "false_negatives": fn,
            "false_positives": fp,
            "true_negatives": tn,
        },
        "search": {
            "count": len(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2],
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)],
            "p99_ms": search_latencies[int(len(search_latencies) * 0.99)],
        },
        "tokens": {
            "tokens_per_query": 0,
            "llm_calls": 0,
        },
        "note": (
            "FPR measures how often the system returns results for completely "
            "irrelevant queries. Lower FPR = better abstention. Currently, "
            "FTS5 will return results for any query with keyword overlap. "
            "A relevance threshold gate (Gap D) is needed to enable proper abstention."
        ),
    }

    if per_case:
        results["per_query"] = per_query_results

    print(f"\nResults:")
    print(f"  TPR (recall): {tpr:.2%} ({tp} TP, {fn} FN)")
    print(f"  FPR (false positive): {fpr:.2%} ({fp} FP, {tn} TN)")
    print(f"  Abstention accuracy: {abstention_accuracy:.2%}")
    print(f"  Precision: {precision:.2%}")
    print(f"  F1: {f1:.4f}")
    print(f"  Search p50: {results['search']['p50_ms']:.1f}ms")

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Abstention benchmark")
    parser.add_argument("--memories", type=int, default=500, help="Number of memories")
    parser.add_argument("--relevant-queries", type=int, default=100, help="Number of relevant queries")
    parser.add_argument("--irrelevant-queries", type=int, default=100, help="Number of irrelevant queries")
    parser.add_argument("--galaxy", default="abstention_bench", help="Galaxy to use")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    results = run_abstention_benchmark(
        num_memories=args.memories,
        num_relevant_queries=args.relevant_queries,
        num_irrelevant_queries=args.irrelevant_queries,
        galaxy=args.galaxy,
        per_case=args.per_case,
    )

    output_path = args.output or "benchmarks/results/abstention.json"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
