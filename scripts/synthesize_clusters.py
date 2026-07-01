#!/usr/bin/env python3
"""
Phase 2 Local Synthesis — Generate titles and key concepts for CODEX clusters
without requiring an external API.

Reads consolidate_output.jsonl, extracts meaningful titles and keywords
from each cluster's merged content, and outputs consolidated_synthesized.jsonl.

Usage:
    python scripts/synthesize_clusters.py \
        --input apps/site/public/consolidate_output.jsonl \
        --output apps/site/public/consolidated_synthesized.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Stopwords to filter from keyword extraction
STOPWORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "and", "but", "or", "nor", "not", "so", "yet",
    "both", "either", "neither", "each", "every", "all", "any", "few",
    "more", "most", "other", "some", "such", "no", "only", "own", "same",
    "than", "too", "very", "just", "because", "about", "up", "out",
    "if", "then", "else", "when", "where", "why", "how", "which", "who",
    "whom", "this", "that", "these", "those", "it", "its", "he", "she",
    "they", "them", "their", "we", "us", "our", "my", "your", "his", "her",
    "i", "me", "you", "what", "one", "two", "also", "make", "like",
    "many", "much", "well", "way", "even", "new", "good", "know",
    "get", "see", "go", "come", "take", "think", "say", "use", "find",
    "give", "tell", "work", "seem", "feel", "try", "leave", "call",
    "keep", "let", "begin", "show", "hear", "play", "run", "move",
    "live", "believe", "hold", "bring", "happen", "write", "provide",
    "sit", "stand", "lose", "pay", "meet", "include", "continue",
    "set", "learn", "change", "lead", "understand", "watch", "follow",
    "stop", "create", "speak", "read", "allow", "add", "spend",
    "grow", "open", "walk", "win", "offer", "remember", "consider",
    "appear", "buy", "wait", "serve", "die", "send", "expect", "build",
    "stay", "fall", "cut", "reach", "remain", "suggest", "raise",
    "pass", "sell", "require", "report", "decide", "pull", "developed",
    "within", "however", "therefore", "although", "furthermore",
    "nevertheless", "meanwhile", "regardless", "consequently",
    "significant", "particularly", "approximately", "potentially",
    "additionally", "specifically", "effectively", "traditionally",
    "indeed", "actually", "basically", "certainly", "clearly",
    "definitely", "probably", "possibly", "generally", "usually",
    "often", "sometimes", "always", "never", "already", "still",
    "perhaps", "rather", "quite", "really", "almost", "enough",
    "far", "less", "little", "long", "made", "might", "much",
    "next", "nothing", "now", "once", "over", "part", "people",
    "place", "put", "said", "since", "something", "thing", "things",
    "think", "thought", "time", "world", "year", "years", "going",
    "got", "great", "look", "looked", "looking", "looks",
}

# Regexes
CHUNK_HEADER_RE = re.compile(r"^###\s*\[doc-[^\]]+\]\s*$")
SENTENCE_RE = re.compile(r"[A-Z][^.!?]+[.!?]")
WORD_RE = re.compile(r"\b[a-zA-Z]{3,}\b")


def clean_content(text: str) -> str:
    """Remove chunk headers and normalize text."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if CHUNK_HEADER_RE.match(line.strip()):
            continue
        cleaned.append(line)
    return " ".join(cleaned).strip()


def extract_title(text: str) -> str:
    """Extract the most representative title from cluster content."""
    sentences = SENTENCE_RE.findall(text)
    for s in sentences:
        words = s.split()
        if len(words) >= 8:
            title = s.strip().rstrip(".")
            if len(title) > 120:
                title = title[:117] + "..."
            return title

    # Fallback: first 120 chars of cleaned text
    fallback = text[:120].strip()
    if len(fallback) > 117:
        fallback = fallback[:117] + "..."
    return fallback if fallback else "Untitled Cluster"


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Extract top keywords from text via word frequency."""
    words = [w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS]
    counter = Counter(words)
    return [word for word, _ in counter.most_common(top_n)]


def synthesize(input_path: Path, output_path: Path) -> None:
    """Read consolidate_output.jsonl, synthesize titles/keywords, write output."""
    synthesized: list[dict] = []
    total = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                node = json.loads(line)
            except json.JSONDecodeError:
                continue

            content = clean_content(node.get("content", ""))
            if not content:
                continue

            title = extract_title(content)
            keywords = extract_keywords(content)

            synthesized.append(
                {
                    "id": node.get("id", ""),
                    "cluster_id": node.get("cluster_id", ""),
                    "title": title,
                    "keywords": keywords,
                    "token_count": node.get("token_count", 0),
                    "source_chunks": node.get("source_chunks", []),
                    "sources": node.get("sources", []),
                    "average_similarity": node.get("average_similarity", 0.0),
                }
            )
            total += 1

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in synthesized:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Synthesized {total} clusters → {output_path}")

    print("\nSample titles:")
    for entry in synthesized[:10]:
        print(f"  [{entry['cluster_id']}] {entry['title'][:100]}")
        if entry["keywords"]:
            print(f"    Keywords: {', '.join(entry['keywords'][:5])}")

    if total > 10:
        print(f"  ... and {total - 10} more")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CODEX Phase 2 — Local cluster synthesis"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to consolidate_output.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for consolidated_synthesized.jsonl",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    synthesize(args.input, args.output)


if __name__ == "__main__":
    main()
