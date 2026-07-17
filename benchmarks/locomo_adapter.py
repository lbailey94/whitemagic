"""LoCoMo benchmark adapter — Long Conversation Memory evaluation.

Loads the LoCoMo dataset (if available) and evaluates WhiteMagic's recall
quality against the standard benchmark used by Mem0, MemGPT, and others.

Dataset format (JSON):
    [
        {
            "conversation_id": "...",
            "session_id": "...",
            "turns": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ],
            "qa_pairs": [
                {
                    "question": "...",
                    "answer": "...",
                    "category": "temporal" | "preference" | "open_domain" | ...
                }
            ]
        }
    ]

If the dataset is not available locally, a synthetic LoCoMo-style dataset
is generated for testing the pipeline.

Usage:
    python benchmarks/locomo_adapter.py --data-path /path/to/locomo.json
    python benchmarks/locomo_adapter.py --synthetic --output benchmarks/results/locomo.json
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


def _call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    from whitemagic.tools.unified_api import call_tool
    return call_tool(name, **kwargs)


def generate_synthetic_locomo(
    num_conversations: int = 20,
    turns_per_conversation: int = 30,
    qa_per_conversation: int = 5,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate a synthetic LoCoMo-style dataset for pipeline testing.

    Each conversation has multiple turns of user/assistant dialogue,
    followed by QA pairs that test memory of specific details.
    """
    rng = random.Random(seed)

    PERSONS = [
        ("Alice", "software engineer", "San Francisco", "hiking", "Italian food"),
        ("Bob", "data scientist", "New York", "chess", "Japanese food"),
        ("Carol", "product manager", "London", "painting", "Indian food"),
        ("Dave", "researcher", "Tokyo", "cycling", "Korean food"),
        ("Eve", "designer", "Paris", "photography", "French food"),
    ]

    TOPICS = [
        "project deadlines", "team dynamics", "career goals",
        "weekend plans", "travel destinations", "book recommendations",
        "technology trends", "health and fitness", "financial planning",
        "home improvement", "cooking recipes", "music preferences",
        "education plans", "startup ideas", "research directions",
        "office politics", "client relationships", "product launches",
    ]

    # Topic-specific details so FTS5 can distinguish turns about different topics.
    # Each topic has its own pool of details — no cross-topic collision.
    TOPIC_DETAILS = {
        "project deadlines": [
            "the deadline is next Friday", "the report is due in two weeks",
            "the sprint ends on Thursday", "the milestone is March 15th",
        ],
        "team dynamics": [
            "the team has 8 members", "Sarah joined the team last week",
            "there was a conflict between two developers", "the team decided to use agile",
        ],
        "career goals": [
            "she wants to become a tech lead", "he is aiming for a promotion by Q3",
            "she plans to switch to management", "he is considering a job change",
        ],
        "weekend plans": [
            "going hiking on Saturday", "visiting the new art exhibition",
            "having dinner with family", "attending a jazz concert",
        ],
        "travel destinations": [
            "planning a trip to Japan in spring", "considering a beach vacation in Bali",
            "booking a flight to Iceland", "exploring Portugal in summer",
        ],
        "book recommendations": [
            "recommended 'Designing Data-Intensive Applications'", "suggested 'The Pragmatic Programmer'",
            "mentioned 'Thinking in Systems'", "liked 'Accelerando' by Charles Stross",
        ],
        "technology trends": [
            "excited about Rust's growing adoption", "interested in WebAssembly for edge computing",
            "watching the LLM agent framework space", "exploring local-first software patterns",
        ],
        "health and fitness": [
            "started a new running routine", "trying intermittent fasting",
            "joined a climbing gym", "tracking sleep with a new device",
        ],
        "financial planning": [
            "the budget is $50,000", "the budget was approved yesterday",
            "considering index fund investing", "setting up an emergency fund",
        ],
        "home improvement": [
            "renovating the kitchen next month", "installed smart lighting",
            "planning a garden redesign", "repainting the living room",
        ],
        "cooking recipes": [
            "learned a new pasta recipe", "tried making sushi at home",
            "perfected the sourdough bread", "discovered a great curry technique",
        ],
        "music preferences": [
            "been listening to a lot of jazz", "discovered a great synthwave playlist",
            "went to a classical concert", "started learning the guitar",
        ],
        "education plans": [
            "enrolled in a machine learning course", "considering an MBA program",
            "taking online classes on systems design", "learning Japanese on Duolingo",
        ],
        "startup ideas": [
            "pitching an AI code review tool", "building a memory engine for agents",
            "exploring decentralized identity", "working on a local search product",
        ],
        "research directions": [
            "exploring holographic memory representations", "studying polyglot acceleration patterns",
            "researching consciousness models for AI", "investigating ethical governance frameworks",
        ],
        "office politics": [
            "there was a disagreement about the roadmap", "the engineering team pushed back on scope",
            "management changed the priority list", "a new VP joined last week",
        ],
        "client relationships": [
            "the client prefers email communication", "the client asked for a demo next Tuesday",
            "the client wants to extend the contract", "the client raised concerns about timeline",
        ],
        "product launches": [
            "launching v2.0 in September", "the beta is live for 50 users",
            "planning a public release in Q4", "the launch was delayed by two weeks",
        ],
    }

    conversations = []

    for ci in range(num_conversations):
        person = rng.choice(PERSONS)
        name, job, city, hobby, food = person

        turns = []
        facts_mentioned: list[dict[str, str]] = []

        # Shuffle topics so each conversation has a different topic order
        conv_topics = TOPICS[:]
        rng.shuffle(conv_topics)

        for ti in range(turns_per_conversation):
            topic = conv_topics[ti % len(conv_topics)]
            detail = rng.choice(TOPIC_DETAILS[topic])

            if ti % 2 == 0:
                content = f"I was talking with {name} about {topic}. They mentioned {detail}."
                turns.append({"role": "user", "content": content})
                facts_mentioned.append({
                    "fact": f"{name} mentioned {detail} regarding {topic}",
                    "detail": detail,
                    "topic": topic,
                    "person": name,
                })
            else:
                content = f"That's interesting about {topic}. Can you tell me more about {detail}?"
                turns.append({"role": "assistant", "content": content})

        # Generate QA pairs from mentioned facts
        qa_pairs = []
        rng.shuffle(facts_mentioned)
        for fi, fact in enumerate(facts_mentioned[:qa_per_conversation]):
            qa_pairs.append({
                "question": f"What did {fact['person']} say about {fact['topic']}?",
                "answer": fact["detail"],
                "category": "detail_recall",
            })

        conversations.append({
            "conversation_id": f"conv_{ci:04d}",
            "session_id": f"sess_{ci:04d}",
            "turns": turns,
            "qa_pairs": qa_pairs,
        })

    return conversations


def load_locomo(data_path: str | Path) -> list[dict[str, Any]]:
    """Load LoCoMo dataset from JSON file."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"LoCoMo dataset not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_locomo_benchmark(
    conversations: list[dict[str, Any]],
    galaxy: str = "locomo_bench",
    per_case: bool = False,
) -> dict[str, Any]:
    """Run LoCoMo benchmark against WhiteMagic.

    For each conversation:
    1. Store all turns as memories
    2. For each QA pair, search for the answer
    3. Check if the ground-truth answer content appears in search results

    Returns benchmark results dict.
    """
    print(f"\n{'=' * 60}")
    print(f"LoCoMo Benchmark — {len(conversations)} conversations")
    print(f"{'=' * 60}")

    # Ensure galaxy exists
    try:
        _call_tool("galaxy.create", name=galaxy)
    except Exception:
        pass

    # Phase 1: Ingest conversations
    print(f"\nIngesting {len(conversations)} conversations...")
    total_turns = 0
    id_map: dict[str, str] = {}
    ingest_latencies: list[float] = []

    for conv in conversations:
        conv_id = conv["conversation_id"]
        for ti, turn in enumerate(conv["turns"]):
            t0 = time.perf_counter()
            result = _call_tool(
                "create_memory",
                title=f"{conv_id}_turn_{ti}",
                content=turn["content"],
                galaxy=galaxy,
                tags=[turn["role"], conv_id],
            )
            ingest_latencies.append((time.perf_counter() - t0) * 1000)
            total_turns += 1

            actual_id = None
            if isinstance(result, dict):
                actual_id = result.get("memory_id") or result.get("details", {}).get("memory_id")
            if actual_id:
                id_map[f"{conv_id}_turn_{ti}"] = actual_id

        # Store conversation-level summary (0-token, structural compression)
        # Concatenates user turns which typically contain the factual content
        # that QA pairs ask about. This helps multi-hop and open-domain queries
        # where the answer spans multiple turns.
        user_facts = [
            t["content"] for t in conv["turns"]
            if t["role"] == "user" and len(t["content"]) > 20
        ]
        if user_facts:
            summary_content = " | ".join(user_facts[:20])  # Cap at 20 turns
            t0 = time.perf_counter()
            result = _call_tool(
                "create_memory",
                title=f"{conv_id}_summary",
                content=summary_content,
                galaxy=galaxy,
                tags=["summary", conv_id],
            )
            ingest_latencies.append((time.perf_counter() - t0) * 1000)
            total_turns += 1

            actual_id = None
            if isinstance(result, dict):
                actual_id = result.get("memory_id") or result.get("details", {}).get("memory_id")
            if actual_id:
                id_map[f"{conv_id}_summary"] = actual_id

    ingest_latencies.sort()
    print(f"  {total_turns} turns ingested in {sum(ingest_latencies) / 1000:.1f}s")
    print(f"  p50={ingest_latencies[len(ingest_latencies) // 2]:.1f}ms")

    # Phase 2: Evaluate QA pairs
    print(f"\nEvaluating QA pairs...")
    total_qa = 0
    recall_at_1 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    mrr_sum = 0.0
    search_latencies: list[float] = []
    per_query_results: list[dict[str, Any]] = []

    # Category breakdown
    cat_stats: dict[str, dict[str, int]] = {}

    for conv in conversations:
        conv_id = conv["conversation_id"]
        for qa in conv.get("qa_pairs", []):
            total_qa += 1
            question = qa["question"]
            answer = qa["answer"]
            category = qa.get("category", "unknown")

            if category not in cat_stats:
                cat_stats[category] = {"total": 0, "r1": 0, "r5": 0, "r10": 0}

            cat_stats[category]["total"] += 1

            t0 = time.perf_counter()
            result = _call_tool(
                "search_memories",
                query=question,
                galaxy=galaxy,
                limit=10,
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
                            content = item.get("content", "")
                            retrieved_contents.append(content)

            # Check if answer appears in retrieved results
            # Use substring matching — answer should appear in the stored turn content
            match_ranks = []
            for rank, content in enumerate(retrieved_contents, 1):
                if answer.lower() in content.lower():
                    match_ranks.append(rank)

            r1 = 1 if any(r <= 1 for r in match_ranks) else 0
            r5 = 1 if any(r <= 5 for r in match_ranks) else 0
            r10 = 1 if match_ranks else 0

            recall_at_1 += r1
            recall_at_5 += r5
            recall_at_10 += r10
            cat_stats[category]["r1"] += r1
            cat_stats[category]["r5"] += r5
            cat_stats[category]["r10"] += r10

            mrr = 0.0
            if match_ranks:
                mrr = 1.0 / match_ranks[0]
            mrr_sum += mrr

            if per_case:
                per_query_results.append({
                    "conversation_id": conv_id,
                    "question": question,
                    "answer": answer,
                    "category": category,
                    "recall_at_1": r1,
                    "recall_at_5": r5,
                    "recall_at_10": r10,
                    "mrr": round(mrr, 4),
                    "first_match_rank": match_ranks[0] if match_ranks else None,
                    "latency_ms": round(lat, 2),
                })

    search_latencies.sort()

    # Compute category breakdown
    cat_breakdown: dict[str, dict[str, float]] = {}
    for cat, stats in cat_stats.items():
        t = stats["total"]
        cat_breakdown[cat] = {
            "total": t,
            "recall_at_1": stats["r1"] / t if t > 0 else 0,
            "recall_at_5": stats["r5"] / t if t > 0 else 0,
            "recall_at_10": stats["r10"] / t if t > 0 else 0,
        }

    results = {
        "system": "whitemagic",
        "benchmark": "locomo",
        "num_conversations": len(conversations),
        "total_turns": total_turns,
        "total_qa_pairs": total_qa,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ingest": {
            "count": total_turns,
            "p50_ms": ingest_latencies[len(ingest_latencies) // 2],
            "p95_ms": ingest_latencies[int(len(ingest_latencies) * 0.95)],
            "throughput_ops_sec": len(ingest_latencies) / (sum(ingest_latencies) / 1000) if sum(ingest_latencies) > 0 else 0,
        },
        "search": {
            "count": len(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2],
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)],
            "p99_ms": search_latencies[int(len(search_latencies) * 0.99)],
        },
        "recall": {
            "total_queries": total_qa,
            "recall_at_1": recall_at_1 / total_qa if total_qa > 0 else 0,
            "recall_at_5": recall_at_5 / total_qa if total_qa > 0 else 0,
            "recall_at_10": recall_at_10 / total_qa if total_qa > 0 else 0,
            "mrr": mrr_sum / total_qa if total_qa > 0 else 0,
        },
        "category_breakdown": cat_breakdown,
        "tokens": {
            "tokens_per_query": 0,
            "llm_calls": 0,
            "search_method": "FTS5 BM25 + FastEmbed semantic reranking",
        },
    }

    if per_case:
        results["per_query"] = per_query_results

    print(f"\nResults:")
    print(f"  recall@1: {results['recall']['recall_at_1']:.2%}")
    print(f"  recall@5: {results['recall']['recall_at_5']:.2%}")
    print(f"  recall@10: {results['recall']['recall_at_10']:.2%}")
    print(f"  MRR: {results['recall']['mrr']:.4f}")
    print(f"  Search p50: {results['search']['p50_ms']:.1f}ms")
    print(f"  Tokens/query: 0")

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LoCoMo benchmark adapter")
    parser.add_argument("--data-path", default=None, help="Path to LoCoMo JSON dataset")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic LoCoMo-style dataset")
    parser.add_argument("--num-conversations", type=int, default=20, help="Synthetic: number of conversations")
    parser.add_argument("--turns-per-conv", type=int, default=30, help="Synthetic: turns per conversation")
    parser.add_argument("--qa-per-conv", type=int, default=5, help="Synthetic: QA pairs per conversation")
    parser.add_argument("--galaxy", default="locomo_bench", help="Galaxy to use")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    if args.data_path:
        conversations = load_locomo(args.data_path)
        print(f"Loaded {len(conversations)} conversations from {args.data_path}")
    elif args.synthetic:
        conversations = generate_synthetic_locomo(
            num_conversations=args.num_conversations,
            turns_per_conversation=args.turns_per_conv,
            qa_per_conversation=args.qa_per_conv,
        )
        print(f"Generated {len(conversations)} synthetic conversations")
    else:
        # Try default path, fall back to synthetic
        default_path = Path("benchmarks/data/locomo.json")
        if default_path.exists():
            conversations = load_locomo(default_path)
            print(f"Loaded {len(conversations)} conversations from {default_path}")
        else:
            print("No dataset path provided and no default found. Using synthetic dataset.")
            conversations = generate_synthetic_locomo()

    results = run_locomo_benchmark(
        conversations=conversations,
        galaxy=args.galaxy,
        per_case=args.per_case,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {args.output}")
    else:
        default_out = Path("benchmarks/results/locomo.json")
        default_out.parent.mkdir(parents=True, exist_ok=True)
        default_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {default_out}")


if __name__ == "__main__":
    main()
