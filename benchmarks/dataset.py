"""Benchmark dataset — 1,000 memories with known semantic relationships.

Generates a deterministic dataset for reproducible benchmarking.
Uses a fixed seed for reproducibility.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

SEED = 42
NUM_MEMORIES = 1000

CATEGORIES = [
    "programming", "science", "history", "literature", "philosophy",
    "mathematics", "biology", "chemistry", "physics", "geography",
    "art", "music", "cooking", "sports", "technology",
    "business", "psychology", "medicine", "law", "education",
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
]


def generate_dataset(
    num_memories: int = NUM_MEMORIES,
    seed: int = SEED,
) -> list[dict[str, str]]:
    """Generate a deterministic dataset of memories.

    Returns list of dicts with keys: id, content, category, tags.
    """
    rng = random.Random(seed)
    memories = []

    for i in range(num_memories):
        cat = rng.choice(CATEGORIES)
        subj = rng.choice(SUBJECTS)
        detail = rng.choice(DETAILS)
        template = rng.choice(TEMPLATES)

        content = template.format(subject=subj, category=cat, detail=detail)
        tags = [cat, subj.split()[0]]

        memories.append({
            "id": f"mem_{i:04d}",
            "content": content,
            "category": cat,
            "tags": tags,
            "subject": subj,
        })

    return memories


def generate_queries(
    num_queries: int = 100,
    seed: int = SEED + 1,
    dataset_seed: int = SEED,
) -> list[dict[str, Any]]:
    """Generate test queries with label-based ground truth.

    Returns list of dicts with: id, query, relevance_labels, relevant_count.
    relevance_labels is a dict like {"subject": "entropy"} or
    {"category": "physics"} — any memory matching ALL labels is relevant.
    relevant_count is the total number of relevant memories (not capped).
    """
    rng = random.Random(seed)
    dataset = generate_dataset(seed=dataset_seed)

    # Build label → count index
    subject_counts: dict[str, int] = {}
    cat_counts: dict[str, int] = {}
    for m in dataset:
        subject_counts[m["subject"]] = subject_counts.get(m["subject"], 0) + 1
        cat_counts[m["category"]] = cat_counts.get(m["category"], 0) + 1

    queries = []
    query_templates = [
        ("Tell me about {subject}", "subject"),
        ("What is {subject}?", "subject"),
        ("Explain {subject} in {category}", "subject"),
        ("Research on {subject}", "subject"),
        ("{category} concepts", "category"),
    ]

    for i in range(num_queries):
        template, match_key = rng.choice(query_templates)
        if match_key == "subject":
            subj = rng.choice(SUBJECTS)
            query = template.format(subject=subj, category=rng.choice(CATEGORIES))
            relevance_labels = {"subject": subj}
            relevant_count = subject_counts.get(subj, 0)
        else:
            cat = rng.choice(CATEGORIES)
            query = template.format(category=cat, subject=rng.choice(SUBJECTS))
            relevance_labels = {"category": cat}
            relevant_count = cat_counts.get(cat, 0)

        if relevant_count == 0:
            continue

        queries.append({
            "id": f"q_{i:03d}",
            "query": query,
            "relevance_labels": relevance_labels,
            "relevant_count": relevant_count,
        })

    return queries


def save_dataset(output_dir: str | Path) -> None:
    """Save dataset and queries to JSON files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = generate_dataset()
    queries = generate_queries()

    (output_dir / "memories.json").write_text(
        json.dumps(dataset, indent=2), encoding="utf-8"
    )
    (output_dir / "queries.json").write_text(
        json.dumps(queries, indent=2), encoding="utf-8"
    )

    print(f"Generated {len(dataset)} memories and {len(queries)} queries in {output_dir}")


if __name__ == "__main__":
    save_dataset("benchmarks/data")
