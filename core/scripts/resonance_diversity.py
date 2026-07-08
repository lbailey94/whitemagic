"""Resonance Diversity Builder
=============================

Builds varied resonance parameters for all memories based on:
- Memory type (different damping/frequency characteristics)
- Garden affiliation (different resonance "flavors")
- Gana classification (different harmonic patterns)
- Content properties (complexity, diversity, emotional valence)

This creates a rich resonance landscape where different memories "ring" differently,
enabling more sophisticated pattern detection and constellation formation.

Usage:
    python scripts/resonance_diversity.py                    # Full build
    python scripts/resonance_diversity.py --limit 1000       # Limit
    python scripts/resonance_diversity.py --dry-run          # Preview
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sqlite3
import sys
from pathlib import Path
from whitemagic.core.memory.db_manager import safe_connect

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("resonance_diversity")


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH

    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = safe_connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


# Garden resonance profiles (damping, frequency, phase_offset)
GARDEN_PROFILES = {
    "core_garden": (0.05, 1.5, 0.0),  # Clear, sustained resonance
    "knowledge_garden": (0.1, 2.0, 0.0),  # High frequency, precise
    "wisdom_garden": (0.03, 0.8, 0.0),  # Deep, slow resonance
    "ephemeral_garden": (0.4, 1.0, 0.0),  # Quick decay
    "dream_garden": (0.08, 0.5, 0.5),  # Low frequency, phase-shifted
    "emotion_garden": (0.15, 0.6, 0.3),  # Moderate damping, emotional
    "code_garden": (0.12, 2.5, 0.0),  # High frequency, technical
    "research_garden": (0.07, 1.8, 0.0),  # Balanced, analytical
    "creative_garden": (0.06, 1.2, 0.4),  # Creative, flowing
    "system_garden": (0.04, 1.0, 0.0),  # System-level, stable
}

# Gana harmonic patterns
GANA_HARMONICS = {
    "Vasus": {"base_freq": 1.0, "harmonic": 2.0, "phase": 0.0},  # Material, grounded
    "Rudras": {
        "base_freq": 1.5,
        "harmonic": 3.0,
        "phase": 0.2,
    },  # Dynamic, transformative
    "Adityas": {
        "base_freq": 0.8,
        "harmonic": 1.5,
        "phase": 0.4,
    },  # Illuminating, cosmic
    "Maruts": {"base_freq": 2.0, "harmonic": 4.0, "phase": 0.1},  # Storm, energetic
    "Rakshasas": {"base_freq": 0.6, "harmonic": 1.2, "phase": 0.6},  # Shadow, deep
    "Yakshas": {"base_freq": 1.2, "harmonic": 2.5, "phase": 0.3},  # Nature, fertile
    "Gandharvas": {
        "base_freq": 1.8,
        "harmonic": 3.5,
        "phase": 0.5,
    },  # Musical, artistic
    "Apsaras": {"base_freq": 1.3, "harmonic": 2.8, "phase": 0.7},  # Graceful, fluid
}


def get_garden_for_memory(mem: sqlite3.Row) -> str:
    """Determine garden affiliation from memory metadata."""
    try:
        metadata = json.loads(mem["metadata"]) if mem["metadata"] else {}
    except Exception:
        metadata = {}

    # Direct garden field
    garden = metadata.get("garden", "")
    if garden:
        return garden

    # Infer from source/type
    source = str(metadata.get("source", "") or "").lower()
    source_file = str(metadata.get("source_file", "") or "").lower()
    category = str(metadata.get("category", "") or "").lower()
    tags = metadata.get("tags", [])
    memory_type = str(mem["memory_type"] or "").lower()

    # Source-based mapping
    if "codex" in source:
        return "knowledge_garden"
    elif "grok" in source:
        return "research_garden"
    elif "library" in source:
        return "knowledge_garden"
    elif "research" in source:
        return "research_garden"
    elif "project_docs" in source:
        return "system_garden"

    # Source file based
    if "grimoire" in source_file:
        return "wisdom_garden"
    elif "dream" in source_file:
        return "dream_garden"
    elif "emotion" in source_file or "feeling" in source_file:
        return "emotion_garden"
    elif "code" in source_file or "script" in source_file:
        return "code_garden"

    # Category based
    if "creative" in category or "art" in category:
        return "creative_garden"
    elif "technical" in category or "code" in category:
        return "code_garden"
    elif "wisdom" in category or "principle" in category:
        return "wisdom_garden"
    elif "dream" in category:
        return "dream_garden"

    # Tag based
    tag_set = set(str(t).lower() for t in tags)
    if tag_set & {"dream", "sleep", "vision"}:
        return "dream_garden"
    elif tag_set & {"emotion", "feeling", "mood"}:
        return "emotion_garden"
    elif tag_set & {"code", "function", "api", "algorithm"}:
        return "code_garden"
    elif tag_set & {"wisdom", "principle", "truth"}:
        return "wisdom_garden"
    elif tag_set & {"creative", "art", "music", "poetry"}:
        return "creative_garden"
    elif tag_set & {"research", "analysis", "study"}:
        return "research_garden"

    # Memory type fallback
    if memory_type in ["wisdom", "principle"]:
        return "wisdom_garden"
    elif memory_type in ["log", "debug"]:
        return "ephemeral_garden"
    elif memory_type in ["pattern"]:
        return "core_garden"
    elif memory_type in ["episodic"]:
        return "emotion_garden"
    else:
        return "core_garden"


def get_gana_for_memory(mem: sqlite3.Row) -> str:
    """Determine Gana classification from memory metadata."""
    try:
        metadata = json.loads(mem["metadata"]) if mem["metadata"] else {}
    except Exception:
        metadata = {}

    gana = metadata.get("gana", "")
    if gana:
        return gana

    # Infer from content properties
    content = str(mem["content"] or "").lower()
    importance = float(mem["importance"] or 0.5)
    emotional_valence = float(mem["emotional_valence"] or 0.0)

    if importance > 0.9:
        return "Adityas"  # High importance = cosmic
    elif emotional_valence > 0.5:
        return "Gandharvas"  # High emotion = artistic
    elif emotional_valence < -0.3:
        return "Rakshasas"  # Negative = shadow
    elif "code" in content or "function" in content:
        return "Vasus"  # Technical = material
    elif "pattern" in content or "system" in content:
        return "Rudras"  # Systemic = transformative
    elif "creative" in content or "design" in content:
        return "Apsaras"  # Creative = graceful
    else:
        return "Yakshas"  # Default = nature


def calculate_resonance_params(mem: sqlite3.Row) -> dict:
    """Calculate full resonance parameters for a memory."""
    content = str(mem["content"] or "")[:3000]
    memory_type = str(mem["memory_type"] or "long_term").lower()
    importance = float(mem["importance"] or 0.5)
    emotional_valence = float(mem["emotional_valence"] or 0.0)
    neuro_score = float(mem["neuro_score"] or 1.0)

    # Garden and Gana
    garden = get_garden_for_memory(mem)
    gana = get_gana_for_memory(mem)

    # Base from garden profile
    garden_damping, garden_freq, garden_phase = GARDEN_PROFILES.get(
        garden, (0.1, 1.0, 0.0)
    )

    # Gana harmonic modulation
    gana_profile = GANA_HARMONICS.get(
        gana, {"base_freq": 1.0, "harmonic": 2.0, "phase": 0.0}
    )
    gana_freq = gana_profile["base_freq"]
    gana_harmonic = gana_profile["harmonic"]
    gana_phase = gana_profile["phase"]

    # Content complexity
    words = content.split()
    unique_ratio = len(set(w.lower() for w in words)) / max(1, len(words))
    complexity = min(1.0, unique_ratio)

    # Emotional resonance
    emotion_factor = abs(emotional_valence)

    # Final damping (lower = longer ring)
    damping = garden_damping
    # Importance reduces damping (important memories ring longer)
    damping *= 1.0 - importance * 0.5
    # Complexity slightly increases damping (complex signals decay faster)
    damping *= 1.0 + complexity * 0.2
    # Emotion can increase or decrease damping based on valence
    if emotional_valence > 0:
        damping *= 1.0 - emotion_factor * 0.3  # Positive = longer ring
    else:
        damping *= 1.0 + emotion_factor * 0.2  # Negative = faster decay
    damping = max(0.01, min(1.0, damping))

    # Final frequency
    frequency = garden_freq * gana_freq
    # Importance increases frequency
    frequency *= 1.0 + importance * 0.5
    # Complexity adds harmonic richness
    frequency += gana_harmonic * complexity * 0.3
    frequency = max(0.1, min(5.0, frequency))

    phase = garden_phase + gana_phase
    phase += emotional_valence * 0.2  # Emotion shifts phase
    phase = phase % (2 * math.pi)

    # Amplitude (how strong the resonance is)
    amplitude = neuro_score * (0.5 + importance * 0.5)
    amplitude *= 1.0 + emotion_factor * 0.3
    amplitude = max(0.1, min(2.0, amplitude))

    # Quality factor (Q = frequency / (2 * damping))
    q_factor = frequency / (2 * damping) if damping > 0 else 100.0

    return {
        "damping": round(damping, 6),
        "frequency": round(frequency, 4),
        "phase": round(phase, 4),
        "amplitude": round(amplitude, 4),
        "q_factor": round(q_factor, 4),
        "garden": garden,
        "gana": gana,
        "garden_damping": garden_damping,
        "garden_freq": garden_freq,
        "gana_freq": gana_freq,
        "gana_harmonic": gana_harmonic,
    }


def build_resonance_diversity(limit: int = 0, dry_run: bool = False) -> dict:
    """Build resonance diversity for all memories."""
    db_path = get_db_path()
    conn = get_conn(db_path)

    query = """
        SELECT id, title, content, memory_type, importance, neuro_score,
               emotional_valence, metadata
        FROM memories
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    total = len(memories)

    log.info("═══ Resonance Diversity Build: %s memories ═══", total)

    # Stats tracking
    damping_values = []
    frequency_values = []
    q_values = []
    garden_counts = {}
    gana_counts = {}

    updated = 0
    for mem in memories:
        params = calculate_resonance_params(mem)

        damping_values.append(params["damping"])
        frequency_values.append(params["frequency"])
        q_values.append(params["q_factor"])

        garden = params["garden"]
        gana = params["gana"]
        garden_counts[garden] = garden_counts.get(garden, 0) + 1
        gana_counts[gana] = gana_counts.get(gana, 0) + 1

        if not dry_run:
            try:
                metadata = json.loads(mem["metadata"]) if mem["metadata"] else {}
            except Exception:
                metadata = {}

            metadata["resonance"] = {
                "damping": params["damping"],
                "frequency": params["frequency"],
                "phase": params["phase"],
                "amplitude": params["amplitude"],
                "q_factor": params["q_factor"],
                "garden": garden,
                "gana": gana,
            }

            conn.execute(
                "UPDATE memories SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), mem["id"]),
            )
            updated += 1

    if not dry_run:
        conn.commit()

    conn.close()

    # Stats
    def stats(values, name):
        avg = sum(values) / len(values) if values else 0
        min_v = min(values) if values else 0
        max_v = max(values) if values else 0
        log.info("  %s: min=%s, max=%s, avg=%s", name, min_v, max_v, avg)

    log.info(f"\n📊 Resonance Statistics:")
    stats(damping_values, "Damping")
    stats(frequency_values, "Frequency")
    stats(q_values, "Q Factor")

    log.info(f"\n🌿 Garden Distribution:")
    for garden, count in sorted(garden_counts.items(), key=lambda x: -x[1]):
        log.info("  %s: %s", garden, count)

    log.info(f"\n🔥 Gana Distribution:")
    for gana, count in sorted(gana_counts.items(), key=lambda x: -x[1]):
        log.info("  %s: %s", gana, count)

    return {
        "updated": updated,
        "total": total,
        "damping_range": (min(damping_values), max(damping_values)),
        "frequency_range": (min(frequency_values), max(frequency_values)),
        "garden_counts": garden_counts,
        "gana_counts": gana_counts,
    }


def main():
    parser = argparse.ArgumentParser(description="Resonance Diversity Builder")
    parser.add_argument("--limit", type=int, default=0, help="Limit memories")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    build_resonance_diversity(
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
