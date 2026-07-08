#!/usr/bin/env python3
"""Association Graph Builder — Massive Association Mining Pipeline
=================================================================

Builds a rich association graph across all memories using multiple engines:
  1. AssociationMiner — Jaccard overlap + keyword co-occurrence
  2. CausalMiner — Temporal + semantic causal edge discovery
  3. KnowledgeGraphV2 — LightNER pattern-based typed extraction
  4. EntityExtractor — LLM/regex entity-relation extraction
  5. Holographic Proximity — 5D spatial neighbor linking
  6. FTS Overlap — Full-text search term co-occurrence

Usage:
    python scripts/build_association_graph.py                    # All engines
    python scripts/build_association_graph.py --engine jaccard   # Jaccard only
    python scripts/build_association_graph.py --engine causal    # Causal only
    python scripts/build_association_graph.py --engine kg        # Knowledge graph only
    python scripts/build_association_graph.py --engine entity    # Entity extraction only
    python scripts/build_association_graph.py --engine holo      # Holographic proximity only
    python scripts/build_association_graph.py --engine fts       # FTS overlap only
    python scripts/build_association_graph.py --limit 1000       # Limit memories per engine
    python scripts/build_association_graph.py --dry-run          # Preview only
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from whitemagic.core.memory.db_manager import safe_connect

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("assoc_builder")


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH

    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = safe_connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def extract_keywords(text: str, max_words: int = 50) -> list[str]:
    """Extract meaningful keywords from text."""
    import re

    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[#*`_\[\]()]", " ", text)

    # Tokenize
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
        "after",
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
        "are",
        "was",
        "were",
        "said",
        "say",
        "says",
        "went",
        "go",
        "get",
        "got",
        "get",
    }
    words = [w for w in words if w not in stopwords]

    # Count frequency
    counter = Counter(words)
    return [word for word, _ in counter.most_common(max_words)]


def jaccard_similarity(set1: set, set2: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def engine_jaccard(
    conn: sqlite3.Connection, limit: int = 0, dry_run: bool = False
) -> dict:
    """Association mining via keyword Jaccard overlap."""
    log.info("═══ Engine: Jaccard Keyword Overlap ═══")

    query = """
        SELECT id, title, content FROM memories
        WHERE LENGTH(content) > 100 AND LENGTH(content) < 10000
        AND is_protected = 0
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"  Processing {len(memories)} memories")

    # Extract keywords for each memory
    keyword_map = {}
    for mem in memories:
        text = f"{mem['title'] or ''} {mem['content'] or ''}"
        keywords = set(extract_keywords(text, max_words=30))
        if keywords:
            keyword_map[mem["id"]] = keywords

    log.info(f"  Extracted keywords for {len(keyword_map)} memories")

    # Find associations
    mem_ids = list(keyword_map.keys())
    new_assoc = 0
    total_compared = 0

    for i, mem_id in enumerate(mem_ids):
        for j in range(i + 1, len(mem_ids)):
            id_a, id_b = mem_ids[i], mem_ids[j]
            sim = jaccard_similarity(keyword_map[id_a], keyword_map[id_b])

            if sim >= 0.15:  # Threshold
                total_compared += 1
                existing = conn.execute(
                    "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                    (id_a, id_b),
                ).fetchone()[0]

                if existing == 0 and not dry_run:
                    try:
                        conn.execute(
                            """INSERT INTO associations
                               (source_id, target_id, association_type, strength)
                               VALUES (?, ?, ?, ?)""",
                            (id_a, id_b, "semantic_overlap", round(sim, 3)),
                        )
                        new_assoc += 1
                    except sqlite3.IntegrityError:
                        pass

        if (i + 1) % 100 == 0:
            conn.commit()
            log.info(
                f"  Progress: {i + 1}/{len(mem_ids)} ({new_assoc} new associations)"
            )

    conn.commit()
    log.info(
        f"  ✅ Jaccard: {new_assoc} new associations from {total_compared} comparisons"
    )
    return {"new_associations": new_assoc, "compared": total_compared}


def engine_causal(
    conn: sqlite3.Connection, limit: int = 0, dry_run: bool = False
) -> dict:
    """Causal edge discovery via temporal + semantic signals."""
    log.info("═══ Engine: Causal Miner ═══")

    try:
        from whitemagic.core.memory.causal_miner import CausalMiner

        miner = CausalMiner()
    except Exception as e:
        log.warning(f"  CausalMiner unavailable: {e}")
        return {"new_associations": 0, "error": str(e)}

    query = """
        SELECT id, title, content, created_at FROM memories
        WHERE LENGTH(content) > 200 AND LENGTH(content) < 5000
        ORDER BY created_at DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"  Processing {len(memories)} memories for causal links")

    new_assoc = 0
    for i, mem in enumerate(memories):
        text = f"{mem['title'] or ''}\n{mem['content'] or ''}"[:3000]

        try:
            causal_links = miner.extract_causal_links(text)
            for link in causal_links:
                target_keywords = set(extract_keywords(link.get("effect", ""), 10))
                for other in memories:
                    if other["id"] == mem["id"]:
                        continue
                    other_text = f"{other['title'] or ''} {other['content'] or ''}"
                    other_keywords = set(extract_keywords(other_text, 30))
                    overlap = jaccard_similarity(target_keywords, other_keywords)

                    if overlap >= 0.1 and not dry_run:
                        existing = conn.execute(
                            "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                            (mem["id"], other["id"]),
                        ).fetchone()[0]

                        if existing == 0:
                            try:
                                conn.execute(
                                    """INSERT INTO associations
                                       (source_id, target_id, association_type, strength)
                                       VALUES (?, ?, ?, ?)""",
                                    (
                                        mem["id"],
                                        other["id"],
                                        link.get("relation", "causal"),
                                        round(overlap, 3),
                                    ),
                                )
                                new_assoc += 1
                            except sqlite3.IntegrityError:
                                pass
        except Exception as e:
            log.debug(f"  Causal extraction failed for {mem['id'][:8]}: {e}")

        if (i + 1) % 100 == 0:
            conn.commit()
            log.info(
                f"  Progress: {i + 1}/{len(memories)} ({new_assoc} new associations)"
            )

    conn.commit()
    log.info(f"  ✅ Causal: {new_assoc} new associations")
    return {"new_associations": new_assoc}


def engine_knowledge_graph(
    conn: sqlite3.Connection, limit: int = 0, dry_run: bool = False
) -> dict:
    """Knowledge graph extraction via LightNER patterns."""
    log.info("═══ Engine: Knowledge Graph V2 ═══")

    try:
        from whitemagic.core.intelligence.knowledge_graph_v2 import KnowledgeGraphV2

        kg = KnowledgeGraphV2()
    except Exception as e:
        log.warning(f"  KnowledgeGraphV2 unavailable: {e}")
        return {"new_associations": 0, "error": str(e)}

    query = """
        SELECT id, title, content FROM memories
        WHERE importance >= 0.5 AND LENGTH(content) > 100
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"  Processing {len(memories)} high-importance memories")

    new_assoc = 0
    for i, mem in enumerate(memories):
        text = f"{mem['title'] or ''}\n{mem['content'] or ''}"[:2000]

        try:
            # Extract entities and relations
            result = kg.extract_from_text(text)
            entities = result.get("entities", [])
            relations = result.get("relations", [])

            # Create entity nodes as synthetic memories if they don't exist
            for entity in entities:
                entity_id = f"entity:{entity.get('name', '').lower().replace(' ', '_')}"
                if not dry_run:
                    exists = conn.execute(
                        "SELECT COUNT(*) FROM memories WHERE id = ?", (entity_id,)
                    ).fetchone()[0]

                    if exists == 0:
                        try:
                            conn.execute(
                                """INSERT OR IGNORE INTO memories
                                   (id, title, content, memory_type, importance, created_at)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (
                                    entity_id,
                                    f"Entity: {entity.get('name')}",
                                    f"Extracted entity of type {entity.get('type')}",
                                    "LONG_TERM",
                                    0.3,
                                    datetime.now().isoformat(),
                                ),
                            )
                        except sqlite3.IntegrityError:
                            pass

            # Create associations from relations
            for rel in relations:
                subject = rel.get("subject", "").lower().replace(" ", "_")
                obj = rel.get("object", "").lower().replace(" ", "_")
                predicate = rel.get("predicate", "RELATED_TO")

                if subject and obj:
                    source_id = f"entity:{subject}"
                    target_id = f"entity:{obj}"

                    if not dry_run:
                        existing = conn.execute(
                            "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                            (source_id, target_id),
                        ).fetchone()[0]

                        if existing == 0:
                            try:
                                conn.execute(
                                    """INSERT INTO associations
                                       (source_id, target_id, association_type, strength)
                                       VALUES (?, ?, ?, ?)""",
                                    (source_id, target_id, predicate, 0.5),
                                )
                                new_assoc += 1
                            except sqlite3.IntegrityError:
                                pass

            # Link memory to its entities
            for entity in entities:
                entity_id = f"entity:{entity.get('name', '').lower().replace(' ', '_')}"
                if not dry_run:
                    existing = conn.execute(
                        "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                        (mem["id"], entity_id),
                    ).fetchone()[0]

                    if existing == 0:
                        try:
                            conn.execute(
                                """INSERT INTO associations
                                   (source_id, target_id, association_type, strength)
                                   VALUES (?, ?, ?, ?)""",
                                (mem["id"], entity_id, "mentions", 0.6),
                            )
                            new_assoc += 1
                        except sqlite3.IntegrityError:
                            pass
        except Exception as e:
            log.debug(f"  KG extraction failed for {mem['id'][:8]}: {e}")

        if (i + 1) % 50 == 0:
            conn.commit()
            log.info(
                f"  Progress: {i + 1}/{len(memories)} ({new_assoc} new associations)"
            )

    conn.commit()
    log.info(f"  ✅ KG: {new_assoc} new associations")
    return {"new_associations": new_assoc}


def engine_entity(
    conn: sqlite3.Connection, limit: int = 0, dry_run: bool = False
) -> dict:
    """Entity-relation extraction via LLM/regex."""
    log.info("═══ Engine: Entity Extractor ═══")

    try:
        from whitemagic.core.intelligence.entity_extractor import get_entity_extractor

        extractor = get_entity_extractor()
    except Exception as e:
        log.warning(f"  EntityExtractor unavailable: {e}")
        return {"new_associations": 0, "error": str(e)}

    query = """
        SELECT id, title, content FROM memories
        WHERE LENGTH(content) > 200 AND LENGTH(content) < 4000
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"  Processing {len(memories)} memories")

    new_assoc = 0
    for i, mem in enumerate(memories):
        text = f"{mem['title'] or ''}\n{mem['content'] or ''}"[:3000]

        try:
            result = extractor.extract(text)
            for rel in result.relations:
                target_entity = f"entity:{rel.object.lower().replace(' ', '_')}"

                if not dry_run:
                    existing = conn.execute(
                        "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                        (mem["id"], target_entity),
                    ).fetchone()[0]

                    if existing == 0:
                        try:
                            conn.execute(
                                """INSERT INTO associations
                                   (source_id, target_id, association_type, strength)
                                   VALUES (?, ?, ?, ?)""",
                                (
                                    mem["id"],
                                    target_entity,
                                    rel.predicate,
                                    round(rel.confidence, 3),
                                ),
                            )
                            new_assoc += 1
                        except sqlite3.IntegrityError:
                            pass
        except Exception as e:
            log.debug(f"  Entity extraction failed for {mem['id'][:8]}: {e}")

        if (i + 1) % 100 == 0:
            conn.commit()
            log.info(
                f"  Progress: {i + 1}/{len(memories)} ({new_assoc} new associations)"
            )

    conn.commit()
    log.info(f"  ✅ Entity: {new_assoc} new associations")
    return {"new_associations": new_assoc}


def engine_holographic(
    conn: sqlite3.Connection, limit: int = 0, dry_run: bool = False
) -> dict:
    """Association via 5D holographic proximity."""
    log.info("═══ Engine: Holographic Proximity ═══")

    query = """
        SELECT m.id, h.x, h.y, h.z, h.w, h.v
        FROM memories m
        JOIN holographic_coords h ON m.id = h.memory_id
        WHERE m.is_protected = 0
        ORDER BY h.v DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    log.info(f"  Processing {len(rows)} memories with holographic coords")

    import math

    def distance_5d(a, b):
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    # Build coordinate map
    coord_map = {}
    for row in rows:
        coord_map[row["id"]] = (row["x"], row["y"], row["z"], row["w"], row["v"])

    # Find neighbors within threshold
    mem_ids = list(coord_map.keys())
    new_assoc = 0
    threshold = 0.3  # 5D distance threshold

    for i, mem_id in enumerate(mem_ids):
        id_a = mem_ids[i]
        coords_a = coord_map[id_a]

        for j in range(i + 1, len(mem_ids)):
            id_b = mem_ids[j]
            coords_b = coord_map[id_b]

            dist = distance_5d(coords_a, coords_b)
            if dist < threshold:
                strength = max(0.1, 1.0 - dist)

                if not dry_run:
                    existing = conn.execute(
                        "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                        (id_a, id_b),
                    ).fetchone()[0]

                    if existing == 0:
                        try:
                            conn.execute(
                                """INSERT INTO associations
                                   (source_id, target_id, association_type, strength)
                                   VALUES (?, ?, ?, ?)""",
                                (
                                    id_a,
                                    id_b,
                                    "holographic_proximity",
                                    round(strength, 3),
                                ),
                            )
                            new_assoc += 1
                        except sqlite3.IntegrityError:
                            pass

        if (i + 1) % 200 == 0:
            conn.commit()
            log.info(
                f"  Progress: {i + 1}/{len(mem_ids)} ({new_assoc} new associations)"
            )

    conn.commit()
    log.info(f"  ✅ Holographic: {new_assoc} new associations")
    return {"new_associations": new_assoc}


def engine_fts(conn: sqlite3.Connection, limit: int = 0, dry_run: bool = False) -> dict:
    """Association via FTS term co-occurrence."""
    log.info("═══ Engine: FTS Overlap ═══")

    query = """
        SELECT id, title, content FROM memories
        WHERE LENGTH(content) > 100
        ORDER BY importance DESC
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    log.info(f"  Processing {len(memories)} memories")

    # Extract FTS terms (simple tokenization)
    import re

    term_map = {}
    for mem in memories:
        text = f"{mem['title'] or ''} {mem['content'] or ''}".lower()
        terms = set(re.findall(r"\b[a-z]{4,}\b", text))
        terms -= {
            "this",
            "that",
            "with",
            "from",
            "have",
            "been",
            "were",
            "will",
            "would",
            "could",
            "should",
        }
        if terms:
            term_map[mem["id"]] = terms

    # Find co-occurrence associations
    mem_ids = list(term_map.keys())
    new_assoc = 0

    for i, mem_id in enumerate(mem_ids):
        for j in range(i + 1, len(mem_ids)):
            id_a, id_b = mem_ids[i], mem_ids[j]
            overlap = len(term_map[id_a] & term_map[id_b])
            union = len(term_map[id_a] | term_map[id_b])

            if union > 0:
                sim = overlap / union
                if sim >= 0.2 and overlap >= 5:  # Threshold
                    if not dry_run:
                        existing = conn.execute(
                            "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                            (id_a, id_b),
                        ).fetchone()[0]

                        if existing == 0:
                            try:
                                conn.execute(
                                    """INSERT INTO associations
                                       (source_id, target_id, association_type, strength)
                                       VALUES (?, ?, ?, ?)""",
                                    (id_a, id_b, "fts_overlap", round(sim, 3)),
                                )
                                new_assoc += 1
                            except sqlite3.IntegrityError:
                                pass

        if (i + 1) % 100 == 0:
            conn.commit()
            log.info(
                f"  Progress: {i + 1}/{len(mem_ids)} ({new_assoc} new associations)"
            )

    conn.commit()
    log.info(f"  ✅ FTS: {new_assoc} new associations")
    return {"new_associations": new_assoc}


def print_final_stats(conn):
    """Print final association statistics."""
    log.info("\n" + "=" * 60)
    log.info("📊 Association Graph Statistics")
    log.info("=" * 60)

    total = conn.execute("SELECT COUNT(*) FROM associations").fetchone()[0]
    log.info(f"  Total associations: {total:,}")

    # Type distribution
    types = conn.execute("""
        SELECT association_type, COUNT(*) as cnt
        FROM associations
        GROUP BY association_type
        ORDER BY cnt DESC
    """).fetchall()

    log.info("\n  Association Types:")
    for row in types:
        log.info(f"    {row['association_type']}: {row['cnt']:,}")

    # Strength distribution
    strength_dist = conn.execute("""
        SELECT
            CASE
                WHEN strength < 0.2 THEN 'weak (0.0-0.2)'
                WHEN strength < 0.4 THEN 'moderate (0.2-0.4)'
                WHEN strength < 0.6 THEN 'strong (0.4-0.6)'
                WHEN strength < 0.8 THEN 'very strong (0.6-0.8)'
                ELSE 'extreme (0.8+)'
            END as bucket,
            COUNT(*) as cnt
        FROM associations
        GROUP BY bucket
        ORDER BY MIN(strength)
    """).fetchall()

    log.info("\n  Strength Distribution:")
    for row in strength_dist:
        log.info(f"    {row['bucket']}: {row['cnt']:,}")

    # Memories with associations
    mems_with_assoc = conn.execute("""
        SELECT COUNT(DISTINCT source_id) FROM associations
    """).fetchone()[0]

    total_mems = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    log.info(
        f"\n  Memories with associations: {mems_with_assoc:,}/{total_mems:,} ({100 * mems_with_assoc / total_mems:.1f}%)"
    )


def main():
    parser = argparse.ArgumentParser(description="Association Graph Builder")
    parser.add_argument(
        "--engine",
        choices=["jaccard", "causal", "kg", "entity", "holo", "fts", "all"],
        default="all",
        help="Run specific engine",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit memories per engine"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    db_path = get_db_path()
    log.info(f"🔗 Association Graph Builder")
    log.info(f"   DB: {db_path}")
    log.info(f"   Engine: {args.engine}")
    log.info(f"   Limit: {args.limit or 'unlimited'}")
    log.info(f"   Dry run: {args.dry_run}")

    if not db_path.exists():
        log.error(f"Database not found: {db_path}")
        sys.exit(1)

    conn = get_conn(db_path)
    total_start = time.perf_counter()
    results = {}

    engines = {
        "jaccard": engine_jaccard,
        "causal": engine_causal,
        "kg": engine_knowledge_graph,
        "entity": engine_entity,
        "holo": engine_holographic,
        "fts": engine_fts,
    }

    if args.engine == "all":
        engine_list = list(engines.items())
    else:
        engine_list = [(args.engine, engines[args.engine])]

    for name, func in engine_list:
        log.info(f"\n🔧 Running engine: {name}")
        results[name] = func(conn, limit=args.limit, dry_run=args.dry_run)

    total_elapsed = time.perf_counter() - total_start
    print_final_stats(conn)

    log.info(f"\n⏱  Total time: {total_elapsed:.1f}s")
    log.info(f"\n✅ Association graph build complete!")

    conn.close()


if __name__ == "__main__":
    main()
