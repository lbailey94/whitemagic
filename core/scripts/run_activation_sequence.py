#!/usr/bin/env python3
"""
WhiteMagic v15.7 — Full Activation Sequence
=============================================

Runs ALL engines across the rehydrated 111K+ memory corpus:
  1. Galactic Sweep (retention scoring + zone assignment)
  2. Association Mining (keyword Jaccard + optional semantic)
  3. Constellation Detection (HDBSCAN/grid clustering)
  4. Graph Topology Build + Bridge Discovery
  5. Dream Cycle (single pass)
  6. Harmony Vector Assessment
  7. System-wide stats report

Usage:
    python scripts/run_activation_sequence.py              # Full sequence
    python scripts/run_activation_sequence.py --quick       # Skip slow ops (dream, semantic mining)
    python scripts/run_activation_sequence.py --step sweep  # Single step only
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("activation")

REPORT_PATH = (
    ROOT / "reports" / f"activation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)


def step_db_stats():
    """Step 0: Current database statistics."""
    logger.debug("\n" + "=" * 70)
    logger.debug("📊 STEP 0: DATABASE STATISTICS")
    logger.debug("=" * 70)

    from whitemagic.core.memory.unified import get_unified_memory

    um = get_unified_memory()
    stats = um.get_stats()
    logger.debug(f"  Memories: {stats.get('total_memories', '?'):,}")
    logger.debug(f"  DB size: {stats.get('db_size_kb', 0) / 1024:.1f} MB")

    with um.backend.pool.connection() as conn:
        assoc_count = conn.execute("SELECT COUNT(*) FROM associations").fetchone()[0]
        typed_count = conn.execute(
            "SELECT COUNT(*) FROM associations WHERE relation_type != 'associated_with'"
        ).fetchone()[0]
        holo_count = conn.execute("SELECT COUNT(*) FROM holographic_coords").fetchone()[
            0
        ]
        embed_count = conn.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[
            0
        ]
        tag_count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        constellation_count = conn.execute(
            "SELECT COUNT(*) FROM constellation_membership"
        ).fetchone()[0]

    logger.debug(f"  Associations: {assoc_count:,} ({typed_count:,} typed)")
    logger.debug(f"  Holographic coords: {holo_count:,}")
    logger.debug(f"  Embeddings: {embed_count:,}")
    logger.debug(f"  Tags: {tag_count:,}")
    logger.debug(f"  Constellation memberships: {constellation_count:,}")

    return {
        "memories": stats.get("total_memories", 0),
        "associations": assoc_count,
        "typed_associations": typed_count,
        "holographic_coords": holo_count,
        "embeddings": embed_count,
        "tags": tag_count,
        "constellation_memberships": constellation_count,
        "db_size_mb": round(stats.get("db_size_kb", 0) / 1024, 1),
    }


def step_galactic_sweep():
    """Step 1: Galactic Sweep — retention scoring + zone assignment."""
    logger.debug("\n" + "=" * 70)
    logger.debug("🌌 STEP 1: GALACTIC SWEEP")
    logger.debug("=" * 70)

    from whitemagic.core.memory.galactic_map import get_galactic_map

    gmap = get_galactic_map()

    start = time.perf_counter()
    report = gmap.full_sweep(batch_size=1000)
    elapsed = time.perf_counter() - start

    logger.debug(f"  Memories mapped: {report.memories_updated}/{report.total_memories}")
    logger.debug(f"  Duration: {elapsed:.1f}s")
    logger.debug(f"  Zone distribution:")
    n = max(report.total_memories, 1)
    for zone_name, count in report.zone_counts.items():
        pct = count / n * 100
        bar = "█" * int(pct / 2)
        logger.debug(f"    {zone_name:>12}: {count:5,d} ({pct:5.1f}%) {bar}")

    logger.debug(
        f"  Core: {report.core_count:,}  |  Far Edge: {report.edge_count:,}  |  Protected: {report.protected_count:,}"
    )
    logger.debug(
        f"  Avg retention: {report.avg_retention:.4f}  |  Avg distance: {report.avg_distance:.4f}"
    )

    return report.to_dict()


def step_association_mining(quick=False):
    """Step 2: Association Mining — discover new semantic connections."""
    logger.debug("\n" + "=" * 70)
    logger.debug("🔗 STEP 2: ASSOCIATION MINING")
    logger.debug("=" * 70)

    from whitemagic.core.memory.miners import get_association_miner

    miner = get_association_miner(max_proposals=100, persist=True)

    # Keyword-based mining
    logger.debug("  [2a] Keyword Jaccard mining...")
    start = time.perf_counter()
    report_kw = miner.mine(sample_size=300)
    elapsed_kw = time.perf_counter() - start
    logger.debug(f"    Sampled: {report_kw.memories_sampled}")
    logger.debug(f"    Pairs evaluated: {report_kw.pairs_evaluated:,}")
    logger.debug(f"    Links proposed: {report_kw.links_proposed}")
    logger.debug(f"    Links created: {report_kw.links_created}")
    logger.debug(f"    Duration: {elapsed_kw:.1f}s")

    result = {
        "keyword_mining": {
            "sampled": report_kw.memories_sampled,
            "pairs_evaluated": report_kw.pairs_evaluated,
            "links_proposed": report_kw.links_proposed,
            "links_created": report_kw.links_created,
            "duration_ms": report_kw.duration_ms,
        }
    }

    # Semantic mining (slower, skip in quick mode)
    if not quick:
        logger.debug("  [2b] Semantic embedding mining...")
        start = time.perf_counter()
        report_sem = miner.mine_semantic(
            min_similarity=0.50,
            strong_threshold=0.70,
            max_proposals=50,
            persist=True,
        )
        elapsed_sem = time.perf_counter() - start
        logger.debug(f"    Pairs evaluated: {report_sem.pairs_evaluated:,}")
        logger.debug(f"    Links proposed: {report_sem.links_proposed}")
        logger.debug(f"    Links created: {report_sem.links_created}")
        logger.debug(f"    Duration: {elapsed_sem:.1f}s")
        result["semantic_mining"] = {
            "pairs_evaluated": report_sem.pairs_evaluated,
            "links_proposed": report_sem.links_proposed,
            "links_created": report_sem.links_created,
            "duration_ms": report_sem.duration_ms,
        }

    return result


def step_constellation_detection():
    """Step 3: Constellation Detection — HDBSCAN clustering in 5D space."""
    logger.debug("\n" + "=" * 70)
    logger.debug("✨ STEP 3: CONSTELLATION DETECTION")
    logger.debug("=" * 70)

    from whitemagic.core.memory.constellations import get_constellation_detector

    detector = get_constellation_detector()

    start = time.perf_counter()
    report = detector.detect(sample_limit=50000)
    elapsed = time.perf_counter() - start

    logger.debug(f"  Algorithm: {report.algorithm}")
    logger.debug(f"  Memories scanned: {report.memories_scanned:,}")
    logger.debug(f"  Constellations found: {report.constellations_found}")
    logger.debug(f"  Largest constellation: {report.largest_constellation} members")
    logger.debug(f"  Duration: {elapsed:.1f}s")

    if report.constellations:
        logger.debug(f"\n  Top constellations:")
        for c in report.constellations[:10]:
            logger.debug(
                f"    🌟 {c.name} ({len(c.member_ids)} members, zone={c.zone}, stability={c.stability:.2f})"
            )
            if c.dominant_tags:
                logger.debug(f"       tags: {', '.join(c.dominant_tags[:5])}")

    # Drift analysis
    try:
        drift = detector.analyze_drift()
        if drift and drift.get("tracked_constellations"):
            logger.debug(
                f"\n  Drift analysis: {drift['tracked_constellations']} constellations tracked"
            )
            logger.debug(f"    Avg drift: {drift.get('avg_drift_distance', 0):.4f}")
    except Exception:
        pass

    return report.to_dict()


def step_graph_topology():
    """Step 4: Graph Topology — build graph, compute centrality, find bridges."""
    logger.debug("\n" + "=" * 70)
    logger.debug("🕸️ STEP 4: GRAPH TOPOLOGY ANALYSIS")
    logger.debug("=" * 70)

    from whitemagic.core.memory.graph import get_graph_engine

    engine = get_graph_engine()

    logger.debug("  Rebuilding graph...")
    start = time.perf_counter()
    engine.rebuild(sample_limit=20000)
    elapsed = time.perf_counter() - start
    logger.debug(f"  Graph built in {elapsed:.1f}s")

    # Stats
    stats = engine.get_stats()
    logger.debug(f"  Nodes: {stats.get('nodes', 0):,}")
    logger.debug(f"  Edges: {stats.get('edges', 0):,}")
    logger.debug(f"  Components: {stats.get('connected_components', 0):,}")
    logger.debug(f"  Density: {stats.get('density', 0):.6f}")

    # Bridge nodes
    logger.debug("\n  Finding bridge nodes...")
    bridges = engine.find_bridge_nodes(top_n=10)
    logger.debug(f"  Bridge nodes found: {len(bridges)}")
    for b in bridges[:5]:
        logger.debug(
            f"    🌉 {b.get('memory_id', '?')[:12]}... "
            f"(betweenness={b.get('betweenness', 0):.6f}, "
            f"communities={b.get('communities_connected', 0)})"
        )

    # Community detection
    logger.debug("\n  Detecting communities...")
    try:
        communities = engine.detect_communities()
        logger.debug(f"  Communities found: {len(communities)}")
        for i, comm in enumerate(communities[:5]):
            logger.debug(f"    Community {i}: {len(comm)} members")
    except Exception as e:
        logger.debug(f"  Community detection: {e}")
        communities = []

    # PageRank top nodes
    logger.debug("\n  Computing PageRank...")
    try:
        pr = engine.pagerank()
        top_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.debug(f"  Top PageRank nodes:")
        for node_id, score in top_pr[:5]:
            logger.debug(f"    📊 {node_id[:12]}... (PR={score:.6f})")
    except Exception as e:
        logger.debug(f"  PageRank: {e}")

    return {
        "stats": stats,
        "bridges": len(bridges),
        "communities": len(communities),
    }


def step_dream_cycle(quick=False):
    """Step 5: Dream Cycle — single pass through all phases."""
    if quick:
        logger.debug("\n" + "=" * 70)
        logger.debug("💤 STEP 5: DREAM CYCLE (SKIPPED — quick mode)")
        logger.debug("=" * 70)
        return {"skipped": True}

    logger.debug("\n" + "=" * 70)
    logger.debug("💤 STEP 5: DREAM CYCLE")
    logger.debug("=" * 70)

    try:
        from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

        cycle = get_dream_cycle()

        logger.debug("  Running all dream phases manually...")
        start = time.perf_counter()
        results_phases = {}

        phase_methods = [
            ("triage", cycle._dream_triage),
            ("consolidation", cycle._dream_consolidation),
            ("serendipity", cycle._dream_serendipity),
            ("governance", cycle._dream_governance),
            ("narrative", cycle._dream_narrative),
            ("kaizen", cycle._dream_kaizen),
            ("oracle", cycle._dream_oracle),
            ("decay", cycle._dream_decay),
        ]

        for phase_name, method in phase_methods:
            t0 = time.perf_counter()
            try:
                result = method()
                dt = time.perf_counter() - t0
                results_phases[phase_name] = result
                summary_str = json.dumps(
                    {
                        k: v
                        for k, v in (result or {}).items()
                        if not isinstance(v, (list, dict)) or len(str(v)) < 100
                    },
                    default=str,
                )[:200]
                logger.debug(f"    💤 {phase_name} ({dt:.1f}s): {summary_str}")
            except Exception as e:
                dt = time.perf_counter() - t0
                results_phases[phase_name] = {"error": str(e)}
                logger.debug(f"    ❌ {phase_name} ({dt:.1f}s): {e}")

        elapsed = time.perf_counter() - start
        logger.debug(f"\n  All dream phases complete in {elapsed:.1f}s")
        return results_phases
    except Exception as e:
        logger.debug(f"  ❌ Dream cycle error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def step_harmony_vector():
    """Step 6: Harmony Vector — 7D system health assessment."""
    logger.debug("\n" + "=" * 70)
    logger.debug("🎵 STEP 6: HARMONY VECTOR")
    logger.debug("=" * 70)

    try:
        from whitemagic.harmony.vector import get_harmony_vector

        hv = get_harmony_vector()
        snap = hv.snapshot()
        assessment = snap.to_dict()

        h = assessment.get("harmony", "?")
        logger.debug(
            f"  Overall harmony: {h:.4f}"
            if isinstance(h, (int, float))
            else f"  Overall harmony: {h}"
        )
        logger.debug(f"  Dimensions:")
        for key in [
            "sattva",
            "rajas",
            "tamas",
            "karma_debt",
            "galactic_vitality",
            "tool_diversity",
            "harmony",
        ]:
            val = assessment.get(key)
            if val is not None and isinstance(val, (int, float)):
                bar = "█" * int(float(val) * 20)
                logger.debug(f"    {key:>20}: {val:.4f} {bar}")

        return assessment
    except Exception as e:
        logger.debug(f"  ❌ Harmony Vector error: {e}")
        return {"error": str(e)}


def step_wu_xing_balance():
    """Step 7: Wu Xing Balance — Five Elements phase check."""
    logger.debug("\n" + "=" * 70)
    logger.debug("🔥 STEP 7: WU XING BALANCE")
    logger.debug("=" * 70)

    try:
        from whitemagic.wu_xing import get_wuxing_engine, get_elemental_balance

        engine = get_wuxing_engine()
        balance = get_elemental_balance()
        logger.debug(f"  Current phase: {balance.get('current_phase', '?')}")
        logger.debug(f"  Elements:")
        for elem, val in balance.get("elements", {}).items():
            bar = "█" * int(float(val) * 20) if isinstance(val, (int, float)) else ""
            logger.debug(f"    {elem:>8}: {val:.3f} {bar}")
        return balance
    except Exception as e:
        logger.debug(f"  ❌ Wu Xing error: {e}")
        return {"error": str(e)}


def step_graph_walker_test():
    """Step 8: Graph Walker — test a walk from a high-importance memory."""
    logger.debug("\n" + "=" * 70)
    logger.debug("🚶 STEP 8: GRAPH WALKER TEST")
    logger.debug("=" * 70)

    try:
        from whitemagic.core.memory.graph import get_graph_walker
        from whitemagic.core.memory.unified import get_unified_memory

        walker = get_graph_walker()
        um = get_unified_memory()

        # Find a high-importance memory with associations
        with um.backend.pool.connection() as conn:
            row = conn.execute(
                """SELECT m.id, m.title FROM memories m
                   JOIN associations a ON m.id = a.source_id
                   WHERE m.importance > 0.7
                   GROUP BY m.id
                   HAVING COUNT(*) > 5
                   ORDER BY m.importance DESC
                   LIMIT 1"""
            ).fetchone()

        if not row:
            logger.debug("  No high-importance connected memory found")
            return {"error": "no seed found"}

        seed_id = row[0]
        seed_title = row[1] or seed_id[:12]
        logger.debug(f"  Seed: {seed_title} ({seed_id[:12]}...)")
        logger.debug(f"  Walking 3 hops, top 5 paths...")

        result = walker.walk(
            seed_ids=[seed_id],
            hops=3,
            top_k=5,
            enforce_causality=False,
        )

        logger.debug(f"  Unique nodes visited: {result.unique_nodes_visited}")
        logger.debug(f"  Paths explored: {result.paths_explored}")
        logger.debug(f"  Duration: {result.duration_ms:.0f}ms")

        if result.paths:
            logger.debug(f"\n  Top paths:")
            for i, path in enumerate(result.paths[:3]):
                logger.debug(
                    f"    Path {i + 1}: {' → '.join(n[:8] for n in path.nodes)} "
                    f"(score={path.total_score:.6f}, depth={path.depth})"
                )
                if path.relation_types:
                    logger.debug(f"      Relations: {' → '.join(path.relation_types[:5])}")

        return {
            "seed": seed_id,
            "nodes_visited": result.unique_nodes_visited,
            "paths_explored": result.paths_explored,
            "duration_ms": result.duration_ms,
            "top_paths": len(result.paths),
        }
    except Exception as e:
        logger.debug(f"  ❌ Graph Walker error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def step_system_summary(results):
    """Final: Print comprehensive system summary."""
    logger.debug("\n" + "=" * 70)
    logger.debug("📋 ACTIVATION SEQUENCE COMPLETE")
    logger.debug("=" * 70)

    db = results.get("db_stats", {})
    sweep = results.get("galactic_sweep", {})
    mining = results.get("association_mining", {})
    constellations = results.get("constellation_detection", {})
    graph = results.get("graph_topology", {})

    logger.debug(f"""
  Galaxy Size:     {db.get("memories", "?"):,} memories
  Associations:    {db.get("associations", "?"):,} ({db.get("typed_associations", "?"):,} typed)
  Embeddings:      {db.get("embeddings", "?"):,}
  Holo Coords:     {db.get("holographic_coords", "?"):,}
  DB Size:         {db.get("db_size_mb", "?")} MB
  
  Galactic Zones:  {json.dumps(sweep.get("zone_counts", {}), indent=None)[:200]}
  Core Memories:   {sweep.get("core_count", "?"):,}
  Constellations:  {constellations.get("constellations_found", "?")}
  Bridge Nodes:    {graph.get("bridges", "?")}
  Communities:     {graph.get("communities", "?")}
  
  New Assocs Created: {mining.get("keyword_mining", {}).get("links_created", 0) + mining.get("semantic_mining", {}).get("links_created", 0)}
""")


def main():
    parser = argparse.ArgumentParser(description="WhiteMagic Activation Sequence")
    parser.add_argument("--quick", action="store_true", help="Skip slow operations")
    parser.add_argument(
        "--step",
        choices=[
            "stats",
            "sweep",
            "mine",
            "constellations",
            "graph",
            "dream",
            "harmony",
            "wuxing",
            "walker",
        ],
        help="Run a single step only",
    )
    args = parser.parse_args()

    print("🚀 WhiteMagic v15.7 — Full Activation Sequence")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'quick' if args.quick else 'full'}")
    if args.step:
        print(f"Step: {args.step}")
    print("=" * 70)

    total_start = time.perf_counter()
    results = {}

    step_map = {
        "stats": ("db_stats", step_db_stats),
        "sweep": ("galactic_sweep", step_galactic_sweep),
        "mine": ("association_mining", lambda: step_association_mining(args.quick)),
        "constellations": ("constellation_detection", step_constellation_detection),
        "graph": ("graph_topology", step_graph_topology),
        "dream": ("dream_cycle", lambda: step_dream_cycle(args.quick)),
        "harmony": ("harmony_vector", step_harmony_vector),
        "wuxing": ("wu_xing", step_wu_xing_balance),
        "walker": ("graph_walker", step_graph_walker_test),
    }

    if args.step:
        key, func = step_map[args.step]
        try:
            results[key] = func()
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()
            results[key] = {"error": str(e)}
    else:
        for step_name, (key, func) in step_map.items():
            try:
                results[key] = func()
            except Exception as e:
                print(f"\n  ❌ Step '{step_name}' failed: {e}")
                import traceback

                traceback.print_exc()
                results[key] = {"error": str(e)}

    total_elapsed = time.perf_counter() - total_start

    if not args.step:
        step_system_summary(results)

    print(f"\n⏱  Total time: {total_elapsed:.1f}s")

    REPORT_PATH.parent.mkdir(exist_ok=True)
    try:
        with open(REPORT_PATH, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Report saved: {REPORT_PATH}")
    except Exception as e:
        print(f"⚠ Could not save report: {e}")


if __name__ == "__main__":
    main()
