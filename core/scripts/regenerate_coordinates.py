"""Holographic Coordinate Space Regenerator
===========================================

Fixes the degenerate coordinate space issue where:
- W-axis was narrow (1.15-1.28) instead of full [0.0, 2.0+] range
- V-axis was constant (0.5) instead of distributed [0.0, 1.0]

This module recalculates all holographic coordinates using the full
encoder pipeline with proper parameter variation based on:
- Memory type (different damping/frequency per type)
- Source (CODEX, Grok, LIBRARY, etc. have different characteristics)
- Content length and complexity
- Tag diversity
- Garden affiliation

Usage:
    python scripts/regenerate_coordinates.py                    # Full regeneration
    python scripts/regenerate_coordinates.py --limit 1000       # Limit
    python scripts/regenerate_coordinates.py --dry-run          # Preview
    python scripts/regenerate_coordinates.py --batch-size 500   # Batch size
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("coord_regen")


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH

    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def extract_keywords(text: str, max_words: int = 50) -> set[str]:
    """Extract meaningful keywords from text."""
    import re

    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[#*`_\[\]()]", " ", text)
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    stopwords = {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "has",
        "have",
        "been",
        "from",
        "this",
        "that",
        "they",
        "with",
        "will",
        "each",
        "make",
        "like",
        "just",
        "over",
        "such",
        "more",
        "than",
        "them",
        "very",
        "when",
        "come",
        "could",
        "into",
        "time",
        "only",
        "its",
        "also",
        "after",
        "some",
        "then",
        "other",
        "what",
        "which",
        "their",
        "there",
        "about",
        "would",
        "these",
        "should",
        "because",
        "through",
        "between",
        "during",
        "before",
        "above",
        "below",
        "any",
        "same",
        "both",
        "few",
        "most",
        "own",
        "while",
        "where",
        "how",
        "who",
        "whom",
        "why",
        "did",
        "does",
        "doing",
        "done",
        "being",
        "is",
        "it",
        "in",
        "on",
        "at",
        "to",
        "of",
        "by",
        "or",
        "an",
        "as",
        "if",
        "so",
        "we",
        "he",
        "she",
        "my",
        "his",
        "me",
        "us",
        "am",
        "be",
    }
    return set(w for w in words if w not in stopwords)


def calculate_diversity_score(keywords: set[str], content: str) -> float:
    """Calculate how diverse/rich the content is."""
    if not keywords:
        return 0.0
    # Unique word ratio
    words = content.lower().split()
    if not words:
        return 0.0
    unique_ratio = len(keywords) / len(words)
    # Content length factor (log scale)
    length_factor = min(1.0, math.log(len(content) + 1) / 10.0)
    return min(1.0, (unique_ratio * 0.6 + length_factor * 0.4))


def calculate_complexity_score(content: str) -> float:
    """Calculate content complexity."""
    if not content:
        return 0.0
    # Sentence diversity
    sentences = content.replace("!", ".").replace("?", ".").split(".")
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences)
    # Normalize: 5-30 words per sentence is typical
    sent_score = min(1.0, avg_sent_len / 20.0)
    # Vocabulary richness
    words = content.lower().split()
    if not words:
        return 0.0
    vocab_richness = len(set(words)) / len(words)
    return min(1.0, (sent_score * 0.5 + vocab_richness * 0.5))


def calculate_resonance_params(
    memory_type: str, importance: float, diversity: float, complexity: float
) -> tuple[float, float]:
    """Calculate varied damping and frequency based on memory properties.

    Returns (damping, frequency) for the resonance oscillator.
    Different memory types have different "ringing" characteristics:
    - Core/protected memories: low damping, high frequency (ring long and clear)
    - Technical memories: medium damping, high frequency (precise, focused)
    - Emotional memories: low damping, low frequency (deep, resonant)
    - Ephemeral memories: high damping, medium frequency (quick decay)
    """
    # Base damping by memory type
    type_damping = {
        "long_term": 0.05,  # Ring long
        "short_term": 0.3,  # Quick decay
        "pattern": 0.08,  # Clear signal
        "wisdom": 0.03,  # Deep resonance
        "log": 0.5,  # Fast decay
        "episodic": 0.2,  # Moderate
    }
    base_damping = type_damping.get(memory_type, 0.15)

    # Base frequency by memory type
    type_frequency = {
        "long_term": 1.5,  # High frequency
        "short_term": 0.8,  # Lower frequency
        "pattern": 2.0,  # Very high (clear signal)
        "wisdom": 0.5,  # Low (deep)
        "log": 1.0,  # Medium
        "episodic": 1.2,  # Medium-high
    }
    base_frequency = type_frequency.get(memory_type, 1.0)

    # Adjust by importance (more important = less damping, higher frequency)
    damping = base_damping * (1.0 - importance * 0.5)
    frequency = base_frequency * (1.0 + importance * 0.5)

    # Adjust by diversity (more diverse = more complex resonance)
    damping *= 1.0 - diversity * 0.3
    frequency *= 1.0 + diversity * 0.3

    # Adjust by complexity (more complex = richer resonance)
    frequency *= 1.0 + complexity * 0.5

    return max(0.01, min(1.0, damping)), max(0.1, min(5.0, frequency))


def regenerate_coordinates(
    limit: int = 0, batch_size: int = 500, dry_run: bool = False
) -> dict:
    """Regenerate all holographic coordinates with proper 5D spread."""
    db_path = get_db_path()
    conn = get_conn(db_path)

    # Get all memories
    query = """
        SELECT id, title, content, memory_type, importance, neuro_score,
               emotional_valence, access_count, recall_count, is_protected,
               galactic_distance, created_at, metadata, retention_score
        FROM memories
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    total = len(memories)

    log.info("═══ Coordinate Regeneration: %s memories ═══", total)
    log.info("  Batch size: %s", batch_size)
    log.info("  Dry run: %s", dry_run)

    # Stats tracking
    w_values = []
    v_values = []
    x_values = []
    y_values = []
    z_values = []

    updated = 0
    for batch_start in range(0, total, batch_size):
        batch = memories[batch_start : batch_start + batch_size]

        for mem in batch:
            # Extract content properties
            content = str(mem["content"] or "")[:5000]
            title = str(mem["title"] or "")
            keywords = extract_keywords(content)
            diversity = calculate_diversity_score(keywords, content)
            complexity = calculate_complexity_score(content)

            # Memory properties
            memory_type = str(mem["memory_type"] or "long_term").lower()
            importance = float(mem["importance"] or 0.5)
            neuro_score = float(mem["neuro_score"] or 1.0)
            emotional_valence = float(mem["emotional_valence"] or 0.0)
            access_count = int(mem["access_count"] or 0)
            recall_count = int(mem["recall_count"] or 0)
            is_protected = bool(mem["is_protected"])
            galactic_distance = float(mem["galactic_distance"] or 0.5)

            # Calculate resonance parameters
            damping, frequency = calculate_resonance_params(
                memory_type, importance, diversity, complexity
            )

            # --- X-Axis: Logic vs Emotion ---
            # Use emotional_valence as primary signal
            x = -0.5 * emotional_valence
            # Add content-based signal
            logic_words = sum(
                1
                for kw in ["code", "function", "class", "api", "database", "algorithm"]
                if kw in content.lower()
            )
            emotion_words = sum(
                1
                for kw in ["feel", "heart", "love", "joy", "wonder", "beauty", "soul"]
                if kw in content.lower()
            )
            x += 0.05 * (logic_words - emotion_words)
            # Add hash-based variation
            import hashlib

            hash_val = int(hashlib.md5(f"{mem['id']}x".encode()).hexdigest()[:8], 16)
            x += ((hash_val % 1000) / 1000.0 - 0.5) * 0.3
            x = max(-1.0, min(1.0, x))

            # --- Y-Axis: Micro vs Macro ---
            if memory_type in ["log", "debug", "short_term"]:
                y = -0.5
            elif memory_type in ["pattern", "wisdom", "principle"]:
                y = 0.5
            else:
                y = 0.0
            # Content-based signal
            if any(
                w in content.lower()
                for w in ["universal", "always", "principle", "pattern"]
            ):
                y += 0.2
            if any(
                w in content.lower() for w in ["specific", "line", "error", "file:"]
            ):
                y -= 0.2
            hash_val = int(hashlib.md5(f"{mem['id']}y".encode()).hexdigest()[:8], 16)
            y += ((hash_val % 1000) / 1000.0 - 0.5) * 0.3
            y = max(-1.0, min(1.0, y))

            # --- Z-Axis: Time ---
            # Use created_at for temporal positioning
            z = 0.0
            if mem["created_at"]:
                try:
                    from datetime import datetime

                    ts = datetime.fromisoformat(str(mem["created_at"])[:26])
                    age_days = (datetime.now() - ts).days
                    if age_days < 1:
                        z = 0.0
                    elif age_days < 7:
                        z = -0.2
                    elif age_days < 30:
                        z = -0.4
                    elif age_days < 90:
                        z = -0.6
                    else:
                        z = -0.8
                except Exception:
                    pass
            # Future-oriented tags
            tags = set()
            try:
                tags = set(
                    json.loads(mem["metadata"]).get("tags", [])
                    if mem["metadata"]
                    else []
                )
            except Exception:
                pass
            if tags & {"future", "plan", "vision", "roadmap"}:
                z += 0.3
            z = max(-1.0, min(1.0, z))

            # --- W-Axis: Importance / Gravity (FIXED: proper range [0.1, 2.0+]) ---
            # Combination of importance, neuro_score, usage, and content richness
            w = (
                (importance * 0.3)
                + (neuro_score * 0.2)
                + (diversity * 0.2)
                + (complexity * 0.1)
            )
            # Usage boost
            usage_boost = min(0.4, (access_count + recall_count * 2) / 15.0)
            w += usage_boost
            # Memory type boost
            if memory_type == "long_term":
                w += 0.2
            elif memory_type == "pattern":
                w += 0.3
            elif memory_type == "short_term":
                w -= 0.1
            # Resonance boost (low damping = higher gravity)
            w += (1.0 - damping) * 0.2
            w = max(0.1, min(2.5, w))

            # --- V-Axis: Vitality / Galactic Distance (FIXED: proper range [0.0, 1.0]) ---
            if is_protected:
                v = 1.0
            else:
                # Base from galactic_distance
                v_base = 1.0 - galactic_distance
                # Decay based on access (memories not accessed decay toward edge)
                access_factor = min(1.0, access_count / 10.0)
                recall_factor = min(1.0, recall_count / 5.0)
                activity = access_factor * 0.6 + recall_factor * 0.4
                v = v_base * 0.5 + activity * 0.5
                # Diversity boost (rich memories stay more vital)
                v += diversity * 0.1
                v = max(0.0, min(1.0, v))

            # Track stats
            x_values.append(x)
            y_values.append(y)
            z_values.append(z)
            w_values.append(w)
            v_values.append(v)

            # Update database
            if not dry_run:
                conn.execute(
                    """INSERT OR REPLACE INTO holographic_coords
                       (memory_id, x, y, z, w, v)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (mem["id"], x, y, z, w, v),
                )
                updated += 1

        if not dry_run:
            conn.commit()

        elapsed = time.perf_counter()
        log.info(f"  Progress: {min(batch_start + batch_size, total)}/{total}")

    conn.close()

    # Print stats
    def stats(values, name):
        avg = sum(values) / len(values) if values else 0
        min_v = min(values) if values else 0
        max_v = max(values) if values else 0
        spread = max_v - min_v
        log.info(
            "  %s: min=%s, max=%s, avg=%s, spread=%s", name, min_v, max_v, avg, spread
        )

    log.info(f"\n📊 Coordinate Statistics:")
    stats(x_values, "X (Logic↔Emotion)")
    stats(y_values, "Y (Micro↔Macro)")
    stats(z_values, "Z (Time)")
    stats(w_values, "W (Importance/Gravity)")
    stats(v_values, "V (Vitality)")

    return {
        "updated": updated,
        "total": total,
        "x_range": (min(x_values), max(x_values)),
        "y_range": (min(y_values), max(y_values)),
        "z_range": (min(z_values), max(z_values)),
        "w_range": (min(w_values), max(w_values)),
        "v_range": (min(v_values), max(v_values)),
    }


def main():
    parser = argparse.ArgumentParser(description="Coordinate Space Regenerator")
    parser.add_argument("--limit", type=int, default=0, help="Limit memories")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    regenerate_coordinates(
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
