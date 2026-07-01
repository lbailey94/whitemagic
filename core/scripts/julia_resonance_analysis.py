#!/usr/bin/env python3
"""Julia Resonance Analysis — Memory Core Resonance Scan
========================================================

Runs the Julia-inspired resonance systems across the memory core:
  1. Single memory resonance calculations (damped harmonic oscillator)
  2. Causal resonance verification (coupled oscillators)
  3. Holographic neighbor search (KD-tree spatial proximity)
  4. Build holographic proximity associations

Usage:
    python scripts/julia_resonance_analysis.py                    # Full analysis
    python scripts/julia_resonance_analysis.py --mode resonance   # Resonance only
    python scripts/julia_resonance_analysis.py --mode causal      # Causal only
    python scripts/julia_resonance_analysis.py --mode neighbors   # Neighbors only
    python scripts/julia_resonance_analysis.py --mode build       # Build associations
    python scripts/julia_resonance_analysis.py --limit 100        # Limit memories
    python scripts/julia_resonance_analysis.py --dry-run          # Preview only
"""

from __future__ import annotations

import argparse
import logging
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
log = logging.getLogger("julia_resonance")


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH

    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def run_resonance_analysis(limit: int = 0) -> dict:
    """Calculate resonance for memories."""
    from whitemagic.core.resonance.julia_resonance import get_resonance_engine

    engine = get_resonance_engine()
    db_path = get_db_path()
    conn = get_conn(db_path)

    query = """
        SELECT id, importance, access_count, emotional_valence
        FROM memories
        WHERE is_protected = 0
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"═══ Resonance Analysis: {len(memories)} memories ═══")

    results = []
    for i, mem in enumerate(memories):
        result = engine.calculate_resonance(
            memory_id=mem["id"],
            importance=mem["importance"] or 0.5,
            access_count=mem["access_count"] or 0,
            emotional_valence=mem["emotional_valence"] or 0.0,
        )
        results.append(result)

        if (i + 1) % 100 == 0:
            log.info(f"  Progress: {i + 1}/{len(memories)}")

    conn.close()

    # Stats
    avg_resonance = (
        sum(r.total_resonance for r in results) / len(results) if results else 0
    )
    avg_half_life = sum(r.half_life for r in results) / len(results) if results else 0
    avg_peak = sum(r.peak_amplitude for r in results) / len(results) if results else 0

    log.info(f"\n📊 Resonance Statistics:")
    log.info(f"  Average total resonance: {avg_resonance:.4f}")
    log.info(f"  Average half-life: {avg_half_life:.4f}")
    log.info(f"  Average peak amplitude: {avg_peak:.4f}")

    # Top 5 most resonant
    top5 = sorted(results, key=lambda r: r.total_resonance, reverse=True)[:5]
    log.info(f"\n  Top 5 Most Resonant Memories:")
    for r in top5:
        log.info(
            f"    {r.memory_id[:20]}... resonance={r.total_resonance:.4f}, half_life={r.half_life:.4f}"
        )

    return {
        "memories_analyzed": len(results),
        "avg_resonance": avg_resonance,
        "avg_half_life": avg_half_life,
        "avg_peak_amplitude": avg_peak,
    }


def run_causal_verification(limit: int = 0) -> dict:
    """Verify causal links using coupled oscillators."""
    from whitemagic.core.resonance.julia_resonance import get_resonance_engine

    engine = get_resonance_engine()

    log.info("═══ Causal Resonance Verification ═══")

    result = engine.verify_association_resonance(
        association_type="semantic_overlap",
        min_strength=0.2,
        limit=limit if limit > 0 else 200,
    )

    log.info(f"\n📊 Causal Verification Statistics:")
    log.info(
        f"  Associations verified: {result['associations_verified']}/{result['total_associations']}"
    )
    log.info(f"  Total nodes: {result['total_nodes']}")
    log.info(f"  Total energy: {result['total_energy']:.4f}")

    return result


def run_neighbor_analysis(limit: int = 0) -> dict:
    """Find spatial neighbors for memories."""
    from whitemagic.core.resonance.julia_resonance import get_resonance_engine

    engine = get_resonance_engine()
    db_path = get_db_path()
    conn = get_conn(db_path)

    query = """
        SELECT id FROM memories
        WHERE is_protected = 0
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"═══ Neighbor Analysis: {len(memories)} memories ═══")

    total_neighbors = 0
    max_neighbors = 0
    max_neighbors_mem = ""

    for i, mem in enumerate(memories):
        neighbors = engine.find_neighbors(mem["id"], radius=0.3)
        total_neighbors += neighbors.count

        if neighbors.count > max_neighbors:
            max_neighbors = neighbors.count
            max_neighbors_mem = mem["id"]

        if (i + 1) % 100 == 0:
            log.info(
                f"  Progress: {i + 1}/{len(memories)} (avg neighbors: {total_neighbors / (i + 1):.1f})"
            )

    conn.close()

    avg_neighbors = total_neighbors / len(memories) if memories else 0

    log.info(f"\n📊 Neighbor Statistics:")
    log.info(f"  Average neighbors per memory: {avg_neighbors:.1f}")
    log.info(f"  Max neighbors: {max_neighbors} ({max_neighbors_mem[:20]}...)")
    log.info(f"  Total neighbor relationships: {total_neighbors}")

    return {
        "memories_analyzed": len(memories),
        "avg_neighbors": avg_neighbors,
        "max_neighbors": max_neighbors,
        "total_relationships": total_neighbors,
    }


def run_build_associations(
    radius: float = 0.2, limit: int = 5000, dry_run: bool = False
) -> dict:
    """Build holographic proximity associations."""
    from whitemagic.core.resonance.julia_resonance import get_resonance_engine

    engine = get_resonance_engine()

    log.info(f"═══ Building Holographic Associations ═══")
    log.info(f"  Radius: {radius}")
    log.info(f"  Limit: {limit}")
    log.info(f"  Dry run: {dry_run}")

    result = engine.build_holographic_associations(
        radius=radius,
        min_strength=0.1,
        limit=limit,
        dry_run=dry_run,
    )

    log.info(f"\n📊 Association Building Results:")
    log.info(f"  Created: {result.get('associations_created', 0)}")
    log.info(f"  Skipped: {result.get('associations_skipped', 0)}")

    return result


def print_final_stats():
    """Print final database statistics."""
    db_path = get_db_path()
    conn = get_conn(db_path)

    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    total_assoc = conn.execute("SELECT COUNT(*) FROM associations").fetchone()[0]
    total_embed = conn.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0]
    total_coords = conn.execute("SELECT COUNT(*) FROM holographic_coords").fetchone()[0]

    # Association type distribution
    types = conn.execute("""
        SELECT association_type, COUNT(*) as cnt
        FROM associations
        GROUP BY association_type
        ORDER BY cnt DESC
    """).fetchall()

    log.info("\n" + "=" * 60)
    log.info("📊 Final Database Statistics")
    log.info("=" * 60)
    log.info(f"  Memories:      {total:,}")
    log.info(f"  Associations:  {total_assoc:,}")
    log.info(f"  Embeddings:    {total_embed:,}")
    log.info(f"  Holo Coords:   {total_coords:,}")

    log.info("\n  Association Types:")
    for row in types:
        log.info(f"    {row['association_type']}: {row['cnt']:,}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Julia Resonance Analysis")
    parser.add_argument(
        "--mode",
        choices=["resonance", "causal", "neighbors", "build", "all"],
        default="all",
        help="Analysis mode",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit memories")
    parser.add_argument(
        "--radius", type=float, default=0.2, help="Neighbor search radius"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    log.info(f"🌙 Julia Resonance Analysis")
    log.info(f"   Mode: {args.mode}")
    log.info(f"   Limit: {args.limit or 'unlimited'}")
    log.info(f"   Radius: {args.radius}")
    log.info(f"   Dry run: {args.dry_run}")

    total_start = time.perf_counter()
    results = {}

    if args.mode in ("resonance", "all"):
        results["resonance"] = run_resonance_analysis(
            limit=args.limit if args.limit > 0 else 200
        )

    if args.mode in ("causal", "all"):
        results["causal"] = run_causal_verification(
            limit=args.limit if args.limit > 0 else 200
        )

    if args.mode in ("neighbors", "all"):
        results["neighbors"] = run_neighbor_analysis(
            limit=args.limit if args.limit > 0 else 200
        )

    if args.mode in ("build", "all"):
        results["build"] = run_build_associations(
            radius=args.radius,
            limit=args.limit if args.limit > 0 else 5000,
            dry_run=args.dry_run,
        )

    total_elapsed = time.perf_counter() - total_start
    print_final_stats()

    log.info(f"\n⏱  Total time: {total_elapsed:.1f}s")
    log.info(f"\n✅ Julia resonance analysis complete!")


if __name__ == "__main__":
    main()
