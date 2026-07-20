#!/usr/bin/env python3
"""Migrate memories from old monolithic DBs into per-galaxy DBs.

Sources:
  1. whitemagic.db.bak.20260709_143945 (62,467 memories, Nov 2025 – Jul 9 2026)
  2. whitemagic.db.corrupt.20260710 (764 extra memories not in source 1)
  3. State galaxy backups (codex 141, insight 27, research 33, sessions 30, etc.)

Deprecated galaxy mappings:
  self_learning -> knowledge
  insight -> knowledge
  self_discovery -> knowledge
  translation -> codex
  test -> archive
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

GALAXIES_DIR = Path(os.path.expanduser("~/.whitemagic/users/local/galaxies"))
MEMORY_DIR = Path(os.path.expanduser("~/.whitemagic/memory"))
STATE_GALAXIES_DIR = Path(os.path.expanduser("~/.whitemagic/state/users/local/galaxies"))

DEPRECATED_GALAXY_MAP = {
    "self_learning": "knowledge",
    "insight": "knowledge",
    "self_discovery": "knowledge",
    "translation": "codex",
    "test": "archive",
}

# Old monolithic memories columns
OLD_COLS = (
    "id", "content", "title", "tags", "created_at", "updated_at",
    "memory_type", "importance", "access_count", "accessed_at",
    "emotional_valence", "neuro_score", "novelty_score", "recall_count",
    "half_life_days", "is_protected", "galactic_distance",
    "retention_score", "last_retention_sweep", "metadata",
    "event_time", "ingestion_time", "is_private", "model_exclude",
    "content_hash", "galaxy", "source_trust",
)

# Live galaxy memories columns (in order for INSERT)
LIVE_COLS = (
    "id", "content", "memory_type", "created_at", "updated_at",
    "accessed_at", "access_count", "emotional_valence", "importance",
    "neuro_score", "novelty_score", "recall_count", "half_life_days",
    "is_protected", "metadata", "title", "galactic_distance",
    "retention_score", "last_retention_sweep", "content_hash",
    "event_time", "ingestion_time", "is_private", "model_exclude",
    "galaxy", "source_trust", "version", "agent_id",
)


def map_galaxy(galaxy: str) -> str:
    return DEPRECATED_GALAXY_MAP.get(galaxy, galaxy)


def galaxy_db_path(galaxy: str) -> Path:
    return GALAXIES_DIR / map_galaxy(galaxy) / "whitemagic.db"


def get_existing(conn, table, col, key_col="id"):
    rows = conn.execute(f"SELECT {key_col} FROM {table}").fetchall()
    return {r[0] for r in rows if r[0]}


def ensure_galaxy_db(galaxy: str):
    """Create a galaxy DB if it doesn't exist, using schema from an existing galaxy."""
    dbp = GALAXIES_DIR / galaxy / "whitemagic.db"
    if dbp.exists():
        return dbp
    dbp.parent.mkdir(parents=True, exist_ok=True)
    # Copy schema from sessions galaxy (has all tables)
    template = GALAXIES_DIR / "sessions" / "whitemagic.db"
    import shutil
    shutil.copy2(str(template), str(dbp))
    # Wipe data but keep schema
    conn = sqlite3.connect(str(dbp))
    for tbl in ["memories", "tags", "associations", "holographic_coords", "constellation_membership", "dharma_audit", "akashic_seeds"]:
        try:
            conn.execute(f"DELETE FROM {tbl}")
        except Exception:
            pass
    try:
        conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print(f"  Created new galaxy DB: {galaxy}")
    return dbp


def migrate_source(src_path: Path, label: str, dry_run=False):
    print(f"\n{'='*60}")
    print(f"Migrating: {label}")
    print(f"  {src_path} ({src_path.stat().st_size / 1048576:.1f} MB)")

    src = sqlite3.connect(str(src_path))
    src.row_factory = sqlite3.Row

    rows = src.execute(f"SELECT {', '.join(OLD_COLS)} FROM memories").fetchall()
    print(f"  Total memories: {len(rows)}")

    by_galaxy = {}
    for r in rows:
        g = map_galaxy(r["galaxy"] or "universal")
        by_galaxy.setdefault(g, []).append(r)

    total_migrated = 0
    total_skipped = 0

    for galaxy, mems in sorted(by_galaxy.items(), key=lambda x: -len(x[1])):
        dbp = galaxy_db_path(galaxy)
        if not dbp.exists():
            if dry_run:
                print(f"  {galaxy}: would create DB + migrate {len(mems)} memories")
                total_migrated += len(mems)
                continue
            dbp = ensure_galaxy_db(galaxy)

        conn = sqlite3.connect(str(dbp))
        existing_ids = get_existing(conn, "memories", "id")
        existing_hashes = {
            r[0] for r in conn.execute(
                "SELECT content_hash FROM memories WHERE content_hash IS NOT NULL AND content_hash != ''"
            ).fetchall()
        }

        to_migrate = []
        for r in mems:
            if r["id"] in existing_ids:
                continue
            h = r["content_hash"]
            if h and h in existing_hashes:
                continue
            to_migrate.append(r)

        if not to_migrate:
            print(f"  {galaxy}: 0 unique (all {len(mems)} present)")
            conn.close()
            continue

        if dry_run:
            print(f"  {galaxy}: would migrate {len(to_migrate)} / {len(mems)}")
            total_migrated += len(to_migrate)
            conn.close()
            continue

        placeholders = ", ".join(["?"] * len(LIVE_COLS))
        col_list = ", ".join(LIVE_COLS)
        migrated = 0
        batch = []

        for r in to_migrate:
            tags_str = r["tags"] or ""
            metadata = r["metadata"] or ""
            if tags_str and not metadata:
                metadata = json.dumps({"original_tags": tags_str})

            values = (
                r["id"], r["content"], r["memory_type"] or "LONG_TERM",
                r["created_at"], r["updated_at"], r["accessed_at"],
                r["access_count"] or 0, r["emotional_valence"] or 0.0,
                r["importance"] or 0.5, r["neuro_score"] or 0.0,
                r["novelty_score"] or 0.5, r["recall_count"] or 0,
                r["half_life_days"] or 30.0, r["is_protected"] or 0,
                metadata, r["title"] or "",
                r["galactic_distance"] or 0.0,
                r["retention_score"] or 0.5,
                r["last_retention_sweep"],
                r["content_hash"], r["event_time"],
                r["ingestion_time"], r["is_private"] or 0,
                r["model_exclude"] or 0, galaxy,
                r["source_trust"] or "user", 0, "",
            )
            batch.append(values)

            if len(batch) >= 500:
                conn.executemany(
                    f"INSERT OR IGNORE INTO memories ({col_list}) VALUES ({placeholders})",
                    batch,
                )
                conn.commit()
                migrated += len(batch)
                batch = []

        if batch:
            conn.executemany(
                f"INSERT OR IGNORE INTO memories ({col_list}) VALUES ({placeholders})",
                batch,
            )
            conn.commit()
            migrated += len(batch)

        # Migrate tags
        tag_count = 0
        for r in to_migrate:
            tags_str = r["tags"] or ""
            if not tags_str:
                continue
            tag_list = [t.strip() for t in tags_str.split(",") if t.strip()]
            tag_tuples = [(r["id"], t) for t in tag_list]
            if tag_tuples:
                conn.executemany(
                    "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                    tag_tuples,
                )
                tag_count += len(tag_tuples)
        conn.commit()

        # Migrate holographic coords (old 5D -> new 6D, u=0.5 default)
        coord_count = 0
        for r in to_migrate:
            coords = src.execute(
                "SELECT x, y, z, w, v FROM holographic_coords WHERE memory_id = ?",
                (r["id"],),
            ).fetchone()
            if coords:
                conn.execute(
                    "INSERT OR IGNORE INTO holographic_coords (memory_id, x, y, z, w, v, u) VALUES (?, ?, ?, ?, ?, ?, 0.5)",
                    (r["id"], coords[0], coords[1], coords[2], coords[3], coords[4]),
                )
                coord_count += 1
        conn.commit()

        # Update FTS index
        try:
            conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
            conn.commit()
        except Exception:
            pass

        conn.close()
        print(f"  {galaxy}: migrated {migrated} memories, {tag_count} tags, {coord_count} coords")
        total_migrated += migrated

    src.close()
    print(f"  TOTAL: migrated {total_migrated}, skipped {total_skipped}")
    return total_migrated


def migrate_state_backups(dry_run=False):
    """Migrate unique memories from state galaxy backups."""
    print(f"\n{'='*60}")
    print("Migrating state galaxy backups")

    if not STATE_GALAXIES_DIR.exists():
        print("  State galaxies dir not found, skipping")
        return 0

    total = 0
    for galaxy_dir in sorted(STATE_GALAXIES_DIR.iterdir()):
        galaxy = galaxy_dir.name
        bak = galaxy_dir / "whitemagic.db.bak.1"
        if not bak.exists():
            continue

        mapped = map_galaxy(galaxy)
        # Skip state meta backups — old auto-generated galaxy summaries
        # already superseded by live meta (18K+ summaries there)
        if galaxy == "meta":
            print(f"  {galaxy} -> {mapped}: skipping (old auto-generated snapshots)")
            continue
        live_db = GALAXIES_DIR / mapped / "whitemagic.db"
        if not live_db.exists():
            if dry_run:
                print(f"  {galaxy} -> {mapped}: would create DB + migrate")
                continue
            live_db = ensure_galaxy_db(mapped)
            continue

        src = sqlite3.connect(str(bak))
        src.row_factory = sqlite3.Row
        # Check if memories table exists
        has_memories = src.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='memories'"
        ).fetchone()[0]
        if not has_memories:
            print(f"  {galaxy} -> {mapped}: no memories table, skipping")
            src.close()
            continue
        rows = src.execute("SELECT * FROM memories").fetchall()

        conn = sqlite3.connect(str(live_db))
        existing_ids = get_existing(conn, "memories", "id")

        to_migrate = [r for r in rows if r["id"] not in existing_ids]
        if not to_migrate:
            print(f"  {galaxy} -> {mapped}: 0 unique")
            src.close()
            conn.close()
            continue

        if dry_run:
            print(f"  {galaxy} -> {mapped}: would migrate {len(to_migrate)}")
            total += len(to_migrate)
            src.close()
            conn.close()
            continue

        live_cols = [d[1] for d in conn.execute("PRAGMA table_info(memories)").fetchall()]
        col_list = ", ".join(live_cols)
        placeholders = ", ".join(["?"] * len(live_cols))

        migrated = 0
        for r in to_migrate:
            vals = []
            for c in live_cols:
                if c == "version":
                    vals.append(0)
                elif c == "agent_id":
                    vals.append("")
                elif c == "galaxy":
                    vals.append(mapped)
                else:
                    vals.append(r[c] if c in r.keys() else None)
            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO memories ({col_list}) VALUES ({placeholders})",
                    vals,
                )
                migrated += 1
            except Exception as e:
                print(f"    ERROR on {r['id']}: {e}")

        conn.commit()
        try:
            conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
            conn.commit()
        except Exception:
            pass

        conn.close()
        src.close()
        print(f"  {galaxy} -> {mapped}: migrated {migrated}")
        total += migrated

    print(f"  TOTAL state migrations: {total}")
    return total


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("DRY RUN — no changes will be made")

    sources = [
        (MEMORY_DIR / "whitemagic.db.bak.20260709_143945", "Timestamped backup (62,467 memories, Nov 2025 – Jul 9 2026)"),
        (MEMORY_DIR / "whitemagic.db.corrupt.20260710", "Corrupt DB (764 extra memories from Jul 9-10)"),
    ]

    grand_total = 0
    for src, label in sources:
        if not src.exists():
            print(f"SKIP: {src} not found")
            continue
        grand_total += migrate_source(src, label, dry_run)

    grand_total += migrate_state_backups(dry_run)

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {grand_total} memories {'would be ' if dry_run else ''}migrated")

    if not dry_run:
        print("\nPost-migration verification:")
        for g in sorted(GALAXIES_DIR.iterdir()):
            db = g / "whitemagic.db"
            if db.exists():
                c = sqlite3.connect(str(db))
                count = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                print(f"  {g.name}: {count} memories")
                c.close()


if __name__ == "__main__":
    main()
