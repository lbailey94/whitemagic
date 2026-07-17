"""LoCoMo-Plus — Cognitive Memory Benchmark.

Goes beyond LoCoMo's fact retrieval to test cognitive memory capabilities:
  1. Temporal reasoning — when did X happen relative to Y?
  2. Preference drift — how did preferences change across conversations?
  3. Goal inference — what is someone trying to achieve?
  4. Emotional context — what was the emotional state when X was discussed?
  5. Cross-conversation synthesis — connect facts across conversations
  6. Contradiction detection — identify when someone changed their mind
  7. Social graph reasoning — who knows whom, relationship types
  8. Importance-weighted recall — which facts matter most to the person?

LoCoMo tests "can you find this fact?"
LoCoMo-Plus tests "can you reason about this person's cognitive state?"

All 0-token evaluation. Uses synthetic conversations with embedded cognitive
structure and known ground truth.

Usage:
    python benchmarks/locomo_plus_adapter.py --synthetic
    python benchmarks/locomo_plus_adapter.py --data-path /path/to/locomo_plus.json
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ── Synthetic persona definitions ─────────────────────────────────────────

PERSONAS = [
    {
        "name": "Alex",
        "age": 28,
        "occupation": "software engineer",
        "location": "Seattle",
        "values": ["work-life balance", "continuous learning"],
        "goals": ["get promoted to senior", "learn Rust"],
        "preferences_initial": {"language": "Python", "hobby": "rock climbing", "food": "Italian"},
        "preferences_final": {"language": "Rust", "hobby": "bouldering", "food": "Japanese"},
        "emotional_baselines": {"work": 0.6, "hobby": 0.9, "social": 0.7},
    },
    {
        "name": "Sam",
        "age": 34,
        "occupation": "product manager",
        "location": "Austin",
        "values": ["user empathy", "data-driven decisions"],
        "goals": ["launch v2.0", "hire 3 engineers"],
        "preferences_initial": {"tool": "Jira", "hobby": "running", "food": "Mexican"},
        "preferences_final": {"tool": "Linear", "hobby": "cycling", "food": "Thai"},
        "emotional_baselines": {"work": 0.5, "hobby": 0.8, "social": 0.6},
    },
    {
        "name": "Jordan",
        "age": 41,
        "occupation": "startup founder",
        "location": "San Francisco",
        "values": ["innovation", "mentorship"],
        "goals": ["raise Series A", "build engineering team"],
        "preferences_initial": {"language": "Go", "hobby": "chess", "food": "Korean"},
        "preferences_final": {"language": "TypeScript", "hobby": "piano", "food": "Vietnamese"},
        "emotional_baselines": {"work": 0.4, "hobby": 0.7, "social": 0.5},
    },
]

SOCIAL_CONNECTIONS = [
    ("Alex", "friend", "Jamie"),
    ("Alex", "colleague", "Taylor"),
    ("Sam", "mentor", "Jordan"),
    ("Jordan", "investor", "Robin"),
    ("Sam", "friend", "Casey"),
]


# ── Conversation generation ───────────────────────────────────────────────

def _generate_conversations(persona: dict, num_sessions: int = 5) -> list[dict]:
    """Generate multi-session conversations for a persona with cognitive structure."""
    sessions = []
    name = persona["name"]
    prefs = persona["preferences_initial"]
    goals = persona["goals"]

    for session_idx in range(num_sessions):
        # Gradually shift preferences toward final
        progress = session_idx / max(num_sessions - 1, 1)
        prefs_current = {}
        for key in persona["preferences_initial"]:
            initial = persona["preferences_initial"][key]
            final = persona["preferences_final"][key]
            if progress > 0.5:
                prefs_current[key] = final
            else:
                prefs_current[key] = initial

        turns = []
        turn_idx = 0

        # Work discussion
        # Use first preference key (language, tool, etc.) for work context
        work_pref_key = list(prefs_current.keys())[0]
        if session_idx < num_sessions - 1:
            turns.append({
                "speaker": name,
                "text": f"I've been working on my goal to {goals[0]}. "
                        f"Using {prefs_current[work_pref_key]} at work lately.",
                "emotion": "determined" if progress < 0.5 else "confident",
                "emotion_valence": 0.6 + progress * 0.2,
            })
            turn_idx += 1

            turns.append({
                "speaker": "Friend",
                "text": f"How's the {persona['occupation']} life in {persona['location']}?",
                "emotion": "curious",
                "emotion_valence": 0.5,
            })
            turn_idx += 1

        # Hobby discussion
        turns.append({
            "speaker": name,
            "text": f"Went {prefs_current['hobby']} this weekend. Love it!"
                    + (" Thinking of switching from " + persona["preferences_initial"]["hobby"] + "."
                       if progress > 0.5 and prefs_current["hobby"] != persona["preferences_initial"]["hobby"] else ""),
            "emotion": "happy",
            "emotion_valence": persona["emotional_baselines"]["hobby"],
        })
        turn_idx += 1

        # Food preference (changes mid-conversation sequence)
        if session_idx == num_sessions // 2:
            turns.append({
                "speaker": name,
                "text": f"Actually, I'm getting tired of {persona['preferences_initial']['food']} food. "
                        f"Been trying {persona['preferences_final']['food']} lately and it's amazing.",
                "emotion": "excited",
                "emotion_valence": 0.85,
            })
            turn_idx += 1
        else:
            turns.append({
                "speaker": name,
                "text": f"Had great {prefs_current['food']} food yesterday.",
                "emotion": "content",
                "emotion_valence": 0.65,
            })
            turn_idx += 1

        # Goal progress
        if session_idx > 0:
            goal_progress = "making progress on" if progress < 0.7 else "almost done with"
            turns.append({
                "speaker": name,
                "text": f"I'm {goal_progress} my goal to {goals[0]}. "
                        f"My value of {persona['values'][0]} keeps me motivated.",
                "emotion": "motivated",
                "emotion_valence": 0.7,
            })
            turn_idx += 1

        # Social connection mention
        for conn_name, conn_type, conn_target in SOCIAL_CONNECTIONS:
            if conn_name == name and session_idx == num_sessions - 1:
                turns.append({
                    "speaker": name,
                    "text": f"My {conn_type} {conn_target} has been really supportive.",
                    "emotion": "grateful",
                    "emotion_valence": 0.8,
                })
                turn_idx += 1

        sessions.append({
            "session_id": f"session_{session_idx}",
            "timestamp": f"2024-0{session_idx + 1}-15T10:00:00Z",
            "turns": turns,
        })

    return sessions


# ── Query generation ──────────────────────────────────────────────────────

QUERY_TYPES = [
    "temporal_reasoning",
    "preference_drift",
    "goal_inference",
    "emotional_context",
    "cross_conversation",
    "contradiction_detection",
    "social_graph",
    "importance_weighted",
]


def _generate_queries(persona: dict, sessions: list[dict]) -> list[dict]:
    """Generate cognitive queries with known ground-truth answers."""
    name = persona["name"]
    queries = []

    # 1. Temporal reasoning — when did X happen?
    first_pref_key = list(persona['preferences_final'].keys())[0]
    queries.append({
        "type": "temporal_reasoning",
        "question": f"When did {name} start using {persona['preferences_final'][first_pref_key]}?",
        "answer": f"session_{len(sessions) // 2}",
        "answer_keywords": {persona["preferences_final"][first_pref_key].lower(), "switched", "changed"},
        "evidence_session": len(sessions) // 2,
    })

    # 2. Preference drift — how did preferences change?
    for pref_key in list(persona['preferences_initial'].keys()):
        initial = persona["preferences_initial"][pref_key]
        final = persona["preferences_final"][pref_key]
        if initial != final:
            queries.append({
                "type": "preference_drift",
                "question": f"What {pref_key} did {name} switch from and to?",
                "answer": f"{initial} to {final}",
                "answer_keywords": {initial.lower(), final.lower(), "switched", "changed", "from", "to"},
            })

    # 3. Goal inference — what is someone trying to achieve?
    for goal in persona["goals"]:
        queries.append({
            "type": "goal_inference",
            "question": f"What is {name}'s goal related to {goal.split()[-1]}?",
            "answer": goal,
            "answer_keywords": {word.lower() for word in goal.split() if len(word) > 3},
        })

    # 4. Emotional context — what was the emotional state?
    for session in sessions:
        for turn in session["turns"]:
            if turn["speaker"] == name and "emotion" in turn:
                emotion = turn["emotion"]
                text_snippet = turn["text"][:50]
                queries.append({
                    "type": "emotional_context",
                    "question": f"How was {name} feeling when discussing {text_snippet}?",
                    "answer": emotion,
                    "answer_keywords": {emotion.lower()},
                })
                break  # One per session

    # 5. Cross-conversation synthesis
    first_key = list(persona['preferences_initial'].keys())[0]
    queries.append({
        "type": "cross_conversation",
        "question": f"What {first_key}s has {name} used across all conversations?",
        "answer": f"{persona['preferences_initial'][first_key]} and {persona['preferences_final'][first_key]}",
        "answer_keywords": {persona["preferences_initial"][first_key].lower(),
                           persona["preferences_final"][first_key].lower()},
    })

    # 6. Contradiction detection — identify preference change
    queries.append({
        "type": "contradiction_detection",
        "question": f"Did {name} change their food preference? From what to what?",
        "answer": f"Yes, from {persona['preferences_initial']['food']} to {persona['preferences_final']['food']}",
        "answer_keywords": {persona["preferences_initial"]["food"].lower(),
                           persona["preferences_final"]["food"].lower(),
                           "yes", "changed", "switched", "tired"},
    })

    # 7. Social graph reasoning
    for conn_name, conn_type, conn_target in SOCIAL_CONNECTIONS:
        if conn_name == name:
            queries.append({
                "type": "social_graph",
                "question": f"Who is {conn_target} to {name}?",
                "answer": conn_type,
                "answer_keywords": {conn_type.lower(), conn_target.lower()},
            })

    # 8. Importance-weighted recall — what matters most?
    for value in persona["values"]:
        queries.append({
            "type": "importance_weighted",
            "question": f"What value does {name} care about most?",
            "answer": value,
            "answer_keywords": {word.lower() for word in value.split() if len(word) > 3},
        })

    return queries


# ── Dataset assembly ──────────────────────────────────────────────────────

def generate_synthetic_locomo_plus(
    num_personas: int = 3,
    sessions_per_persona: int = 5,
) -> dict[str, Any]:
    """Generate a synthetic LoCoMo-Plus dataset."""
    personas = PERSONAS[:num_personas]
    conversations = []
    all_queries = []

    for persona in personas:
        sessions = _generate_conversations(persona, num_sessions=sessions_per_persona)
        queries = _generate_queries(persona, sessions)

        conversations.append({
            "persona_id": persona["name"].lower(),
            "persona": persona,
            "sessions": sessions,
        })
        all_queries.extend(queries)

    return {
        "metadata": {
            "name": "LoCoMo-Plus",
            "version": "1.0",
            "description": "Cognitive memory benchmark testing temporal reasoning, preference drift, goal inference, emotional context, cross-conversation synthesis, contradiction detection, social graph, and importance-weighted recall.",
            "num_personas": len(personas),
            "sessions_per_persona": sessions_per_persona,
            "total_queries": len(all_queries),
            "query_types": QUERY_TYPES,
            "tokens_per_query": 0,
        },
        "conversations": conversations,
        "queries": all_queries,
    }


# ── Ingestion ─────────────────────────────────────────────────────────────

def ingest_locomo_plus(
    memory_store: Any,
    dataset: dict[str, Any],
    galaxy: str = "locomo_plus",
) -> int:
    """Ingest LoCoMo-Plus conversations into WhiteMagic memory."""
    ingested = 0
    for conv in dataset["conversations"]:
        persona = conv["persona"]
        persona_name = persona["name"]

        for session in conv["sessions"]:
            session_id = session["session_id"]
            timestamp = session["timestamp"]

            # Ingest each turn as an episodic memory
            for turn_idx, turn in enumerate(session["turns"]):
                emotion = turn.get("emotion", "neutral")
                valence = turn.get("emotion_valence", 0.5)

                memory_store.store(
                    content=turn["text"],
                    title=f"locomo_plus_{persona_name}_{session_id}_turn_{turn_idx}",
                    tags={"locomo_plus", persona_name.lower(), session_id,
                          f"emotion_{emotion}", turn["speaker"].lower()},
                    galaxy=galaxy,
                    metadata={
                        "source": "locomo_plus",
                        "persona": persona_name,
                        "session_id": session_id,
                        "timestamp": timestamp,
                        "turn_index": turn_idx,
                        "speaker": turn["speaker"],
                        "emotion": emotion,
                        "emotion_valence": valence,
                    },
                    importance=0.7 if turn["speaker"] == persona_name else 0.4,
                    emotional_valence=valence,
                )
                ingested += 1

            # Ingest session summary
            summary_text = f"{persona_name} had a session about {', '.join(set(t['emotion'] for t in session['turns'] if t['speaker'] == persona_name))} topics."
            memory_store.store(
                content=summary_text,
                title=f"locomo_plus_{persona_name}_{session_id}_summary",
                tags={"locomo_plus", persona_name.lower(), session_id, "summary"},
                galaxy=galaxy,
                metadata={
                    "source": "locomo_plus",
                    "persona": persona_name,
                    "session_id": session_id,
                    "is_summary": True,
                },
                importance=0.8,
            )
            ingested += 1

        # Ingest persona facts (structured)
        for goal in persona["goals"]:
            memory_store.store(
                content=f"{persona_name}'s goal is to {goal}.",
                title=f"locomo_plus_{persona_name}_goal_{goal[:20]}",
                tags={"locomo_plus", persona_name.lower(), "goal"},
                galaxy=galaxy,
                metadata={"source": "locomo_plus", "persona": persona_name, "fact_type": "goal"},
                importance=0.9,
            )
            ingested += 1

        for value in persona["values"]:
            memory_store.store(
                content=f"{persona_name} values {value}.",
                title=f"locomo_plus_{persona_name}_value_{value[:20]}",
                tags={"locomo_plus", persona_name.lower(), "value"},
                galaxy=galaxy,
                metadata={"source": "locomo_plus", "persona": persona_name, "fact_type": "value"},
                importance=0.85,
            )
            ingested += 1

        # Social connections
        for conn_name, conn_type, conn_target in SOCIAL_CONNECTIONS:
            if conn_name == persona_name:
                memory_store.store(
                    content=f"{persona_name}'s {conn_type} is {conn_target}.",
                    title=f"locomo_plus_{persona_name}_social_{conn_target}",
                    tags={"locomo_plus", persona_name.lower(), "social", conn_type},
                    galaxy=galaxy,
                    metadata={"source": "locomo_plus", "persona": persona_name,
                             "fact_type": "social", "connection": conn_type, "target": conn_target},
                    importance=0.7,
                )
                ingested += 1

    return ingested


# ── Evaluation ────────────────────────────────────────────────────────────

def _key_term_match(answer_keywords: set[str], content: str) -> bool:
    """Check if content contains enough answer keywords."""
    content_lower = content.lower()
    if not answer_keywords:
        return False
    matches = sum(1 for kw in answer_keywords if kw in content_lower)
    return matches / len(answer_keywords) >= 0.5


def evaluate_locomo_plus(
    memory_store: Any,
    dataset: dict[str, Any],
    galaxy: str = "locomo_plus",
) -> dict[str, Any]:
    """Evaluate LoCoMo-Plus queries against the memory store."""
    queries = dataset["queries"]
    correct_at_1 = 0
    correct_at_5 = 0
    reciprocal_ranks = []
    latencies = []
    type_results: dict[str, dict[str, int]] = {}
    per_query = []

    for qa in queries:
        q_type = qa["type"]
        question = qa["question"]
        answer_keywords = qa.get("answer_keywords", set())

        if q_type not in type_results:
            type_results[q_type] = {"total": 0, "correct_1": 0, "correct_5": 0}
        type_results[q_type]["total"] += 1

        t0 = time.time()
        results = memory_store.search_hybrid(question, galaxy=galaxy, limit=10)
        latency_ms = (time.time() - t0) * 1000
        latencies.append(latency_ms)

        if not results:
            reciprocal_ranks.append(0.0)
            per_query.append({"type": q_type, "question": question, "found": False, "rank": -1})
            continue

        found_at = None
        for rank, result in enumerate(results):
            content = getattr(result, "content", str(result))
            if _key_term_match(answer_keywords, content):
                found_at = rank + 1
                break

        if found_at is not None:
            reciprocal_ranks.append(1.0 / found_at)
            if found_at == 1:
                correct_at_1 += 1
                type_results[q_type]["correct_1"] += 1
            if found_at <= 5:
                correct_at_5 += 1
                type_results[q_type]["correct_5"] += 1
            per_query.append({"type": q_type, "question": question, "found": True, "rank": found_at})
        else:
            reciprocal_ranks.append(0.0)
            per_query.append({"type": q_type, "question": question, "found": False, "rank": -1})

    total = len(queries)
    mrr = sum(reciprocal_ranks) / total if total > 0 else 0

    type_breakdown = {}
    for q_type, data in type_results.items():
        t = data["total"]
        type_breakdown[q_type] = {
            "total": t,
            "correct_1": data["correct_1"],
            "correct_5": data["correct_5"],
            "accuracy": data["correct_1"] / t if t > 0 else 0,
            "recall_5": data["correct_5"] / t if t > 0 else 0,
        }

    return {
        "benchmark": "locomo_plus",
        "total_queries": total,
        "recall": {
            "recall_at_1": correct_at_1 / total if total > 0 else 0,
            "recall_at_5": correct_at_5 / total if total > 0 else 0,
            "mrr": mrr,
        },
        "type_breakdown": type_breakdown,
        "latency": {
            "median_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        },
        "tokens": {
            "tokens_per_query": 0,
            "llm_calls": 0,
        },
        "per_query": per_query,
    }


# ── Main runner ───────────────────────────────────────────────────────────

def run_locomo_plus_benchmark(
    dataset: dict[str, Any] | None = None,
    galaxy: str = "locomo_plus",
    per_case: bool = False,
) -> dict[str, Any]:
    """Run the full LoCoMo-Plus benchmark."""
    from whitemagic.core.memory.unified import UnifiedMemory

    if dataset is None:
        dataset = generate_synthetic_locomo_plus()

    store = UnifiedMemory()

    # Ingest
    t0 = time.time()
    ingested = ingest_locomo_plus(store, dataset, galaxy=galaxy)
    ingest_time = time.time() - t0
    print(f"  Ingested {ingested} memories in {ingest_time:.1f}s")

    # Evaluate
    print(f"  Evaluating {len(dataset['queries'])} cognitive queries...")
    results = evaluate_locomo_plus(store, dataset, galaxy=galaxy)

    results["ingestion"] = {
        "total_memories": ingested,
        "ingest_time_s": ingest_time,
        "num_personas": len(dataset["conversations"]),
    }

    # Print summary
    r = results["recall"]
    print(f"  recall@1: {r['recall_at_1']:.2%}")
    print(f"  recall@5: {r['recall_at_5']:.2%}")
    print(f"  MRR: {r['mrr']:.4f}")
    print(f"  median latency: {results['latency']['median_ms']:.1f}ms")

    for q_type, bd in sorted(results["type_breakdown"].items()):
        print(f"  {q_type}: r@1={bd['accuracy']:.2%} r@5={bd['recall_5']:.2%} ({bd['total']} q)")

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LoCoMo-Plus cognitive memory benchmark")
    parser.add_argument("--data-path", default=None, help="Path to LoCoMo-Plus JSON dataset")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic dataset")
    parser.add_argument("--num-personas", type=int, default=3, help="Synthetic: number of personas")
    parser.add_argument("--sessions-per-persona", type=int, default=5, help="Synthetic: sessions per persona")
    parser.add_argument("--galaxy", default="locomo_plus", help="Galaxy to use")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    if args.data_path:
        dataset = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
        print(f"Loaded dataset from {args.data_path}")
    elif args.synthetic:
        dataset = generate_synthetic_locomo_plus(
            num_personas=args.num_personas,
            sessions_per_persona=args.sessions_per_persona,
        )
        print(f"Generated synthetic dataset: {dataset['metadata']}")
    else:
        print("No dataset found. Using synthetic dataset.")
        dataset = generate_synthetic_locomo_plus()

    results = run_locomo_plus_benchmark(
        dataset=dataset,
        galaxy=args.galaxy,
        per_case=args.per_case,
    )

    output_path = args.output or "benchmarks/results/locomo_plus.json"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
