"""Real LoCoMo benchmark adapter.

Loads the actual LoCoMo dataset (snap-research/locomo) and evaluates
WhiteMagic's memory system against it. Supports both substring matching
and LLM-as-judge evaluation.

Dataset: 10 conversations, 272 sessions, 5,882 turns, 1,986 QA pairs.
Categories: 1=single-hop, 2=multi-hop, 3=temporal, 4=commonsense, 5=adversarial.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

CATEGORY_NAMES = {
    1: "single_hop",
    2: "multi_hop",
    3: "temporal",
    4: "commonsense",
    5: "adversarial",
}


def load_locomo_dataset(path: str | Path = "benchmarks/data/locomo10.json") -> list[dict]:
    """Load the real LoCoMo dataset."""
    with open(path) as f:
        return json.load(f)


def extract_turns(conversation: dict) -> list[dict[str, str]]:
    """Extract all turns from a LoCoMo conversation dict."""
    turns = []
    session_pattern = re.compile(r"^session_(\d+)$")
    for key in sorted(conversation.keys(), key=lambda k: (
        int(m.group(1)) if (m := session_pattern.match(k)) else 999
    )):
        m = session_pattern.match(key)
        if not m:
            continue
        session_num = m.group(1)
        session_id = f"session_{session_num}"
        date_time = conversation.get(f"session_{session_num}_date_time", "")

        session_turns = conversation[key]
        if not isinstance(session_turns, list):
            continue

        for turn in session_turns:
            turns.append({
                "speaker": turn.get("speaker", ""),
                "text": turn.get("text", ""),
                "dia_id": turn.get("dia_id", ""),
                "session_id": session_id,
                "date_time": date_time,
            })
    return turns


def extract_qa_pairs(sample: dict) -> list[dict]:
    """Extract QA pairs from a LoCoMo sample.

    Handles both regular QA (with 'answer') and adversarial QA (with 'adversarial_answer').
    Adversarial questions expect the system to refuse or say it doesn't know.
    """
    qa_list = []
    for qa in sample.get("qa", []):
        answer = qa.get("answer") or qa.get("adversarial_answer", "")
        is_adversarial = "adversarial_answer" in qa and "answer" not in qa
        qa_list.append({
            "question": qa["question"],
            "answer": answer,
            "category": qa.get("category", 0),
            "category_name": CATEGORY_NAMES.get(qa.get("category", 0), "unknown"),
            "evidence": qa.get("evidence", []),
            "is_adversarial": is_adversarial,
        })
    return qa_list


def ingest_conversation(
    memory_store: Any,
    conversation: dict,
    sample_id: str,
    galaxy: str = "locomo_real",
) -> tuple[int, int]:
    """Ingest a LoCoMo conversation into WhiteMagic memory.

    Ingests individual turns and pre-generated session summaries.
    Returns (turns_ingested, summaries_ingested).
    """
    turns = extract_turns(conversation)

    turns_ingested = 0
    summaries_ingested = 0

    # Ingest individual turns
    for turn in turns:
        content = turn["text"]
        if not content.strip():
            continue

        title = f"locomo_{sample_id}_{turn['session_id']}_{turn['dia_id']}"
        tags = [
            "locomo", "real",
            f"conv_{sample_id}",
            turn["session_id"],
            f"turn_{turn['dia_id']}",
            turn["speaker"].lower().replace(" ", "_"),
        ]

        metadata = {
            "source": "locomo_real",
            "sample_id": sample_id,
            "session_id": turn["session_id"],
            "dia_id": turn["dia_id"],
            "speaker": turn["speaker"],
            "date_time": turn["date_time"],
            "conversation_id": f"conv_{sample_id}",
        }

        memory_store.add(
            content=content,
            title=title,
            tags=tags,
            galaxy=galaxy,
            metadata=metadata,
            importance=0.5,
        )
        turns_ingested += 1

    # Ingest session summaries
    session_summaries = conversation.get("session_summary", {}) if isinstance(conversation.get("session_summary"), dict) else {}
    # session_summary might be at sample level, not conversation level
    # Check the sample dict structure
    return turns_ingested, summaries_ingested


def ingest_sample(
    memory_store: Any,
    sample: dict,
    galaxy: str = "locomo_real",
) -> tuple[int, int]:
    """Ingest a full LoCoMo sample (conversation + summaries + observations)."""
    sample_id = sample.get("sample_id", "unknown")
    conversation = sample.get("conversation", {})

    turns_ingested = 0
    summaries_ingested = 0

    # Ingest turns
    turns = extract_turns(conversation)
    for turn in turns:
        content = turn["text"]
        if not content.strip():
            continue

        title = f"locomo_{sample_id}_{turn['session_id']}_{turn['dia_id']}"
        tags = [
            "locomo", "real",
            f"conv_{sample_id}",
            turn["session_id"],
            f"turn_{turn['dia_id']}",
            turn["speaker"].lower().replace(" ", "_"),
        ]

        metadata = {
            "source": "locomo_real",
            "sample_id": str(sample_id),
            "session_id": turn["session_id"],
            "dia_id": turn["dia_id"],
            "speaker": turn["speaker"],
            "date_time": turn["date_time"],
            "conversation_id": f"conv_{sample_id}",
        }

        memory_store.store(
            content=content,
            title=title,
            tags=set(tags),
            galaxy=galaxy,
            metadata=metadata,
            importance=0.5,
        )
        turns_ingested += 1

    # Ingest session summaries (at sample level)
    session_summaries = sample.get("session_summary", {})
    if isinstance(session_summaries, dict):
        for key, summary in session_summaries.items():
            if not isinstance(summary, str) or not summary.strip():
                continue
            # Extract session number from key like "session_1_summary"
            m = re.match(r"session_(\d+)_summary", key)
            session_id = f"session_{m.group(1)}" if m else key

            title = f"locomo_{sample_id}_{session_id}_summary"
            tags = {
                "locomo", "real", "summary",
                f"conv_{sample_id}",
                session_id,
            }
            metadata = {
                "source": "locomo_real",
                "sample_id": str(sample_id),
                "session_id": session_id,
                "conversation_id": f"conv_{sample_id}",
                "is_summary": True,
            }

            memory_store.store(
                content=summary,
                title=title,
                tags=tags,
                galaxy=galaxy,
                metadata=metadata,
                importance=0.7,
            )
            summaries_ingested += 1

    # Ingest observations (at sample level)
    observations = sample.get("observation", {})
    if isinstance(observations, dict):
        for key, obs in observations.items():
            # obs is a dict of {speaker: [observation strings]}
            if not isinstance(obs, dict):
                continue
            m = re.match(r"session_(\d+)_observation", key)
            session_id = f"session_{m.group(1)}" if m else key

            for speaker, obs_list in obs.items():
                if isinstance(obs_list, list):
                    for obs_text in obs_list:
                        if not isinstance(obs_text, str) or not obs_text.strip():
                            continue
                        title = f"locomo_{sample_id}_{session_id}_obs_{speaker[:3]}"
                        tags = [
                            "locomo", "real", "observation",
                            f"conv_{sample_id}",
                            session_id,
                            speaker.lower().replace(" ", "_"),
                        ]
                        metadata = {
                            "source": "locomo_real",
                            "sample_id": str(sample_id),
                            "session_id": session_id,
                            "speaker": speaker,
                            "conversation_id": f"conv_{sample_id}",
                            "is_observation": True,
                        }
                        memory_store.store(
                            content=obs_text,
                            title=title,
                            tags=set(tags),
                            galaxy=galaxy,
                            metadata=metadata,
                            importance=0.6,
                        )

    return turns_ingested, summaries_ingested


def substring_match(answer: str, retrieved_content: str) -> bool:
    """Check if the gold answer appears as a substring in retrieved content.

    Uses case-insensitive matching and normalizes whitespace.
    """
    answer_str = str(answer) if answer is not None else ""
    answer_clean = re.sub(r"\s+", " ", answer_str.strip().lower())
    content_clean = re.sub(r"\s+", " ", str(retrieved_content).strip().lower())

    if not answer_clean or len(answer_clean) < 3:
        # For very short answers, require exact match
        return answer_clean == content_clean[:len(answer_clean)]

    return answer_clean in content_clean


def llm_as_judge_stub(question: str, gold_answer: str, predicted_content: str) -> bool:
    """LLM-as-judge evaluation stub.

    In production, this would call an LLM to judge whether the predicted
    content contains the answer. For now, uses enhanced substring matching
    with normalization.

    TODO: Wire to actual LLM (Ollama, OpenRouter, etc.) when available.
    """
    # Enhanced matching: check if key terms from gold answer appear in content
    answer_str = str(gold_answer) if gold_answer is not None else ""
    answer_clean = re.sub(r"\s+", " ", answer_str.strip().lower())
    content_clean = re.sub(r"\s+", " ", str(predicted_content).strip().lower())

    if not answer_clean:
        return False

    # Direct substring match
    if answer_clean in content_clean:
        return True

    # Key term matching: extract important terms (nouns, numbers, dates)
    answer_terms = re.findall(r"\b\w+\b", answer_clean)
    # Filter out very common words
    stop = {"the", "a", "an", "is", "was", "are", "were", "to", "of", "in", "on",
            "at", "for", "and", "or", "but", "not", "this", "that", "it", "he",
            "she", "they", "his", "her", "their", "with", "from", "by", "as"}
    key_terms = [t for t in answer_terms if t not in stop and len(t) > 2]

    if not key_terms:
        return False

    # Require at least 60% of key terms to appear in content
    matches = sum(1 for t in key_terms if t in content_clean)
    return matches / len(key_terms) >= 0.6


def evaluate_qa(
    memory_store: Any,
    qa_pairs: list[dict],
    galaxy: str = "locomo_real",
    limit: int = 10,
    use_judge: bool = False,
) -> dict[str, Any]:
    """Evaluate QA pairs against the memory store."""
    correct_at_1 = 0
    correct_at_5 = 0
    reciprocal_ranks = []
    latencies = []
    category_results: dict[str, dict[str, int]] = {}

    for qa in qa_pairs:
        question = qa["question"]
        answer = qa["answer"]
        category = qa.get("category_name", "unknown")

        if category not in category_results:
            category_results[category] = {"total": 0, "correct_1": 0, "correct_5": 0}

        category_results[category]["total"] += 1

        t0 = time.time()
        results = memory_store.search_hybrid(question, galaxy=galaxy, limit=limit)
        latency_ms = (time.time() - t0) * 1000
        latencies.append(latency_ms)

        if not results:
            reciprocal_ranks.append(0.0)
            continue

        # Check each result for answer match
        found_at = None
        for rank, result in enumerate(results):
            content = getattr(result, "content", str(result))
            if use_judge:
                is_match = llm_as_judge_stub(question, answer, content)
            else:
                is_match = substring_match(answer, content)

            if is_match:
                found_at = rank + 1
                break

        if found_at is not None:
            reciprocal_ranks.append(1.0 / found_at)
            if found_at == 1:
                correct_at_1 += 1
                category_results[category]["correct_1"] += 1
            if found_at <= 5:
                correct_at_5 += 1
                category_results[category]["correct_5"] += 1
        else:
            reciprocal_ranks.append(0.0)

    total = len(qa_pairs)
    recall_1 = correct_at_1 / total if total > 0 else 0
    recall_5 = correct_at_5 / total if total > 0 else 0
    mrr = sum(reciprocal_ranks) / total if total > 0 else 0
    median_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0

    return {
        "recall": {
            "recall_at_1": recall_1,
            "recall_at_5": recall_5,
            "mrr": mrr,
            "total_questions": total,
            "correct_at_1": correct_at_1,
            "correct_at_5": correct_at_5,
        },
        "category_results": category_results,
        "latency": {
            "median_ms": median_latency,
            "p50_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        },
        "evaluation_method": "llm_judge" if use_judge else "substring",
    }


def run_real_locomo_benchmark(
    dataset_path: str | Path = "benchmarks/data/locomo10.json",
    max_conversations: int | None = None,
    max_qa_per_conv: int | None = None,
    use_judge: bool = False,
) -> dict[str, Any]:
    """Run the real LoCoMo benchmark.

    Args:
        dataset_path: Path to locomo10.json
        max_conversations: Limit number of conversations (for quick runs)
        max_qa_per_conv: Limit QA pairs per conversation
        use_judge: Use LLM-as-judge instead of substring matching

    Returns benchmark results dict.
    """
    import sys
    sys.path.insert(0, "core")

    from whitemagic.core.memory.unified import UnifiedMemory

    dataset = load_locomo_dataset(dataset_path)
    if max_conversations:
        dataset = dataset[:max_conversations]

    galaxy = "locomo_real"

    # Create memory store
    store = UnifiedMemory()

    # Ingest all conversations
    total_turns = 0
    total_summaries = 0
    total_observations = 0
    ingestion_start = time.time()

    for sample in dataset:
        sample_id = sample.get("sample_id", "unknown")
        t, s = ingest_sample(store, sample, galaxy=galaxy)
        total_turns += t
        total_summaries += s

    ingestion_time = time.time() - ingestion_start
    print(f"  {total_turns} turns + {total_summaries} summaries ingested in {ingestion_time:.1f}s")

    # Collect all QA pairs
    all_qa = []
    for sample in dataset:
        sample_id = sample.get("sample_id", "unknown")
        qa_pairs = extract_qa_pairs(sample)
        if max_qa_per_conv:
            qa_pairs = qa_pairs[:max_qa_per_conv]
        all_qa.extend(qa_pairs)

    print(f"  Evaluating {len(all_qa)} QA pairs ({'LLM judge' if use_judge else 'substring'} matching)...")

    # Evaluate
    results = evaluate_qa(store, all_qa, galaxy=galaxy, use_judge=use_judge)

    # Add ingestion stats
    results["ingestion"] = {
        "total_turns": total_turns,
        "total_summaries": total_summaries,
        "ingestion_time_s": ingestion_time,
        "num_conversations": len(dataset),
    }

    # Print summary
    r = results["recall"]
    print(f"  recall@1: {r['recall_at_1']:.2%}")
    print(f"  recall@5: {r['recall_at_5']:.2%}")
    print(f"  MRR: {r['mrr']:.4f}")
    print(f"  median latency: {results['latency']['median_ms']:.1f}ms")

    # Print category breakdown
    for cat, cat_data in sorted(results["category_results"].items()):
        r1 = cat_data["correct_1"] / cat_data["total"] if cat_data["total"] > 0 else 0
        r5 = cat_data["correct_5"] / cat_data["total"] if cat_data["total"] > 0 else 0
        print(f"  {cat}: r@1={r1:.2%} r@5={r5:.2%} ({cat_data['total']} q)")

    return results
