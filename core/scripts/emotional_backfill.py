#!/usr/bin/env python3
"""Batch backfill emotional_valence for existing memories.

Scans memories with zero/null emotional_valence and assigns a heuristic
valence based on content analysis. Focuses on semantically meaningful
content (user messages, AI responses, decisions, summaries) rather than
low-level system telemetry (CORTEX_STEP_TYPE_*).

Usage:
    python scripts/emotional_backfill.py [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from whitemagic.core.galactic import get_db_path  # noqa: E402

# Positive emotion keywords (mapped to valence weight)
POSITIVE_KEYWORDS: dict[str, float] = {
    "excellent": 0.8,
    "amazing": 0.8,
    "wonderful": 0.7,
    "great": 0.6,
    "thank": 0.6,
    "grateful": 0.7,
    "gratitude": 0.7,
    "love": 0.7,
    "joy": 0.8,
    "happy": 0.7,
    "excited": 0.7,
    "exciting": 0.7,
    "satisfied": 0.5,
    "satisfaction": 0.5,
    "accomplished": 0.6,
    "success": 0.6,
    "successful": 0.6,
    "complete": 0.4,
    "completed": 0.4,
    "done": 0.3,
    "working": 0.2,
    "progress": 0.4,
    "breakthrough": 0.8,
    "insight": 0.5,
    "inspired": 0.6,
    "beautiful": 0.6,
    "perfect": 0.7,
    "awesome": 0.7,
    "fantastic": 0.7,
    "brilliant": 0.7,
    "celebrate": 0.7,
    "achievement": 0.6,
    "resolved": 0.5,
    "fixed": 0.4,
    "implemented": 0.5,
    "shipped": 0.6,
    "passed": 0.5,
}

# Negative emotion keywords
NEGATIVE_KEYWORDS: dict[str, float] = {
    "error": -0.3,
    "fail": -0.5,
    "failed": -0.5,
    "failure": -0.5,
    "bug": -0.4,
    "broken": -0.5,
    "crash": -0.6,
    "frustrated": -0.6,
    "frustration": -0.6,
    "sad": -0.6,
    "angry": -0.7,
    "stuck": -0.4,
    "confused": -0.3,
    "confusing": -0.3,
    "difficult": -0.3,
    "problem": -0.3,
    "issue": -0.2,
    "wrong": -0.4,
    "missing": -0.2,
    "unavailable": -0.2,
    "unreachable": -0.3,
    "timeout": -0.3,
    "deprecated": -0.2,
    "warning": -0.2,
    "concern": -0.3,
    "worry": -0.4,
    "afraid": -0.5,
    "fear": -0.5,
    "uncertain": -0.3,
    "uncertainty": -0.3,
}

# Patterns that indicate system telemetry (skip these)
TELEMETRY_PATTERNS = [
    r"^\[CORTEX_STEP_TYPE_",
    r"^\[ai\] #\d+ (error|message)$",
    r"^Running command:",
    r"^Step \d+",
]

# Content roles that should get higher valence weighting
MEANINGFUL_TITLE_PATTERNS = [
    r"\[user\]",
    r"\[ai\].*(decision|summary|code_change|answer|question)",
    r"Session",
    r"CODEX",
]


def is_telemetry(title: str, content: str) -> bool:
    """Check if a memory is low-level system telemetry."""
    for pattern in TELEMETRY_PATTERNS:
        if re.match(pattern, title) or re.match(pattern, content[:50]):
            return True
    # Very short content with no semantic meaning
    if len(content.strip()) < 20:
        return True
    return False


def compute_valence(title: str, content: str) -> float:
    """Compute emotional valence from content using keyword analysis.

    Returns a value in [-1.0, 1.0].
    """
    text = (title + " " + content).lower()
    words = set(re.findall(r"\b\w+\b", text))

    valence = 0.0
    matches = 0

    for kw, weight in POSITIVE_KEYWORDS.items():
        if kw in words:
            valence += weight
            matches += 1

    for kw, weight in NEGATIVE_KEYWORDS.items():
        if kw in words:
            valence += weight
            matches += 1

    if matches == 0:
        # Neutral default for meaningful content
        return 0.1

    # Average and clamp
    valence = max(-1.0, min(1.0, valence / max(matches, 3)))
    return round(valence, 3)


def backfill(dry_run: bool = True, limit: int = 0) -> dict:
    """Run the emotional valence backfill.

    Args:
        dry_run: If True, only report what would change.
        limit: Max memories to process (0 = all).

    Returns:
        Summary dict with counts.
    """
    import sqlite3

    db = get_db_path()
    conn = sqlite3.connect(str(db))

    # Select zero-valence memories
    sql = (
        "SELECT id, title, content, memory_type FROM memories "
        "WHERE emotional_valence = 0.0 OR emotional_valence IS NULL"
    )
    if limit > 0:
        sql += f" LIMIT {limit}"

    rows = conn.execute(sql).fetchall()
    total = len(rows)

    skipped_telemetry = 0
    updated = 0
    valence_sum = 0.0
    valence_dist = {"positive": 0, "neutral": 0, "negative": 0}

    updates: list[tuple[float, str]] = []

    for row in rows:
        mem_id, title, content, mem_type = row
        title = title or ""
        content = content or ""

        if is_telemetry(title, content):
            skipped_telemetry += 1
            continue

        valence = compute_valence(title, content)
        updates.append((valence, mem_id))
        valence_sum += valence
        updated += 1

        if valence > 0.15:
            valence_dist["positive"] += 1
        elif valence < -0.15:
            valence_dist["negative"] += 1
        else:
            valence_dist["neutral"] += 1

    if not dry_run and updates:
        conn.executemany(
            "UPDATE memories SET emotional_valence = ? WHERE id = ?",
            updates,
        )
        conn.commit()

    conn.close()

    avg_valence = valence_sum / updated if updated > 0 else 0.0

    return {
        "total_scanned": total,
        "skipped_telemetry": skipped_telemetry,
        "updated": updated,
        "avg_valence": round(avg_valence, 3),
        "distribution": valence_dist,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill emotional valence")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't write")
    parser.add_argument("--limit", type=int, default=0, help="Max memories to process")
    args = parser.parse_args()

    print(f"Starting emotional backfill (dry_run={args.dry_run})...")
    result = backfill(dry_run=args.dry_run, limit=args.limit)

    print(f"\nResults:")
    print(f"  Total scanned:     {result['total_scanned']}")
    print(f"  Skipped telemetry: {result['skipped_telemetry']}")
    print(f"  Updated:           {result['updated']}")
    print(f"  Avg valence:       {result['avg_valence']}")
    print(f"  Distribution:      {result['distribution']}")

    if args.dry_run:
        print("\n(dry run — no changes written. Re-run without --dry-run to apply.)")
    else:
        print(f"\nApplied {result['updated']} valence updates.")


if __name__ == "__main__":
    main()
