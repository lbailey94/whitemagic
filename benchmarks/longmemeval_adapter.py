"""LongMemEval benchmark adapter — long-term memory evaluation.

Evaluates WhiteMagic against the LongMemEval benchmark, which tests:
  - Single-session recall
  - Multi-session aggregation
  - Temporal reasoning
  - Preference tracking
  - Knowledge updates

If dataset not available locally, generates a synthetic LongMemEval-style
dataset for pipeline testing.

Usage:
    python benchmarks/longmemeval_adapter.py --data-path /path/to/longmemeval.json
    python benchmarks/longmemeval_adapter.py --synthetic --output benchmarks/results/longmemeval.json
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


def generate_synthetic_longmemeval(
    num_sessions: int = 10,
    turns_per_session: int = 20,
    questions_per_session: int = 5,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate synthetic LongMemEval-style dataset.

    LongMemEval tests multi-session memory with categories:
    - detail_recall: specific facts from conversations
    - aggregation: combining info across sessions
    - temporal: time-based reasoning
    - preference: user preference tracking
    - knowledge_update: updated information over time
    """
    rng = random.Random(seed)

    USER_PROFILES = [
        {"name": "Alice", "role": "engineer", "preferences": {"language": "Python", "editor": "VS Code", "coffee": "oat milk latte"}},
        {"name": "Bob", "role": "analyst", "preferences": {"language": "R", "editor": "Neovim", "coffee": "espresso"}},
        {"name": "Carol", "role": "manager", "preferences": {"language": "SQL", "editor": "JetBrains", "coffee": "cappuccino"}},
    ]

    PREFERENCE_CHANGES = [
        ("switched from Python to Rust", "language", "Rust"),
        ("started using Neovim instead of VS Code", "editor", "Neovim"),
        ("now prefers tea over coffee", "coffee", "green tea"),
        ("moved from San Francisco to Austin", "location", "Austin"),
        ("changed team from backend to infrastructure", "team", "infrastructure"),
    ]

    SESSION_TOPICS = [
        "code review", "architecture discussion", "bug triage",
        "sprint planning", "retrospective", "design review",
        "performance optimization", "deployment strategy",
        "team hiring", "project roadmap",
    ]

    sessions = []

    for si in range(num_sessions):
        profile = rng.choice(USER_PROFILES)
        name = profile["name"]

        turns = []
        facts: list[dict[str, str]] = []

        # Add some preference changes in later sessions
        if si > 2 and rng.random() < 0.4:
            change_desc, pref_key, new_val = rng.choice(PREFERENCE_CHANGES)
            turn_content = f"{name} mentioned they {change_desc}."
            turns.append({"role": "user", "content": turn_content})
            turns.append({"role": "assistant", "content": f"Noted, you now prefer {new_val} for {pref_key}."})
            facts.append({
                "fact": turn_content,
                "detail": new_val,
                "category": "preference",
                "key": pref_key,
            })

        for ti in range(turns_per_session - len(turns)):
            topic = rng.choice(SESSION_TOPICS)
            if ti % 2 == 0:
                detail = f"discussed {topic} with {name}'s team"
                content = f"In the {topic} session, {name} said the key takeaway was about {detail}."
                turns.append({"role": "user", "content": content})
                facts.append({
                    "fact": content,
                    "detail": detail,
                    "category": "detail_recall",
                    "topic": topic,
                })
            else:
                turns.append({"role": "assistant", "content": f"Understood. Let me help with {topic}."})

        # Generate questions
        questions = []
        rng.shuffle(facts)
        for fi, fact in enumerate(facts[:questions_per_session]):
            cat = fact.get("category", "detail_recall")
            if cat == "preference":
                q = f"What is {name}'s current preference for {fact['key']}?"
                a = fact["detail"]
            else:
                q = f"What did {name} discuss about {fact.get('topic', 'the project')}?"
                a = fact["detail"]

            questions.append({
                "question": q,
                "answer": a,
                "category": cat,
                "session_index": si,
            })

        sessions.append({
            "session_id": f"session_{si:04d}",
            "user_name": name,
            "turns": turns,
            "questions": questions,
        })

    return sessions


def run_longmemeval_benchmark(
    sessions: list[dict[str, Any]],
    galaxy: str = "longmemeval_bench",
    per_case: bool = False,
) -> dict[str, Any]:
    """Run LongMemEval benchmark.

    1. Ingest all sessions as memories (chronologically)
    2. For each question, search and check if answer appears
    3. Track per-category recall
    """
    print(f"\n{'=' * 60}")
    print(f"LongMemEval Benchmark — {len(sessions)} sessions")
    print(f"{'=' * 60}")

    try:
        _call_tool("galaxy.create", name=galaxy)
    except Exception:
        pass

    # Ingest
    print(f"\nIngesting {len(sessions)} sessions...")
    total_turns = 0
    ingest_latencies: list[float] = []

    for session in sessions:
        sid = session["session_id"]
        for ti, turn in enumerate(session["turns"]):
            t0 = time.perf_counter()
            _call_tool(
                "create_memory",
                title=f"{sid}_turn_{ti}",
                content=turn["content"],
                galaxy=galaxy,
                tags=[turn["role"], sid, session.get("user_name", "")],
            )
            ingest_latencies.append((time.perf_counter() - t0) * 1000)
            total_turns += 1

        # Session-level summary (0-token, structural compression)
        user_facts = [
            t["content"] for t in session["turns"]
            if t["role"] == "user" and len(t["content"]) > 20
        ]
        if user_facts:
            summary_content = " | ".join(user_facts[:20])
            t0 = time.perf_counter()
            _call_tool(
                "create_memory",
                title=f"{sid}_summary",
                content=summary_content,
                galaxy=galaxy,
                tags=["summary", sid, session.get("user_name", "")],
            )
            ingest_latencies.append((time.perf_counter() - t0) * 1000)
            total_turns += 1

    ingest_latencies.sort()
    print(f"  {total_turns} turns ingested in {sum(ingest_latencies) / 1000:.1f}s")

    # Evaluate
    print(f"\nEvaluating questions...")
    total_q = 0
    recall_at_1 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    mrr_sum = 0.0
    search_latencies: list[float] = []
    per_query_results: list[dict[str, Any]] = []
    cat_stats: dict[str, dict[str, int]] = {}

    for session in sessions:
        sid = session["session_id"]
        for q_data in session.get("questions", []):
            total_q += 1
            question = q_data["question"]
            answer = q_data["answer"]
            category = q_data.get("category", "unknown")

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

            retrieved_contents: list[str] = []
            if result.get("status") == "success":
                details = result.get("details", {})
                data = details.get("memories", details.get("data", details.get("results", [])))
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            retrieved_contents.append(item.get("content", ""))

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

            mrr = 1.0 / match_ranks[0] if match_ranks else 0.0
            mrr_sum += mrr

            if per_case:
                per_query_results.append({
                    "session_id": sid,
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
        "benchmark": "longmemeval",
        "num_sessions": len(sessions),
        "total_turns": total_turns,
        "total_questions": total_q,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ingest": {
            "count": total_turns,
            "p50_ms": ingest_latencies[len(ingest_latencies) // 2],
            "p95_ms": ingest_latencies[int(len(ingest_latencies) * 0.95)],
        },
        "search": {
            "count": len(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2],
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)],
            "p99_ms": search_latencies[int(len(search_latencies) * 0.99)],
        },
        "recall": {
            "total_queries": total_q,
            "recall_at_1": recall_at_1 / total_q if total_q > 0 else 0,
            "recall_at_5": recall_at_5 / total_q if total_q > 0 else 0,
            "recall_at_10": recall_at_10 / total_q if total_q > 0 else 0,
            "mrr": mrr_sum / total_q if total_q > 0 else 0,
        },
        "category_breakdown": cat_breakdown,
        "tokens": {
            "tokens_per_query": 0,
            "llm_calls": 0,
        },
    }

    if per_case:
        results["per_query"] = per_query_results

    print(f"\nResults:")
    print(f"  recall@1: {results['recall']['recall_at_1']:.2%}")
    print(f"  recall@5: {results['recall']['recall_at_5']:.2%}")
    print(f"  recall@10: {results['recall']['recall_at_10']:.2%}")
    print(f"  MRR: {results['recall']['mrr']:.4f}")
    for cat, bd in cat_breakdown.items():
        print(f"  {cat}: r@1={bd['recall_at_1']:.2%} r@5={bd['recall_at_5']:.2%} ({bd['total']} q)")

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LongMemEval benchmark adapter")
    parser.add_argument("--data-path", default=None, help="Path to LongMemEval JSON dataset")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic dataset")
    parser.add_argument("--num-sessions", type=int, default=10, help="Synthetic: number of sessions")
    parser.add_argument("--turns-per-session", type=int, default=20, help="Synthetic: turns per session")
    parser.add_argument("--questions-per-session", type=int, default=5, help="Synthetic: questions per session")
    parser.add_argument("--galaxy", default="longmemeval_bench", help="Galaxy to use")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    if args.data_path:
        sessions = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
        print(f"Loaded {len(sessions)} sessions from {args.data_path}")
    elif args.synthetic:
        sessions = generate_synthetic_longmemeval(
            num_sessions=args.num_sessions,
            turns_per_session=args.turns_per_session,
            questions_per_session=args.questions_per_session,
        )
        print(f"Generated {len(sessions)} synthetic sessions")
    else:
        default_path = Path("benchmarks/data/longmemeval.json")
        if default_path.exists():
            sessions = json.loads(default_path.read_text(encoding="utf-8"))
            print(f"Loaded {len(sessions)} sessions from {default_path}")
        else:
            print("No dataset found. Using synthetic dataset.")
            sessions = generate_synthetic_longmemeval()

    results = run_longmemeval_benchmark(
        sessions=sessions,
        galaxy=args.galaxy,
        per_case=args.per_case,
    )

    output_path = args.output or "benchmarks/results/longmemeval.json"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
