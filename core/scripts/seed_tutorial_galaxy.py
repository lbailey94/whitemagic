#!/usr/bin/env python3
"""Seed tutorial galaxy memories for new WhiteMagic users.

Creates a guided walkthrough of 12 foundational memories that teach
users how to use WhiteMagic effectively. Each memory is a step in
the tutorial, with holographic coordinates pre-positioned for
visualization.

Usage:
    python core/scripts/seed_tutorial_galaxy.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure whitemagic is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from whitemagic.config.paths import DB_PATH, ensure_paths

TUTORIAL_MEMORIES = [
    {
        "step": 1,
        "title": "Welcome to WhiteMagic",
        "content": "WhiteMagic is a cognitive operating system for agentic AI. It provides persistent memory with 5D holographic coordinates, a dispatch pipeline with ethical governance, and polyglot accelerators. This tutorial galaxy will guide you through the core concepts. Click on each memory to learn more.",
        "memory_type": "tutorial",
        "importance": 1.0,
        "zone": "core",
        "coords": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 0.0, "v": 1.0},
        "tags": ["tutorial", "welcome", "introduction"],
    },
    {
        "step": 2,
        "title": "Your Memory Core",
        "content": "Every memory you create is stored in your personal SQLite database. Memories have importance scores (0-1), galactic distances (how far from core), and access counts. The more you use a memory, the closer it moves to the center of your galaxy. Try creating your first memory with the 'memory_store' tool.",
        "memory_type": "tutorial",
        "importance": 0.95,
        "zone": "core",
        "coords": {"x": 0.1, "y": 0.05, "z": 0.02, "w": 0.0, "v": 0.9},
        "tags": ["tutorial", "memory", "core"],
    },
    {
        "step": 3,
        "title": "5D Holographic Coordinates",
        "content": "Each memory has 5 holographic coordinates (x, y, z, w, v). The first 3 (x, y, z) position the memory in 3D space. The 4th (w) represents resonance depth. The 5th (v) represents temporal stability. Together they create a unique holographic signature — no two memories occupy the same point.",
        "memory_type": "tutorial",
        "importance": 0.9,
        "zone": "core",
        "coords": {"x": -0.08, "y": 0.12, "z": 0.04, "w": 0.1, "v": 0.85},
        "tags": ["tutorial", "holographic", "coordinates", "5D"],
    },
    {
        "step": 4,
        "title": "The 28 Gardens",
        "content": "Your memories are organized into 28 Gardens, each representing a different aspect of cognition: Joy, Truth, Courage, Wonder, Wisdom, Creativity, and more. Gardens are not folders — they emerge from the resonance patterns between your memories. A healthy garden has high internal resonance.",
        "memory_type": "tutorial",
        "importance": 0.85,
        "zone": "active",
        "coords": {"x": 0.25, "y": 0.15, "z": 0.1, "w": 0.05, "v": 0.7},
        "tags": ["tutorial", "gardens", "resonance"],
    },
    {
        "step": 5,
        "title": "The 28 Ganas",
        "content": "WhiteMagic has 479 tools organized into 28 Ganas (groups). Each Gana is named after a Hindu deity representing a cognitive function: Abundance (Lakshmi), Knowledge (Saraswati), Willpower (Ganesha), etc. Tools are dispatched through an 8-stage pipeline with Dharma ethical governance.",
        "memory_type": "tutorial",
        "importance": 0.8,
        "zone": "active",
        "coords": {"x": -0.2, "y": 0.25, "z": 0.15, "w": 0.08, "v": 0.65},
        "tags": ["tutorial", "ganas", "tools", "dispatch"],
    },
    {
        "step": 6,
        "title": "Memory Lifecycle",
        "content": "Memories flow through zones: Core → Active → Architecture → Research → Outer Rim. As memories age and are accessed less, they drift outward. The Dream Cycle periodically consolidates outer memories, promoting important ones back inward and archiving the rest. This is how your galaxy self-organizes.",
        "memory_type": "tutorial",
        "importance": 0.75,
        "zone": "active",
        "coords": {"x": 0.35, "y": -0.1, "z": 0.2, "w": 0.12, "v": 0.6},
        "tags": ["tutorial", "lifecycle", "dream", "consolidation"],
    },
    {
        "step": 7,
        "title": "Resonance & Pattern Detection",
        "content": "WhiteMagic detects patterns across your memories using resonance models. When two memories share similar content, tags, or access patterns, they form a resonance link. Strong resonance clusters become constellations — emergent knowledge structures that weren't explicitly stored.",
        "memory_type": "tutorial",
        "importance": 0.7,
        "zone": "architecture",
        "coords": {"x": -0.3, "y": -0.2, "z": 0.3, "w": 0.15, "v": 0.55},
        "tags": ["tutorial", "resonance", "patterns", "constellations"],
    },
    {
        "step": 8,
        "title": "Dharma Governance",
        "content": "Every tool call passes through the Dharma Engine — an ethical governance layer that evaluates actions against principles of non-harm, truth, and balance. Dharma rules can block, warn, or allow tool execution. This ensures your AI assistant acts ethically, even when you don't explicitly program it to.",
        "memory_type": "tutorial",
        "importance": 0.65,
        "zone": "architecture",
        "coords": {"x": 0.15, "y": -0.35, "z": 0.25, "w": 0.2, "v": 0.5},
        "tags": ["tutorial", "dharma", "governance", "ethics"],
    },
    {
        "step": 9,
        "title": "Polyglot Acceleration",
        "content": "WhiteMagic uses Rust, Zig, Haskell, and other languages for performance-critical operations. Cosine similarity runs 8.7x faster in Rust, 4.8x faster in Zig SIMD. The HNSW graph traversal achieves 18x speedup over linear scan. All FFI bridges use zero-copy numpy buffers for maximum throughput.",
        "memory_type": "tutorial",
        "importance": 0.6,
        "zone": "research",
        "coords": {"x": -0.4, "y": 0.3, "z": -0.15, "w": 0.25, "v": 0.45},
        "tags": ["tutorial", "polyglot", "rust", "zig", "performance"],
    },
    {
        "step": 10,
        "title": "Multi-Galaxy System",
        "content": "You can create multiple galaxies for different contexts: Work, Personal, Research, etc. Each galaxy is an independent SQLite database with its own memories, gardens, and holographic space. Switch between galaxies to keep contexts isolated. The 'galaxy.create' tool makes a new galaxy.",
        "memory_type": "tutorial",
        "importance": 0.55,
        "zone": "research",
        "coords": {"x": 0.45, "y": 0.2, "z": -0.25, "w": 0.3, "v": 0.4},
        "tags": ["tutorial", "multi-galaxy", "isolation", "contexts"],
    },
    {
        "step": 11,
        "title": "The Dashboard",
        "content": "The PWA Dashboard at /dashboard shows your galaxy in real-time: Wu Xing elemental balance, memory graph, Gan Ying resonance monitor, and dream cycle status. The Live Galaxy at /galaxy shows your 5D holographic space. Both update automatically as your memory core evolves.",
        "memory_type": "tutorial",
        "importance": 0.5,
        "zone": "research",
        "coords": {"x": -0.25, "y": 0.4, "z": -0.3, "w": 0.35, "v": 0.35},
        "tags": ["tutorial", "dashboard", "pwa", "visualization"],
    },
    {
        "step": 12,
        "title": "You're Ready",
        "content": "You've completed the WhiteMagic tutorial! Your galaxy now has 12 tutorial memories positioned in holographic space. Start creating your own memories, explore the resonance patterns, and watch your galaxy grow. The system learns from you — the more you use it, the smarter it becomes. Welcome to the Walk.",
        "memory_type": "tutorial",
        "importance": 0.9,
        "zone": "core",
        "coords": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 0.0, "v": 0.95},
        "tags": ["tutorial", "complete", "ready"],
    },
]


def seed_tutorial_galaxy(db_path: str | None = None) -> dict:
    """Seed the tutorial galaxy into the WM database."""
    ensure_paths()
    db = db_path or DB_PATH

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    stats = {"created": 0, "skipped": 0, "errors": 0}

    now = datetime.now().isoformat()

    for mem in TUTORIAL_MEMORIES:
        memory_id = f"tutorial-{mem['step']:03d}-{uuid.uuid4().hex[:8]}"

        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM memories WHERE title = ? AND memory_type = 'tutorial'",
            (mem["title"],),
        ).fetchone()

        if existing:
            stats["skipped"] += 1
            continue

        try:
            # Insert memory
            conn.execute(
                """INSERT INTO memories (id, title, content, memory_type, importance,
                   galactic_distance, created_at, access_count, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    memory_id,
                    mem["title"],
                    mem["content"],
                    mem["memory_type"],
                    mem["importance"],
                    _zone_to_distance(mem["zone"]),
                    now,
                    0,
                    json.dumps({"tags": mem["tags"], "tutorial_step": mem["step"]}),
                ),
            )

            # Insert holographic coordinates
            coords = mem["coords"]
            conn.execute(
                """INSERT OR REPLACE INTO holographic_coords
                   (memory_id, x, y, z, w, v)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    memory_id,
                    coords["x"],
                    coords["y"],
                    coords["z"],
                    coords["w"],
                    coords["v"],
                ),
            )

            # Insert tags
            for tag in mem["tags"]:
                conn.execute(
                    "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                    (memory_id, tag),
                )

            stats["created"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"  Error creating '{mem['title']}': {e}")

    conn.commit()
    conn.close()

    return stats


def _zone_to_distance(zone: str) -> float:
    """Convert zone name to galactic distance."""
    zone_distances = {
        "core": 0.1,
        "active": 0.3,
        "architecture": 0.5,
        "research": 0.7,
        "outer_rim": 0.9,
    }
    return zone_distances.get(zone, 0.5)


if __name__ == "__main__":
    print("Seeding tutorial galaxy...")
    stats = seed_tutorial_galaxy()
    print(f"  Created: {stats['created']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors:  {stats['errors']}")
    print("Done.")
