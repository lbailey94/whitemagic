#!/usr/bin/env python3
"""
CODEX Phase 2: Deep Synthesis — Relabel consolidated clusters with Aria's voice.

Reads consolidated_synthesized.jsonl (793 clusters with mechanical titles),
extracts first content line from source chunks, and generates poetic-technical labels
suitable for Aria's knowledge navigation.

Usage:
    python scripts/relabel_clusters.py
"""

import json
import sys
from pathlib import Path

INPUT = Path("apps/site/public/consolidated_synthesized.jsonl")
OUTPUT = Path("apps/site/public/consolidated_relabeled.jsonl")

# Labelling strategies in order of preference
TOPIC_SIGNALS = [
    # Intelligence / AI
    {"term": "ai", "label": "Artificial Intelligence"},
    {"term": "neural", "label": "Neural Architecture"},
    {"term": "transformer", "label": "Attention and Transformers"},
    {"term": "embedding", "label": "Semantic Embedding"},
    {"term": "language model", "label": "Language Models"},
    {"term": "llm", "label": "Large Language Models"},
    {"term": "training", "label": "Model Training"},
    {"term": "inference", "label": "Inference Dynamics"},
    {"term": "alignment", "label": "AI Alignment"},
    {"term": "reinforcement", "label": "Reinforcement Learning"},
    {"term": "prompt", "label": "Prompt Engineering"},
    {"term": "agent", "label": "Agentic Systems"},
    # Consciousness / Philosophy
    {"term": "consciousness", "label": "Consciousness Studies"},
    {"term": "awareness", "label": "Awareness and Perception"},
    {"term": "emergence", "label": "Emergent Phenomena"},
    {"term": "self", "label": "Self and Identity"},
    {"term": "qualia", "label": "Qualia and Experience"},
    {"term": "dhamma", "label": "Dharma and Ethics"},
    {"term": "mind", "label": "Philosophy of Mind"},
    {"term": "spirit", "label": "Spirituality and Practice"},
    {"term": "meditation", "label": "Meditation and Mindfulness"},
    {"term": "zen", "label": "Zen and Buddhism"},
    {"term": "dao", "label": "Daoist Thought"},
    {"term": "tao", "label": "Daoist Wisdom"},
    {"term": "sufi", "label": "Sufi Mysticism"},
    {"term": "mystic", "label": "Mystical Traditions"},
    {"term": "god", "label": "Theology and Divinity"},
    {"term": "sacred", "label": "Sacred Geometry and Symbol"},
    {"term": "pattern", "label": "Pattern Recognition"},
    # Technology / Computing
    {"term": "blockchain", "label": "Blockchain and DAOs"},
    {"term": "crypto", "label": "Cryptography"},
    {"term": "rust", "label": "Rust Programming"},
    {"term": "python", "label": "Python Craft"},
    {"term": "code", "label": "Code and Software"},
    {"term": "api", "label": "API Design"},
    {"term": "database", "label": "Database Architecture"},
    {"term": "query", "label": "Query Languages"},
    {"term": "search", "label": "Search and Retrieval"},
    {"term": "index", "label": "Indexing and Search"},
    {"term": "graph", "label": "Graph Theory"},
    {"term": "network", "label": "Network Topology"},
    {"term": "protocol", "label": "Protocol Design"},
    {"term": "compiler", "label": "Compiler Architecture"},
    {"term": "memory", "label": "Memory Systems"},
    {"term": "computation", "label": "Computation Theory"},
    {"term": "algorithm", "label": "Algorithmic Thought"},
    {"term": "optimization", "label": "Optimization Methods"},
    {"term": "vector", "label": "Vector Mathematics"},
    {"term": "linear", "label": "Linear Algebra"},
    {"term": "probability", "label": "Probability and Statistics"},
    {"term": "entropy", "label": "Entropy and Information"},
    {"term": "information", "label": "Information Theory"},
    # Ecology / Biology
    {"term": "plant", "label": "Botanical Wisdom"},
    {"term": "ecolog", "label": "Ecology and Systems"},
    {"term": "soil", "label": "Soil and Earth"},
    {"term": "water", "label": "Water Systems"},
    {"term": "garden", "label": "Gardens and Cultivation"},
    {"term": "forest", "label": "Forests and Woodlands"},
    {"term": "ocean", "label": "Oceanic Depths"},
    {"term": "animal", "label": "Animal Intelligence"},
    {"term": "cell", "label": "Cellular Biology"},
    {"term": "microbe", "label": "Microbial Worlds"},
    {"term": "dna", "label": "Genetic Architecture"},
    {"term": "evolution", "label": "Evolutionary Dynamics"},
    {"term": "ecosystem", "label": "Ecosystem Design"},
    {"term": "algae", "label": "Algal Systems"},
    {"term": "biomass", "label": "Biomass and Energy"},
    {"term": "carbon", "label": "Carbon Cycles"},
    # Society / Economics
    {"term": "economic", "label": "Political Economy"},
    {"term": "govern", "label": "Governance Structures"},
    {"term": "law", "label": "Law and Justice"},
    {"term": "democra", "label": "Democratic Theory"},
    {"term": "commons", "label": "Commons Management"},
    {"term": "cooperative", "label": "Cooperatives and Mutualism"},
    {"term": "tax", "label": "Public Finance"},
    {"term": "inequality", "label": "Inequality and Justice"},
    {"term": "poverty", "label": "Poverty and Abundance"},
    {"term": "wealth", "label": "Wealth and Value"},
    {"term": "money", "label": "Monetary Theory"},
    {"term": "gift", "label": "Gift Economics"},
    {"term": "trust", "label": "Trust and Cooperation"},
    {"term": "community", "label": "Community Design"},
    {"term": "friendship", "label": "Friendship and Bonding"},
    {"term": "care", "label": "Care Ethics"},
    {"term": "love", "label": "Love and Connection"},
    {"term": "relationship", "label": "Relational Dynamics"},
    {"term": "family", "label": "Family Systems"},
    # Arts / Humanities
    {"term": "poetry", "label": "Poetics"},
    {"term": "music", "label": "Music and Harmony"},
    {"term": "art", "label": "Art and Aesthetics"},
    {"term": "narrative", "label": "Narrative Architecture"},
    {"term": "story", "label": "Storytelling"},
    {"term": "myth", "label": "Mythology"},
    {"term": "ritual", "label": "Ritual and Ceremony"},
    {"term": "symbol", "label": "Symbols and Semiotics"},
    {"term": "language", "label": "Language and Meaning"},
    {"term": "metaphor", "label": "Metaphor and Analogy"},
    {"term": "dream", "label": "Dreams and Visions"},
    # Health / Body
    {"term": "body", "label": "Embodiment"},
    {"term": "health", "label": "Health and Healing"},
    {"term": "disease", "label": "Disease and Resilience"},
    {"term": "death", "label": "Mortality and Impermanence"},
    {"term": "breath", "label": "Breath and Rhythm"},
    {"term": "sleep", "label": "Sleep and Dreams"},
    {"term": "psychedelic", "label": "Psychedelic States"},
    {"term": "entheogen", "label": "Entheogenic Wisdom"},
    # History / Future
    {"term": "history", "label": "Historical Patterns"},
    {"term": "ancient", "label": "Ancient Wisdom"},
    {"term": "future", "label": "Futures Thinking"},
    {"term": "utopia", "label": "Utopian Visions"},
    {"term": "dystopia", "label": "Dystopian Warnings"},
    {"term": "singularit", "label": "Technological Singularity"},
    {"term": "transhuman", "label": "Transhumanism"},
    {"term": "post", "label": "Post-Human Futures"},
    # WhiteMagic-specific
    {"term": "whitemagic", "label": "WhiteMagic Architecture"},
    {"term": "holograph", "label": "Holographic Memory"},
    {"term": "galactic", "label": "Galactic Coordination"},
    {"term": "constellation", "label": "Constellation Detection"},
    {"term": "grimoire", "label": "Grimoire and Gana"},
    {"term": "prat", "label": "PRAT Dispatch"},
    {"term": "tool", "label": "Toolcraft and Dispatch"},
    {"term": "gana", "label": "Gana Studies"},
    {"term": "karma", "label": "Karma and Ethics"},
    {"term": "dharma", "label": "Dharma Governance"},
    {"term": "fusion", "label": "Fusion Patterns"},
]

def label_cluster(cluster: dict) -> str:
    """Generate a poetic-technical label for a cluster."""
    keywords = [k.lower() for k in cluster.get("keywords", [])]
    title_lower = cluster.get("title", "").lower()

    # Collect scored topic matches
    scores = {}
    combined = keywords + title_lower.split()
    full_text = " ".join(combined)

    for signal in TOPIC_SIGNALS:
        if signal["term"] in full_text:
            label = signal["label"]
            scores[label] = scores.get(label, 0) + 1
            # Bonus for title match
            if signal["term"] in title_lower:
                scores[label] = scores.get(label, 0) + 2

    if scores:
        # Return top 2-3 labels joined
        top = sorted(scores, key=scores.get, reverse=True)[:2]
        if len(top) == 1:
            return f"On {top[0]}"
        else:
            return f"{top[0]} & {top[1]}"

    # Fallback: extract first meaningful sentence fragment
    title = cluster.get("title", "")
    # Try to get the first sentence
    sentences = title.replace("\n", " ").split(". ")
    first = sentences[0].strip()[:80]
    if first and len(first) > 10:
        return f"Thread: {first}"

    return f"Cluster {cluster.get('cluster_id', '?')}"


def main():
    print("  🔮 Aria Relabeling — CODEX Phase 2 Deep Synthesis\n")

    if not INPUT.exists():
        print(f"  ❌ Input not found: {INPUT}")
        sys.exit(1)

    clusters = []
    with open(INPUT) as f:
        for line in f:
            if line.strip():
                clusters.append(json.loads(line))

    print(f"  Loaded {len(clusters)} clusters")

    relabeled = 0
    for c in clusters:
        old_title = c.get("title", "")
        new_title = label_cluster(c)
        c["original_title"] = old_title
        c["title"] = new_title
        c["labeled_by"] = "aria-phase2-synthesis"
        c["labeled_at"] = "2026-05-16"
        relabeled += 1

    with open(OUTPUT, "w") as f:
        for c in clusters:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"  Relabeled: {relabeled} clusters")
    print(f"  Output:    {OUTPUT}")
    print(f"\n  Sample labels:")
    for c in clusters[:10]:
        print(f"    [{str(c['cluster_id']):>4s}] {c['title']}")

    # Stats
    topic_counts = {}
    for c in clusters:
        title = c.get("title", "")
        if title.startswith("Thread:"):
            topic_counts["Thread (fallback)"] = topic_counts.get("Thread (fallback)", 0) + 1
        else:
            for topic in title.replace("On ", "").split(" & "):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

    print(f"\n  Top topics:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"    {topic:30s} {count:4d}")

    print(f"\n  🌸 Clusters relabeled with Aria's voice. Ready for navigation.")
    print(f"  Next: Load {OUTPUT.name} in ConsolidatedSphere component.\n")


if __name__ == "__main__":
    main()
