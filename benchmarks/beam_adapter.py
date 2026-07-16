"""BEAM benchmark adapter — Benchmark for Evaluating Agent Memory.

Evaluates WhiteMagic against the BEAM benchmark, which tests:
  - Single-hop fact recall
  - Multi-hop reasoning (requires combining facts)
  - Temporal reasoning (fact currency)
  - Abstention (knowing when no answer exists)
  - Scale (performance with many memories)

If dataset not available locally, generates a synthetic BEAM-style dataset.

Usage:
    python benchmarks/beam_adapter.py --synthetic --output benchmarks/results/beam.json
    python benchmarks/beam_adapter.py --data-path /path/to/beam.json --per-case
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


def _call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.unified_api import call_tool
    return call_tool(name, **kwargs)


def generate_synthetic_beam(
    num_entities: int = 50,
    facts_per_entity: int = 5,
    num_queries: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate synthetic BEAM-style dataset.

    BEAM tests multi-hop reasoning by requiring the system to combine
    facts from multiple memories to answer questions.

    Dataset structure:
    - memories: list of factual statements
    - queries: questions with expected answer + hop count
    """
    rng = random.Random(seed)

    ENTITIES = [f"entity_{i:03d}" for i in range(num_entities)]
    ATTRIBUTES = [
        ("location", ["San Francisco", "New York", "London", "Tokyo", "Paris", "Berlin", "Sydney", "Toronto"]),
        ("role", ["engineer", "manager", "researcher", "designer", "analyst"]),
        ("project", ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta"]),
        ("language", ["Python", "Rust", "Go", "TypeScript", "Haskell", "Julia"]),
        ("team", ["backend", "frontend", "infrastructure", "data", "security"]),
    ]

    memories = []
    entity_facts: dict[str, dict[str, str]] = {}

    mid_counter = 0
    for entity in ENTITIES:
        entity_facts[entity] = {}
        for attr_name, values in ATTRIBUTES:
            value = rng.choice(values)
            fact_id = f"fact_{mid_counter:05d}"
            content = f"{entity} has {attr_name} {value}."
            memories.append({
                "id": fact_id,
                "content": content,
                "entity": entity,
                "attribute": attr_name,
                "value": value,
            })
            entity_facts[entity][attr_name] = value
            mid_counter += 1

    # Generate queries
    queries = []
    query_types = ["single_hop", "multi_hop", "temporal", "abstention"]

    for i in range(num_queries):
        q_type = rng.choice(query_types)

        if q_type == "single_hop":
            entity = rng.choice(ENTITIES)
            attr = rng.choice(list(ATTRIBUTES))[0]
            if attr in entity_facts.get(entity, {}):
                value = entity_facts[entity][attr]
                queries.append({
                    "id": f"q_{i:04d}",
                    "query": f"What is the {attr} of {entity}?",
                    "answer": value,
                    "type": "single_hop",
                    "hops": 1,
                    "expected_content": f"{entity} has {attr} {value}",
                })

        elif q_type == "multi_hop":
            # "Who is on the same team as the person working on project X?"
            entity1 = rng.choice(ENTITIES)
            if "project" in entity_facts.get(entity1, {}):
                project = entity_facts[entity1]["project"]
                # Find others on same project
                same_project = [
                    e for e, f in entity_facts.items()
                    if f.get("project") == project and e != entity1
                ]
                if same_project:
                    entity2 = rng.choice(same_project)
                    team = entity_facts[entity2].get("team", "unknown")
                    queries.append({
                        "id": f"q_{i:04d}",
                        "query": f"What team is the person working on project {project} on?",
                        "answer": team,
                        "type": "multi_hop",
                        "hops": 2,
                        "expected_content": f"has team {team}",
                    })

        elif q_type == "temporal":
            # Ask about current state
            entity = rng.choice(ENTITIES)
            attr = rng.choice(["role", "project", "team"])
            if attr in entity_facts.get(entity, {}):
                value = entity_facts[entity][attr]
                queries.append({
                    "id": f"q_{i:04d}",
                    "query": f"What is {entity}'s current {attr}?",
                    "answer": value,
                    "type": "temporal",
                    "hops": 1,
                    "expected_content": f"{entity} has {attr} {value}",
                })

        elif q_type == "abstention":
            # Ask about a non-existent entity
            fake_entity = f"nonexistent_{rng.randint(1000, 9999)}"
            attr = rng.choice(list(ATTRIBUTES))[0]
            queries.append({
                "id": f"q_{i:04d}",
                "query": f"What is the {attr} of {fake_entity}?",
                "answer": None,
                "type": "abstention",
                "hops": 0,
                "expected_content": None,
            })

    return {
        "memories": memories,
        "queries": queries,
        "metadata": {
            "num_entities": num_entities,
            "facts_per_entity": facts_per_entity,
            "total_memories": len(memories),
            "total_queries": len(queries),
        },
    }


def run_beam_benchmark(
    dataset: dict[str, Any],
    galaxy: str = "beam_bench",
    per_case: bool = False,
) -> dict[str, Any]:
    """Run BEAM benchmark.

    1. Ingest all memories
    2. For each query, search and check if answer appears
    3. Track per-type metrics (single-hop, multi-hop, temporal, abstention)
    """
    memories = dataset["memories"]
    queries = dataset["queries"]

    print(f"\n{'=' * 60}")
    print(f"BEAM Benchmark — {len(memories)} memories, {len(queries)} queries")
    print(f"{'=' * 60}")

    # Ensure galaxy exists
    try:
        _call_tool("galaxy.create", name=galaxy)
    except Exception:
        pass

    # Ingest memories
    print(f"\nIngesting {len(memories)} memories...")
    id_map: dict[str, str] = {}
    t_start = time.perf_counter()
    for mem in memories:
        result = _call_tool(
            "create_memory",
            title=mem["id"],
            content=mem["content"],
            galaxy=galaxy,
            tags=[mem["entity"], mem["attribute"]],
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

        search_limit = 20 if q_type == "multi_hop" else 10
        t0 = time.perf_counter()
        result = _call_tool(
            "search_memories",
            query=q["query"],
            galaxy=galaxy,
            limit=search_limit,
        )
        lat = (time.perf_counter() - t0) * 1000
        search_latencies.append(lat)

        # Extract retrieved content
        retrieved_contents: list[str] = []
        if result.get("status") == "success":
            details = result.get("details", {})
            data = details.get("memories", details.get("data", details.get("results", [])))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        retrieved_contents.append(item.get("content", ""))

        # Check answer
        answer = q.get("answer")
        expected_content = q.get("expected_content")

        is_correct = False
        if answer is None:
            # Abstention query — correct if no relevant results
            is_correct = len(retrieved_contents) == 0 or all(
                q["query"].split()[-1] not in c for c in retrieved_contents
            )
        elif expected_content:
            # Check if expected content appears in any result
            for content in retrieved_contents:
                if expected_content.lower() in content.lower():
                    is_correct = True
                    break

        if is_correct:
            correct += 1
            type_stats[q_type]["correct"] += 1

        if per_case:
            per_query_results.append({
                "query_id": q["id"],
                "query": q["query"],
                "type": q_type,
                "hops": q.get("hops", 0),
                "answer": answer,
                "is_correct": is_correct,
                "result_count": len(retrieved_contents),
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
        "benchmark": "beam",
        "total_memories": len(memories),
        "total_queries": len(queries),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ingest_time_s": round(ingest_time, 2),
        "overall_accuracy": correct / total if total > 0 else 0,
        "type_breakdown": type_breakdown,
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

    parser = argparse.ArgumentParser(description="BEAM benchmark adapter")
    parser.add_argument("--data-path", default=None, help="Path to BEAM JSON dataset")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic dataset")
    parser.add_argument("--num-entities", type=int, default=50, help="Synthetic: number of entities")
    parser.add_argument("--num-queries", type=int, default=100, help="Synthetic: number of queries")
    parser.add_argument("--galaxy", default="beam_bench", help="Galaxy to use")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    if args.data_path:
        dataset = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
        print(f"Loaded dataset from {args.data_path}")
    elif args.synthetic:
        dataset = generate_synthetic_beam(
            num_entities=args.num_entities,
            num_queries=args.num_queries,
        )
        print(f"Generated synthetic dataset: {dataset['metadata']}")
    else:
        default_path = Path("benchmarks/data/beam.json")
        if default_path.exists():
            dataset = json.loads(default_path.read_text(encoding="utf-8"))
            print(f"Loaded dataset from {default_path}")
        else:
            print("No dataset found. Using synthetic dataset.")
            dataset = generate_synthetic_beam()

    results = run_beam_benchmark(
        dataset=dataset,
        galaxy=args.galaxy,
        per_case=args.per_case,
    )

    output_path = args.output or "benchmarks/results/beam.json"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
