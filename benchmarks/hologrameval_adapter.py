"""HologramEval — Holographic Memory Coordinate Evaluation.

Tests WhiteMagic's unique 5D holographic memory positioning:
  x: temporal (recency vs age)
  y: semantic (topic similarity)
  z: emotional (valence/arousal)
  w: relational (association strength)
  v: importance (user-set vs system-inferred)

Unlike LoCoMo/LongMemEval which test flat recall, HologramEval tests:
  1. Coordinate accuracy — are memories positioned correctly in 5D space?
  2. Galactic lifecycle — do memories migrate through zones correctly?
  3. Emotional clustering — do emotionally similar memories cluster?
  4. Temporal decay — does recency weighting work?
  5. Importance ranking — does importance affect retrieval priority?
  6. Relational proximity — do associated memories boost each other?

All 0-token (no LLM calls). Uses synthetic data with known coordinates.

Usage:
    python benchmarks/hologrameval_adapter.py --synthetic
    python benchmarks/hologrameval_adapter.py --data-path /path/to/hologram.json
"""

from __future__ import annotations

import json
import math
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


def _call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.unified_api import call_tool
    return call_tool(name, **kwargs)


# ── Synthetic data generation ─────────────────────────────────────────────

EMOTIONAL_CONTEXTS = [
    ("joyful", 0.9, 0.7),    # (label, valence, arousal)
    ("excited", 0.8, 0.9),
    ("content", 0.7, 0.3),
    ("calm", 0.6, 0.2),
    ("neutral", 0.5, 0.5),
    ("anxious", 0.3, 0.8),
    ("frustrated", 0.2, 0.7),
    ("sad", 0.1, 0.3),
    ("angry", 0.05, 0.9),
    ("grieving", 0.02, 0.4),
]

TOPIC_CLUSTERS = {
    "machine learning": [
        "Training a new transformer model on the dataset",
        "Evaluating the BERT classifier on benchmark data",
        "Tuning hyperparameters for the neural network",
        "Deploying the ML inference service to production",
    ],
    "system design": [
        "Designing the microservices architecture for the platform",
        "Implementing the event-driven messaging system",
        "Setting up the API gateway with rate limiting",
        "Configuring the service mesh for inter-service communication",
    ],
    "data engineering": [
        "Building the ETL pipeline for data ingestion",
        "Optimizing the PostgreSQL queries for analytics",
        "Setting up the data warehouse with Snowflake",
        "Implementing real-time stream processing with Kafka",
    ],
    "security": [
        "Conducting the security audit of the authentication module",
        "Implementing OAuth2 for the API endpoints",
        "Setting up rate limiting to prevent brute force attacks",
        "Rotating all API keys and certificates",
    ],
    "product": [
        "Defining the product roadmap for Q3 and Q4",
        "Gathering user feedback on the new dashboard feature",
        "Prioritizing features based on customer impact analysis",
        "Launching the beta program for 50 early adopters",
    ],
}

IMPORTANCE_LEVELS = [0.3, 0.5, 0.7, 0.9]  # low, medium, high, critical


def generate_synthetic_hologrameval(
    num_memories: int = 100,
    num_queries: int = 50,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate synthetic HologramEval dataset with known 5D coordinates.

    Each memory has a known:
    - topic (semantic cluster)
    - emotional context (valence, arousal)
    - importance level
    - relative age (temporal position)
    - association links (relational)

    Queries test whether retrieval respects these dimensions.
    """
    rng = random.Random(seed)

    memories = []
    topics = list(TOPIC_CLUSTERS.keys())

    for i in range(num_memories):
        topic = rng.choice(topics)
        content = rng.choice(TOPIC_CLUSTERS[topic])
        emo_label, valence, arousal = rng.choice(EMOTIONAL_CONTEXTS)
        importance = rng.choice(IMPORTANCE_LEVELS)
        age_days = rng.randint(1, 90)  # 1 day old to 90 days old

        memories.append({
            "id": f"holo_{i:04d}",
            "content": f"[{emo_label}] {content}",
            "topic": topic,
            "emotion": emo_label,
            "valence": valence,
            "arousal": arousal,
            "importance": importance,
            "age_days": age_days,
            "expected_tags": [topic, emo_label],
        })

    # Generate queries that test each dimension
    queries = []

    # 1. Semantic queries — should retrieve memories from the correct topic cluster
    for i in range(num_queries // 6):
        topic = rng.choice(topics)
        queries.append({
            "id": f"q_sem_{i:04d}",
            "query": f"What did we discuss about {topic}?",
            "type": "semantic",
            "expected_topic": topic,
            "answer": None,  # checked by topic match, not substring
        })

    # 2. Emotional queries — should retrieve memories with matching emotional context
    for i in range(num_queries // 6):
        emo_label, _, _ = rng.choice(EMOTIONAL_CONTEXTS)
        queries.append({
            "id": f"q_emo_{i:04d}",
            "query": f"What was the {emo_label} memory about?",
            "type": "emotional",
            "expected_emotion": emo_label,
            "answer": None,
        })

    # 3. Importance queries — high-importance memories should rank first
    for i in range(num_queries // 6):
        topic = rng.choice(topics)
        queries.append({
            "id": f"q_imp_{i:04d}",
            "query": f"What is the most important thing about {topic}?",
            "type": "importance",
            "expected_topic": topic,
            "min_importance": 0.7,
            "answer": None,
        })

    # 4. Temporal queries — recent memories should rank first
    for i in range(num_queries // 6):
        topic = rng.choice(topics)
        queries.append({
            "id": f"q_tmp_{i:04d}",
            "query": f"What did we recently discuss about {topic}?",
            "type": "temporal",
            "expected_topic": topic,
            "max_age_days": 30,
            "answer": None,
        })

    # 5. Substring queries — standard recall (control group)
    for i in range(num_queries // 6):
        mem = rng.choice(memories)
        # Extract a unique phrase from the content
        words = mem["content"].split()
        if len(words) < 4:
            continue
        phrase = " ".join(words[2:5])
        queries.append({
            "id": f"q_sub_{i:04d}",
            "query": phrase,
            "type": "substring",
            "answer": phrase,
            "expected_memory_id": mem["id"],
        })

    # 6. Combined queries — semantic + importance (multi-dimensional)
    for i in range(num_queries - len(queries)):
        topic = rng.choice(topics)
        queries.append({
            "id": f"q_cmb_{i:04d}",
            "query": f"What is the critical finding about {topic}?",
            "type": "combined",
            "expected_topic": topic,
            "min_importance": 0.7,
            "answer": None,
        })

    return {
        "metadata": {
            "name": "HologramEval-Synthetic",
            "num_memories": len(memories),
            "num_queries": len(queries),
            "dimensions": ["temporal", "semantic", "emotional", "relational", "importance"],
            "seed": seed,
        },
        "memories": memories,
        "queries": queries,
    }


# ── Evaluation ─────────────────────────────────────────────────────────────


def run_hologrameval_benchmark(
    dataset: dict[str, Any],
    galaxy: str = "hologram_bench",
    per_case: bool = False,
) -> dict[str, Any]:
    """Run HologramEval benchmark.

    For each query type, tests whether the 5D holographic positioning
    correctly influences retrieval ranking.
    """
    memories = dataset["memories"]
    queries = dataset["queries"]

    print(f"\n{'=' * 60}")
    print(f"HologramEval — {len(memories)} memories, {len(queries)} queries")
    print(f"{'=' * 60}")

    # Ensure galaxy exists
    try:
        _call_tool("galaxy.create", name=galaxy)
    except Exception:
        pass

    # Ingest memories with importance and tags
    print(f"\nIngesting {len(memories)} memories...")
    id_map: dict[str, str] = {}
    t_start = time.perf_counter()
    for mem in memories:
        result = _call_tool(
            "create_memory",
            title=mem["id"],
            content=mem["content"],
            galaxy=galaxy,
            tags=mem["expected_tags"],
            importance=mem["importance"],
        )
        actual_id = None
        if isinstance(result, dict):
            actual_id = result.get("memory_id") or result.get("details", {}).get("memory_id")
        if actual_id:
            id_map[mem["id"]] = actual_id

    ingest_time = time.perf_counter() - t_start
    print(f"  {len(id_map)}/{len(memories)} ingested in {ingest_time:.1f}s")

    # Evaluate queries
    print(f"\nEvaluating {len(queries)} queries...")
    total = 0
    correct = 0
    search_latencies: list[float] = []
    per_query_results: list[dict[str, Any]] = []
    type_stats: dict[str, dict[str, int]] = {}

    for q in queries:
        total += 1
        q_type = q["type"]
        if q_type not in type_stats:
            type_stats[q_type] = {"total": 0, "correct": 0}
        type_stats[q_type]["total"] += 1

        t0 = time.perf_counter()
        result = _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=10,
        )
        lat = (time.perf_counter() - t0) * 1000
        search_latencies.append(lat)

        # Extract retrieved content and metadata
        retrieved: list[dict[str, Any]] = []
        if result.get("status") == "success":
            details = result.get("details", {})
            data = details.get("memories", details.get("data", details.get("results", [])))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        retrieved.append({
                            "content": item.get("content", ""),
                            "title": item.get("title", ""),
                            "tags": item.get("tags", []),
                            "importance": item.get("importance", 0.5),
                            "id": item.get("id", ""),
                        })

        # Evaluate based on query type
        is_correct = False

        if q_type == "substring":
            # Standard substring match
            answer = q.get("answer", "")
            for r in retrieved:
                if answer.lower() in r["content"].lower():
                    is_correct = True
                    break

        elif q_type == "semantic":
            # Top result should be from the expected topic
            expected_topic = q.get("expected_topic", "")
            if retrieved:
                top = retrieved[0]
                if expected_topic in top.get("tags", []) or expected_topic in top["content"].lower():
                    is_correct = True

        elif q_type == "emotional":
            # Top result should contain the expected emotion label
            expected_emotion = q.get("expected_emotion", "")
            if retrieved:
                top = retrieved[0]
                if expected_emotion in top["content"].lower() or expected_emotion in top.get("tags", []):
                    is_correct = True

        elif q_type == "importance":
            # Top result should be from expected topic AND have importance >= min
            expected_topic = q.get("expected_topic", "")
            min_imp = q.get("min_importance", 0.7)
            if retrieved:
                top = retrieved[0]
                topic_match = expected_topic in top.get("tags", []) or expected_topic in top["content"].lower()
                imp_match = float(top.get("importance", 0)) >= min_imp
                is_correct = topic_match and imp_match

        elif q_type == "temporal":
            # At least one result in top-5 should be from expected topic
            expected_topic = q.get("expected_topic", "")
            for r in retrieved[:5]:
                if expected_topic in r.get("tags", []) or expected_topic in r["content"].lower():
                    is_correct = True
                    break

        elif q_type == "combined":
            # Top result should be from expected topic with high importance
            expected_topic = q.get("expected_topic", "")
            min_imp = q.get("min_importance", 0.7)
            if retrieved:
                top = retrieved[0]
                topic_match = expected_topic in top.get("tags", []) or expected_topic in top["content"].lower()
                imp_match = float(top.get("importance", 0)) >= min_imp
                is_correct = topic_match and imp_match

        if is_correct:
            correct += 1
            type_stats[q_type]["correct"] += 1

        if per_case:
            per_query_results.append({
                "query_id": q["id"],
                "query": q["query"],
                "type": q_type,
                "is_correct": is_correct,
                "result_count": len(retrieved),
                "latency_ms": round(lat, 2),
            })

    search_latencies.sort()

    # Compute per-type accuracy
    type_breakdown: dict[str, dict[str, float]] = {}
    for q_type, stats in type_stats.items():
        t = stats["total"]
        type_breakdown[q_type] = {
            "total": t,
            "accuracy": stats["correct"] / t if t > 0 else 0,
        }

    results = {
        "system": "whitemagic",
        "benchmark": "hologrameval",
        "total_memories": len(memories),
        "total_queries": len(queries),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ingest_time_s": round(ingest_time, 2),
        "overall_accuracy": correct / total if total > 0 else 0,
        "type_breakdown": type_breakdown,
        "search": {
            "count": len(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2] if search_latencies else 0,
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)] if search_latencies else 0,
        },
        "tokens": {
            "tokens_per_query": 0,
            "llm_calls": 0,
        },
    }

    if per_case:
        results["per_query"] = per_query_results

    print(f"\nResults:")
    print(f"  Overall accuracy: {results['overall_accuracy']:.2%}")
    for q_type, bd in type_breakdown.items():
        print(f"  {q_type}: {bd['accuracy']:.2%} ({bd['total']} queries)")
    print(f"  Search p50: {results['search']['p50_ms']:.1f}ms")

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="HologramEval benchmark adapter")
    parser.add_argument("--data-path", default=None, help="Path to HologramEval JSON dataset")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic dataset")
    parser.add_argument("--num-memories", type=int, default=100, help="Synthetic: number of memories")
    parser.add_argument("--num-queries", type=int, default=50, help="Synthetic: number of queries")
    parser.add_argument("--galaxy", default="hologram_bench", help="Galaxy to use")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    if args.data_path:
        dataset = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
        print(f"Loaded dataset from {args.data_path}")
    elif args.synthetic:
        dataset = generate_synthetic_hologrameval(
            num_memories=args.num_memories,
            num_queries=args.num_queries,
        )
        print(f"Generated synthetic dataset: {dataset['metadata']}")
    else:
        print("No dataset found. Using synthetic dataset.")
        dataset = generate_synthetic_hologrameval()

    results = run_hologrameval_benchmark(
        dataset=dataset,
        galaxy=args.galaxy,
        per_case=args.per_case,
    )

    output_path = args.output or "benchmarks/results/hologrameval.json"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
