"""Migrate monolithic SQLite DB to per-galaxy databases.

Reads all memories from the monolithic whitemagic.db and writes them
to per-galaxy databases at ~/.whitemagic/users/local/galaxies/{name}/whitemagic.db

Also migrates: tags, holographic_coords, memory_embeddings.

Usage:
    python scripts/migrate_to_per_galaxy.py [--dry-run] [--galaxy NAME]
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
MONOLITHIC_DB = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"
GALAXIES_DIR = Path.home() / ".whitemagic" / "users" / "local" / "galaxies"

# Standard PRAGMAs for new databases
WAL_PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA mmap_size=268435456",
    "PRAGMA cache_size=-65536",
    "PRAGMA temp_store=MEMORY",
    "PRAGMA busy_timeout=30000",
    "PRAGMA wal_autocheckpoint=1000",
    "PRAGMA foreign_keys=ON",
]


def get_galaxy_backends(mono_conn: sqlite3.Connection) -> dict[str, sqlite3.Connection]:
    """Create or get per-galaxy SQLite connections."""
    galaxies = mono_conn.execute(
        "SELECT DISTINCT galaxy FROM memories ORDER BY galaxy"
    ).fetchall()
    
    connections = {}
    for (galaxy,) in galaxies:
        if not galaxy or galaxy == "default":
            galaxy = "universal"
        
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in galaxy)
        galaxy_dir = GALAXIES_DIR / safe_name
        galaxy_dir.mkdir(parents=True, exist_ok=True)
        db_path = galaxy_dir / "whitemagic.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        for pragma in WAL_PRAGMAS:
            try:
                conn.execute(pragma)
            except sqlite3.OperationalError:
                pass
        
        # Create schema (same as monolithic)
        init_schema(conn)
        connections[galaxy] = conn
        logger.info("Opened galaxy DB: %s (%s)", galaxy, db_path)
    
    return connections


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize the schema for a per-galaxy database."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT,
            title TEXT,
            tags TEXT,
            created_at TEXT,
            updated_at TEXT,
            memory_type TEXT,
            importance REAL,
            access_count INTEGER,
            accessed_at TEXT,
            emotional_valence REAL,
            neuro_score REAL,
            novelty_score REAL,
            recall_count INTEGER,
            half_life_days REAL,
            is_protected INTEGER,
            galactic_distance REAL,
            retention_score REAL,
            last_retention_sweep TEXT,
            metadata TEXT,
            event_time TEXT,
            ingestion_time TEXT,
            is_private INTEGER,
            model_exclude INTEGER,
            content_hash TEXT,
            galaxy TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            memory_id TEXT,
            tag TEXT,
            PRIMARY KEY (memory_id, tag)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS holographic_coords (
            memory_id TEXT PRIMARY KEY,
            x REAL, y REAL, z REAL, w REAL, v REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_embeddings (
            memory_id TEXT PRIMARY KEY,
            embedding BLOB,
            model TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS associations (
            source_id TEXT,
            target_id TEXT,
            strength REAL,
            created_at TEXT,
            PRIMARY KEY (source_id, target_id)
        )
    """)
    # FTS5 index
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content, title, metadata,
            content='memories',
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)
    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_galaxy ON memories(galaxy)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(content_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
    conn.commit()


def migrate_memories(
    mono_conn: sqlite3.Connection,
    galaxy_conns: dict[str, sqlite3.Connection],
    galaxy_filter: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Migrate memories from monolithic to per-galaxy DBs."""
    counts = {}
    
    for galaxy, gconn in galaxy_conns.items():
        if galaxy_filter and galaxy != galaxy_filter:
            continue
        
        # Count source memories
        count = mono_conn.execute(
            "SELECT COUNT(*) FROM memories WHERE galaxy = ?", [galaxy]
        ).fetchone()[0]
        logger.info("Migrating %d memories for galaxy '%s'...", count, galaxy)
        
        if dry_run:
            counts[galaxy] = count
            continue
        
        # Batch migrate memories
        batch_size = 500
        offset = 0
        migrated = 0
        start_time = time.time()
        
        # Get column names from source
        sample_row = mono_conn.execute(
            "SELECT * FROM memories WHERE galaxy = ? LIMIT 1", [galaxy]
        ).fetchone()
        if not sample_row:
            counts[galaxy] = 0
            continue
        source_cols = list(sample_row.keys())
        
        # Get target columns
        target_cols = [c[1] for c in gconn.execute("PRAGMA table_info(memories)").fetchall()]
        # Only migrate columns that exist in both
        common_cols = [c for c in source_cols if c in target_cols]
        placeholders = ", ".join(["?"] * len(common_cols))
        col_names = ", ".join(common_cols)
        
        while offset < count:
            rows = mono_conn.execute(
                f"SELECT {', '.join(source_cols)} FROM memories WHERE galaxy = ? ORDER BY id LIMIT ? OFFSET ?",
                [galaxy, batch_size, offset],
            ).fetchall()
            
            if not rows:
                break
            
            for row in rows:
                row_dict = dict(zip(source_cols, row))
                values = [row_dict[c] for c in common_cols]
                gconn.execute(
                    f"INSERT OR REPLACE INTO memories ({col_names}) VALUES ({placeholders})",
                    values,
                )
            
            gconn.commit()
            migrated += len(rows)
            offset += batch_size
            
            if migrated % 5000 == 0 or migrated == count:
                elapsed = time.time() - start_time
                rate = migrated / elapsed if elapsed > 0 else 0
                logger.info(
                    "  %s: %d/%d (%.1f%%) — %.0f rec/s",
                    galaxy, migrated, count, 100 * migrated / count, rate,
                )
        
        counts[galaxy] = migrated
        elapsed = time.time() - start_time
        logger.info("  %s: COMPLETE — %d memories in %.1fs", galaxy, migrated, elapsed)
    
    return counts


def migrate_tags(
    mono_conn: sqlite3.Connection,
    galaxy_conns: dict[str, sqlite3.Connection],
    dry_run: bool = False,
) -> int:
    """Migrate tags for migrated memories."""
    total = 0
    for galaxy, gconn in galaxy_conns.items():
        # Get tags for memories in this galaxy
        count = mono_conn.execute("""
            SELECT COUNT(*) FROM tags t
            JOIN memories m ON t.memory_id = m.id
            WHERE m.galaxy = ?
        """, [galaxy]).fetchone()[0]
        
        if dry_run:
            total += count
            continue
        
        rows = mono_conn.execute("""
            SELECT t.memory_id, t.tag FROM tags t
            JOIN memories m ON t.memory_id = m.id
            WHERE m.galaxy = ?
        """, [galaxy]).fetchall()
        
        for row in rows:
            gconn.execute(
                "INSERT OR REPLACE INTO tags (memory_id, tag) VALUES (?, ?)",
                [row["memory_id"], row["tag"]],
            )
        gconn.commit()
        total += len(rows)
        logger.info("  Migrated %d tags for galaxy '%s'", len(rows), galaxy)
    
    return total


def migrate_coords(
    mono_conn: sqlite3.Connection,
    galaxy_conns: dict[str, sqlite3.Connection],
    dry_run: bool = False,
) -> int:
    """Migrate holographic coordinates."""
    total = 0
    for galaxy, gconn in galaxy_conns.items():
        count = mono_conn.execute("""
            SELECT COUNT(*) FROM holographic_coords hc
            JOIN memories m ON hc.memory_id = m.id
            WHERE m.galaxy = ?
        """, [galaxy]).fetchone()[0]
        
        if dry_run:
            total += count
            continue
        
        rows = mono_conn.execute("""
            SELECT hc.* FROM holographic_coords hc
            JOIN memories m ON hc.memory_id = m.id
            WHERE m.galaxy = ?
        """, [galaxy]).fetchall()
        
        for row in rows:
            gconn.execute("""
                INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [row["memory_id"], row["x"], row["y"], row["z"], row["w"], row["v"]])
        gconn.commit()
        total += len(rows)
        logger.info("  Migrated %d coords for galaxy '%s'", len(rows), galaxy)
    
    return total


def migrate_embeddings(
    mono_conn: sqlite3.Connection,
    galaxy_conns: dict[str, sqlite3.Connection],
    dry_run: bool = False,
) -> int:
    """Migrate memory embeddings."""
    total = 0
    for galaxy, gconn in galaxy_conns.items():
        count = mono_conn.execute("""
            SELECT COUNT(*) FROM memory_embeddings me
            JOIN memories m ON me.memory_id = m.id
            WHERE m.galaxy = ?
        """, [galaxy]).fetchone()[0]
        
        if dry_run:
            total += count
            continue
        
        rows = mono_conn.execute("""
            SELECT me.* FROM memory_embeddings me
            JOIN memories m ON me.memory_id = m.id
            WHERE m.galaxy = ?
        """, [galaxy]).fetchall()
        
        for row in rows:
            gconn.execute("""
                INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model, created_at)
                VALUES (?, ?, ?, ?)
            """, [row["memory_id"], row["embedding"], row["model"], row["created_at"]])
        gconn.commit()
        total += len(rows)
        logger.info("  Migrated %d embeddings for galaxy '%s'", len(rows), galaxy)
    
    return total


def verify_migration(
    mono_conn: sqlite3.Connection,
    galaxy_conns: dict[str, sqlite3.Connection],
) -> bool:
    """Verify migration by comparing counts."""
    all_ok = True
    for galaxy, gconn in galaxy_conns.items():
        mono_count = mono_conn.execute(
            "SELECT COUNT(*) FROM memories WHERE galaxy = ?", [galaxy]
        ).fetchone()[0]
        galaxy_count = gconn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        
        status = "OK" if mono_count == galaxy_count else "MISMATCH"
        if mono_count != galaxy_count:
            all_ok = False
        logger.info("  Verify %s: mono=%d galaxy=%d — %s", galaxy, mono_count, galaxy_count, status)
    
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate monolithic DB to per-galaxy DBs")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't migrate")
    parser.add_argument("--galaxy", type=str, help="Migrate only this galaxy")
    parser.add_argument("--verify", action="store_true", help="Only verify existing migration")
    args = parser.parse_args()
    
    if not MONOLITHIC_DB.exists():
        logger.error("Monolithic DB not found: %s", MONOLITHIC_DB)
        return 1
    
    logger.info("Source: %s (%.1f MB)", MONOLITHIC_DB, MONOLITHIC_DB.stat().st_size / 1e6)
    
    mono_conn = sqlite3.connect(str(MONOLITHIC_DB))
    mono_conn.row_factory = sqlite3.Row
    
    galaxy_conns = get_galaxy_backends(mono_conn)
    
    if args.verify:
        logger.info("Verifying migration...")
        ok = verify_migration(mono_conn, galaxy_conns)
        if ok:
            logger.info("All galaxies verified OK!")
        else:
            logger.warning("Some galaxies have count mismatches!")
        for conn in galaxy_conns.values():
            conn.close()
        mono_conn.close()
        return 0 if ok else 1
    
    start = time.time()
    
    # 1. Migrate memories
    logger.info("=== Phase 1: Migrating memories ===")
    mem_counts = migrate_memories(mono_conn, galaxy_conns, args.galaxy, args.dry_run)
    total_mem = sum(mem_counts.values())
    logger.info("Total memories migrated: %d", total_mem)
    
    # 2. Migrate tags
    logger.info("=== Phase 2: Migrating tags ===")
    total_tags = migrate_tags(mono_conn, galaxy_conns, args.dry_run)
    logger.info("Total tags migrated: %d", total_tags)
    
    # 3. Migrate coords
    logger.info("=== Phase 3: Migrating holographic coords ===")
    total_coords = migrate_coords(mono_conn, galaxy_conns, args.dry_run)
    logger.info("Total coords migrated: %d", total_coords)
    
    # 4. Migrate embeddings
    logger.info("=== Phase 4: Migrating embeddings ===")
    total_emb = migrate_embeddings(mono_conn, galaxy_conns, args.dry_run)
    logger.info("Total embeddings migrated: %d", total_emb)
    
    # 5. Verify
    if not args.dry_run:
        logger.info("=== Phase 5: Verification ===")
        verify_migration(mono_conn, galaxy_conns)
    
    elapsed = time.time() - start
    logger.info("=== Migration complete in %.1fs ===", elapsed)
    logger.info("  Memories: %d", total_mem)
    logger.info("  Tags: %d", total_tags)
    logger.info("  Coords: %d", total_coords)
    logger.info("  Embeddings: %d", total_emb)
    
    for conn in galaxy_conns.values():
        conn.close()
    mono_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
