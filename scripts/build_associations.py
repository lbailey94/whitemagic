#!/usr/bin/env python3
"""
Build intragalactic and extragalactic associations across WhiteMagic galaxies.

Phase 1: Assign holographic coordinates to memories that lack them.
Phase 2: Build intragalactic associations (keyword overlap within a galaxy).
Phase 3: Build extragalactic associations (cross-galaxy keyword overlap).
Phase 4: Report constellation candidates (topic clusters spanning galaxies).

Uses batch SQLite operations (executemany) per the I/O optimization pattern.
Bypasses the unified API to avoid injection scanner false positives on long text.

USAGE:
  PYTHONPATH=core python3 scripts/build_associations.py [--dry-run] [--galaxy NAME] [--skip-coords]
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ASSOC] %(message)s")
logger = logging.getLogger(__name__)

GALAXIES_DIR = Path.home() / ".whitemagic/users/local/galaxies"

STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "because", "but", "and", "or",
    "if", "while", "about", "up", "out", "off", "over", "this", "that",
    "these", "those", "it", "its", "my", "your", "his", "her", "our",
    "their", "what", "which", "who", "whom", "me", "him", "them", "we",
    "you", "they", "i", "he", "she", "us", "self", "none", "also", "any",
    "def", "class", "import", "return", "true", "false", "none",
    "file", "data", "code", "test", "run", "set", "get", "new", "old",
    "one", "two", "three", "first", "last", "next", "prev", "line",
    # Generic terms that produce noisy constellations
    "session", "source", "across", "insight", "insights", "summary",
    "note", "notes", "create", "needs", "guide", "multi", "success",
    "actually", "anything", "approach", "believe", "begin", "beginning",
    "close", "codebase", "conduct", "decision", "discuss", "discussed",
    "address", "agree", "article", "account", "apply", "back", "backed",
    "bare", "batch", "categorize", "already", "aren", "contributions",
    "context", "current", "error", "events", "call", "changed",
    "bleeding", "free", "core", "memories", "research",
})

WORD_RE = re.compile(r"[a-z_][a-z0-9_]{3,}")

# Galaxies to process (skip benchmark/test galaxies)
TARGET_GALAXIES = [
    "codex", "sessions", "research", "archive", "meta",
    "universal", "knowledge", "dreams", "citta", "aria",
]


def get_db_path(galaxy: str) -> Path:
    return GALAXIES_DIR / galaxy / "whitemagic.db"


def extract_keywords(text: str, max_keywords: int = 40) -> set[str]:
    """Extract meaningful keywords from text."""
    text_lower = text.lower()
    words = WORD_RE.findall(text_lower)
    keywords = {w for w in words if w not in STOP_WORDS and len(w) > 3}
    if len(keywords) > max_keywords:
        freq: defaultdict[str, int] = defaultdict(int)
        for w in words:
            if w in keywords:
                freq[w] += 1
        sorted_kw = sorted(keywords, key=lambda k: freq[k], reverse=True)
        keywords = set(sorted_kw[:max_keywords])
    return keywords


def compute_overlap(kw_a: set[str], kw_b: set[str]) -> tuple[float, set[str]]:
    """Compute weighted Jaccard overlap between two keyword sets."""
    if not kw_a or not kw_b:
        return 0.0, set()
    shared = kw_a & kw_b
    union_size = len(kw_a | kw_b)
    if union_size == 0:
        return 0.0, set()
    raw_jaccard = len(shared) / union_size
    count_bonus = min(1.0, len(shared) / 5.0) * 0.3
    score = min(1.0, raw_jaccard + count_bonus)
    return score, shared


def assign_holographic_coords(galaxy: str, dry_run: bool = False) -> int:
    """Assign holographic coordinates to memories that lack them."""
    db_path = get_db_path(galaxy)
    if not db_path.exists():
        return 0

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row

    # Find memories without coords
    try:
        missing = db.execute("""
            SELECT m.id, m.title, m.content, m.importance, m.galaxy, m.memory_type,
                   m.emotional_valence, m.created_at, m.metadata
            FROM memories m
            LEFT JOIN holographic_coords h ON m.id = h.memory_id
            WHERE h.memory_id IS NULL
            LIMIT 5000
        """).fetchall()
    except sqlite3.OperationalError:
        logger.warning(f"  {galaxy}: holographic_coords table missing, skipping")
        db.close()
        return 0

    if not missing:
        db.close()
        return 0

    logger.info(f"  {galaxy}: {len(missing)} memories need holographic coords")

    if dry_run:
        db.close()
        return len(missing)

    from whitemagic.core.intelligence.hologram.encoder import CoordinateEncoder
    encoder = CoordinateEncoder()

    # Batch insert coords
    BATCH_SIZE = 500
    assigned = 0
    chunk = []

    for row in missing:
        mem_dict = {
            "id": row["id"],
            "title": row["title"] or "",
            "content": str(row["content"])[:500],
            "importance": row["importance"] or 0.5,
            "galaxy": row["galaxy"] or galaxy,
            "memory_type": row["memory_type"] or "LONG_TERM",
            "emotional_valence": row["emotional_valence"] or 0.0,
            "created_at": row["created_at"] or "",
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
        }
        try:
            coord = encoder.encode(mem_dict)
            chunk.append((row["id"], coord.x, coord.y, coord.z, coord.w, coord.v, coord.u))
        except Exception as e:
            logger.debug(f"  encode failed for {row['id'][:12]}: {e}")
            continue

        if len(chunk) >= BATCH_SIZE:
            db.executemany(
                "INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v, u) VALUES (?,?,?,?,?,?,?)",
                chunk,
            )
            db.commit()
            assigned += len(chunk)
            chunk = []

    if chunk:
        db.executemany(
            "INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v, u) VALUES (?,?,?,?,?,?,?)",
            chunk,
        )
        db.commit()
        assigned += len(chunk)

    db.close()
    logger.info(f"  {galaxy}: assigned {assigned} holographic coords")
    return assigned


def build_intragalactic(galaxy: str, min_overlap: float = 0.15, dry_run: bool = False) -> dict:
    """Build keyword-overlap associations within a single galaxy.

    Uses an inverted keyword index for O(n*k) candidate generation instead of O(n²)
    pairwise comparison. Only memories sharing at least one keyword are compared.
    """
    db_path = get_db_path(galaxy)
    if not db_path.exists():
        return {"galaxy": galaxy, "edges": 0, "error": "db not found"}

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row

    # Load all memories (id, title, content preview)
    # For sessions galaxy, limit content preview to keep memory bounded
    content_len = 500 if galaxy == "sessions" else 2000
    rows = db.execute(f"""
        SELECT id, title, SUBSTR(content, 1, {content_len}) as content_preview
        FROM memories
        WHERE content IS NOT NULL AND LENGTH(content) > 50
    """).fetchall()

    if len(rows) < 2:
        db.close()
        return {"galaxy": galaxy, "memories": len(rows), "edges": 0}

    logger.info(f"  {galaxy}: {len(rows)} memories to process for intragalactic associations")

    # Extract keywords for each memory and build inverted index
    fingerprints: dict[str, set[str]] = {}
    inverted_index: dict[str, set[str]] = defaultdict(set)  # keyword -> set of memory_ids

    for row in rows:
        text = f"{row['title'] or ''} {row['content_preview'] or ''}"
        kw = extract_keywords(text)
        if len(kw) >= 3:
            fingerprints[row["id"]] = kw
            for k in kw:
                inverted_index[k].add(row["id"])

    mem_ids = list(fingerprints.keys())
    logger.info(f"  {galaxy}: {len(mem_ids)} memories with sufficient keywords, {len(inverted_index)} unique keywords")

    # Load existing associations to skip
    existing = set()
    try:
        for row in db.execute("SELECT source_id, target_id FROM associations").fetchall():
            existing.add((row["source_id"], row["target_id"]))
    except Exception:
        pass

    # Generate candidate pairs via inverted index (only pairs sharing keywords)
    candidate_pairs: set[tuple[str, str]] = set()
    for keyword, mem_set in inverted_index.items():
        if len(mem_set) < 2:
            continue
        # Cap candidates per keyword to avoid explosion on very common terms
        mem_list = list(mem_set)
        if len(mem_list) > 500:
            # Only take top memories by keyword frequency (proxy: first 500)
            mem_list = mem_list[:500]
        for i in range(len(mem_list)):
            for j in range(i + 1, len(mem_list)):
                a, b = mem_list[i], mem_list[j]
                if a < b:
                    candidate_pairs.add((a, b))
                else:
                    candidate_pairs.add((b, a))

    logger.info(f"  {galaxy}: {len(candidate_pairs)} candidate pairs from inverted index")

    # Evaluate candidate pairs
    edges = []
    pairs_evaluated = 0

    for a_id, b_id in candidate_pairs:
        pairs_evaluated += 1
        if (a_id, b_id) in existing or (b_id, a_id) in existing:
            continue

        score, shared = compute_overlap(fingerprints[a_id], fingerprints[b_id])
        if score >= min_overlap and len(shared) >= 3:
            edges.append((a_id, b_id, score, sorted(shared)[:5]))

    logger.info(f"  {galaxy}: {pairs_evaluated} pairs evaluated, {len(edges)} new edges found")

    if not dry_run and edges:
        # Use DELETE journal mode for bulk inserts (avoids WAL bloat)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA cache_size=-64000")  # 64MB cache
        db.execute("PRAGMA temp_store=MEMORY")

        # Use plain INSERT with periodic commits.
        # We already filtered existing associations in Python.
        BATCH_SIZE = 50000
        COMMIT_EVERY = 500000  # commit every 500K rows
        total_inserted = 0
        chunk = []
        since_commit = 0

        for a_id, b_id, score, shared_kw in edges:
            chunk.append((a_id, b_id, score, "keyword_overlap", "intra_galaxy"))
            chunk.append((b_id, a_id, score, "keyword_overlap", "intra_galaxy"))

            if len(chunk) >= BATCH_SIZE:
                try:
                    db.executemany(
                        "INSERT INTO associations (source_id, target_id, strength, relation_type, edge_type) VALUES (?, ?, ?, ?, ?)",
                        chunk,
                    )
                except sqlite3.OperationalError:
                    db.executemany(
                        "INSERT INTO associations (source_id, target_id, strength) VALUES (?, ?, ?)",
                        [(c[0], c[1], c[2]) for c in chunk],
                    )
                total_inserted += len(chunk)
                since_commit += len(chunk)
                chunk = []

                if since_commit >= COMMIT_EVERY:
                    db.commit()
                    since_commit = 0
                    logger.info(f"  {galaxy}: {total_inserted} rows inserted...")

        if chunk:
            try:
                db.executemany(
                    "INSERT INTO associations (source_id, target_id, strength, relation_type, edge_type) VALUES (?, ?, ?, ?, ?)",
                    chunk,
                )
            except sqlite3.OperationalError:
                db.executemany(
                    "INSERT INTO associations (source_id, target_id, strength) VALUES (?, ?, ?)",
                    [(c[0], c[1], c[2]) for c in chunk],
                )
            total_inserted += len(chunk)

        db.commit()
        db.execute("PRAGMA synchronous=NORMAL")

        logger.info(f"  {galaxy}: inserted {total_inserted} association rows (bidirectional)")

    db.close()
    return {
        "galaxy": galaxy,
        "memories": len(rows),
        "with_keywords": len(mem_ids),
        "pairs_evaluated": pairs_evaluated,
        "edges": len(edges),
        "inserted": total_inserted if not dry_run and edges else 0,
    }


def build_extragalactic(min_overlap: float = 0.20, dry_run: bool = False) -> dict:
    """Build cross-galaxy associations using keyword overlap."""
    # Sample memories from each galaxy
    galaxy_samples: dict[str, list[tuple[str, set[str]]]] = {}

    for galaxy in TARGET_GALAXIES:
        db_path = get_db_path(galaxy)
        if not db_path.exists():
            continue
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row

        # Sample up to 200 memories per galaxy (title + content preview)
        rows = db.execute("""
            SELECT id, title, SUBSTR(content, 1, 1000) as content_preview
            FROM memories
            WHERE content IS NOT NULL AND LENGTH(content) > 50
            ORDER BY importance DESC
            LIMIT 200
        """).fetchall()

        samples = []
        for row in rows:
            text = f"{row['title'] or ''} {row['content_preview'] or ''}"
            kw = extract_keywords(text)
            if len(kw) >= 3:
                samples.append((row["id"], kw))

        if samples:
            galaxy_samples[galaxy] = samples
            logger.info(f"  {galaxy}: {len(samples)} sampled for cross-galaxy matching")

        db.close()

    if len(galaxy_samples) < 2:
        return {"galaxies": len(galaxy_samples), "edges": 0}

    # Cross-galaxy matching
    galaxy_list = list(galaxy_samples.keys())
    edges = []  # (source_id, source_galaxy, target_id, target_galaxy, score, shared_keywords)
    pairs_evaluated = 0

    for i in range(len(galaxy_list)):
        for j in range(i + 1, len(galaxy_list)):
            g1, g2 = galaxy_list[i], galaxy_list[j]
            for mem1_id, kw1 in galaxy_samples[g1]:
                for mem2_id, kw2 in galaxy_samples[g2]:
                    pairs_evaluated += 1
                    score, shared = compute_overlap(kw1, kw2)
                    if score >= min_overlap and len(shared) >= 4:
                        edges.append((mem1_id, g1, mem2_id, g2, score, sorted(shared)[:5]))

    logger.info(f"  Cross-galaxy: {pairs_evaluated} pairs, {len(edges)} edges found")

    # Persist: store cross-galaxy edges in the source galaxy's DB
    total_inserted = 0
    if not dry_run and edges:
        # Group edges by source galaxy
        by_galaxy: dict[str, list] = defaultdict(list)
        for src_id, src_gal, tgt_id, tgt_gal, score, shared in edges:
            by_galaxy[src_gal].append((src_id, tgt_id, score, "cross_galaxy", "cross_galaxy"))
            by_galaxy[tgt_gal].append((tgt_id, src_id, score, "cross_galaxy", "cross_galaxy"))

        for gal, chunk_data in by_galaxy.items():
            db_path = get_db_path(gal)
            if not db_path.exists():
                continue
            db = sqlite3.connect(str(db_path))
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-64000")
            db.execute("PRAGMA temp_store=MEMORY")
            try:
                db.executemany(
                    "INSERT INTO associations (source_id, target_id, strength, relation_type, edge_type) VALUES (?, ?, ?, ?, ?)",
                    chunk_data,
                )
                db.commit()
                total_inserted += len(chunk_data)
            except sqlite3.OperationalError:
                db.executemany(
                    "INSERT INTO associations (source_id, target_id, strength) VALUES (?, ?, ?)",
                    [(c[0], c[1], c[2]) for c in chunk_data],
                )
                db.commit()
                total_inserted += len(chunk_data)
            db.execute("PRAGMA synchronous=NORMAL")
            db.close()

        logger.info(f"  Cross-galaxy: inserted {total_inserted} association rows")

    return {
        "galaxies": len(galaxy_samples),
        "total_sampled": sum(len(v) for v in galaxy_samples.values()),
        "pairs_evaluated": pairs_evaluated,
        "edges": len(edges),
        "inserted": total_inserted,
        "top_links": [
            {"src_galaxy": e[1], "tgt_galaxy": e[3], "score": round(e[4], 3), "shared": e[5]}
            for e in sorted(edges, key=lambda x: -x[4])[:20]
        ],
    }


def find_constellations() -> list[dict]:
    """Find topic clusters (constellations) spanning multiple galaxies."""
    # Build a keyword -> [(memory_id, galaxy)] index
    keyword_index: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for galaxy in TARGET_GALAXIES:
        db_path = get_db_path(galaxy)
        if not db_path.exists():
            continue
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT id, title, SUBSTR(content, 1, 500) as content_preview
            FROM memories
            WHERE content IS NOT NULL AND LENGTH(content) > 50
            ORDER BY importance DESC
            LIMIT 100
        """).fetchall()

        for row in rows:
            text = f"{row['title'] or ''} {row['content_preview'] or ''}"
            kw = extract_keywords(text)
            for k in kw:
                keyword_index[k].append((row["id"], galaxy))

        db.close()

    # Find keywords that appear across multiple galaxies
    constellations = []
    for kw, locations in keyword_index.items():
        galaxies = {loc[1] for loc in locations}
        if len(galaxies) >= 3 and len(locations) >= 5:
            constellations.append({
                "keyword": kw,
                "galaxies": sorted(galaxies),
                "galaxy_count": len(galaxies),
                "memory_count": len(locations),
            })

    # Sort by galaxy count (most connected first)
    constellations.sort(key=lambda c: (-c["galaxy_count"], -c["memory_count"]))
    return constellations[:50]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build intragalactic and extragalactic associations")
    parser.add_argument("--dry-run", action="store_true", help="Analyze without writing to DBs")
    parser.add_argument("--galaxy", type=str, default=None, help="Only process a specific galaxy")
    parser.add_argument("--skip-coords", action="store_true", help="Skip holographic coordinate assignment")
    parser.add_argument("--skip-intra", action="store_true", help="Skip intragalactic associations")
    parser.add_argument("--skip-extra", action="store_true", help="Skip extragalactic associations")
    parser.add_argument("--skip-constellations", action="store_true", help="Skip constellation detection")
    args = parser.parse_args()

    print("=" * 70)
    print("WHITE MAGIC — GALACTIC ASSOCIATION BUILDER")
    print("=" * 70)
    print(f"Dry run: {args.dry_run}")
    print()

    galaxies = [args.galaxy] if args.galaxy else TARGET_GALAXIES
    start = time.time()

    # Phase 1: Holographic coordinates
    if not args.skip_coords:
        print("=" * 70)
        print("PHASE 1: Holographic Coordinate Assignment")
        print("=" * 70)
        total_coords = 0
        for galaxy in galaxies:
            assigned = assign_holographic_coords(galaxy, dry_run=args.dry_run)
            total_coords += assigned
        print(f"\nTotal coords assigned: {total_coords}")
        print()

    # Phase 2: Intragalactic associations
    if not args.skip_intra:
        print("=" * 70)
        print("PHASE 2: Intragalactic Associations (keyword overlap)")
        print("=" * 70)
        all_results = []
        for galaxy in galaxies:
            result = build_intragalactic(galaxy, dry_run=args.dry_run)
            all_results.append(result)
            print(f"  {galaxy}: {result.get('edges', 0)} edges, {result.get('inserted', 0)} inserted")
        print()
        total_edges = sum(r.get("edges", 0) for r in all_results)
        total_inserted = sum(r.get("inserted", 0) for r in all_results)
        print(f"Total intragalactic edges: {total_edges}")
        print(f"Total rows inserted: {total_inserted}")
        print()

    # Phase 3: Extragalactic associations
    if not args.skip_extra:
        print("=" * 70)
        print("PHASE 3: Extragalactic Associations (cross-galaxy)")
        print("=" * 70)
        xgal_result = build_extragalactic(dry_run=args.dry_run)
        print(f"  Galaxies sampled: {xgal_result['galaxies']}")
        print(f"  Total memories sampled: {xgal_result['total_sampled']}")
        print(f"  Pairs evaluated: {xgal_result['pairs_evaluated']}")
        print(f"  Cross-galaxy edges: {xgal_result['edges']}")
        print(f"  Rows inserted: {xgal_result.get('inserted', 0)}")
        if xgal_result.get("top_links"):
            print(f"\n  Top cross-galaxy links:")
            for link in xgal_result["top_links"][:10]:
                print(f"    {link['src_galaxy']:>12} ↔ {link['tgt_galaxy']:<12}  score={link['score']}  shared={link['shared']}")
        print()

    # Phase 4: Constellations
    if not args.skip_constellations:
        print("=" * 70)
        print("PHASE 4: Constellation Detection (cross-galaxy topic clusters)")
        print("=" * 70)
        constellations = find_constellations()
        print(f"  Found {len(constellations)} constellation candidates")
        print(f"\n  Top 20 constellations (by galaxy span):")
        for c in constellations[:20]:
            print(f"    {c['keyword']:>25}  galaxies={c['galaxy_count']}  memories={c['memory_count']}  [{', '.join(c['galaxies'])}]")
        print()

    elapsed = time.time() - start
    print("=" * 70)
    print(f"DONE — {elapsed:.1f}s elapsed")
    print("=" * 70)


if __name__ == "__main__":
    main()
