#!/usr/bin/env python3
"""The Great Realignment — Full Holographic Re-Indexing.

Recalculates spatial coordinates (holographic coords) for all memories
and rebuilds the FTS search index. Run after bulk imports or major DB changes.

Usage:
    python3 scripts/reindex_data_sea.py
    python3 scripts/reindex_data_sea.py --db /path/to/whitemagic.db
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

try:
    from whitemagic.config.paths import DB_PATH
except ImportError:
    DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"


def reindex(db_path: Path) -> None:
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-65536")  # 64MB
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB
    conn.execute("PRAGMA busy_timeout=60000")

    print("\n[1/2] Rebuilding FTS index...")
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    print(f"  Total memories: {total}")

    conn.execute("DELETE FROM memories_fts")
    conn.commit()

    t0 = time.time()
    conn.execute("""
        INSERT INTO memories_fts (id, title, content, tags_text)
        SELECT m.id, COALESCE(m.title, ''), COALESCE(m.content, ''),
               COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE memory_id = m.id), '')
        FROM memories m
    """)
    conn.commit()
    conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('optimize')")
    elapsed = time.time() - t0
    fts_count = conn.execute("SELECT COUNT(*) FROM memories_fts").fetchone()[0]
    print(f"  FTS rebuilt: {fts_count} entries in {elapsed:.1f}s")

    print("\n[2/2] Recalculating holographic coordinates...")
    hc_count = conn.execute("SELECT COUNT(*) FROM holographic_coords").fetchone()[0]
    print(f"  Existing coords: {hc_count}")

    # Create coords for memories that lack them
    t0 = time.time()
    conn.execute("""
        INSERT OR IGNORE INTO holographic_coords (memory_id, x, y, z, w, v)
        SELECT m.id,
               RANDOM() * 1.0,
               RANDOM() * 1.0,
               RANDOM() * 1.0,
               m.importance,
               m.neuro_score
        FROM memories m
        WHERE NOT EXISTS (
            SELECT 1 FROM holographic_coords hc WHERE hc.memory_id = m.id
        )
    """)
    new_coords = conn.total_changes
    conn.commit()
    elapsed = time.time() - t0
    print(f"  New coords created: {new_coords} in {elapsed:.1f}s")

    # Integrity check
    print("\nVerifying integrity...")
    result = conn.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"  {result}")

    conn.close()
    print("\nRealignment complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="The Great Realignment — Reindex Data Sea"
    )
    parser.add_argument("--db", type=str, default=None, help="Path to whitemagic.db")
    args = parser.parse_args()

    path = Path(args.db) if args.db else Path(DB_PATH)
    if not path.exists():
        print(f"Error: Database not found at {path}", file=sys.stderr)
        sys.exit(1)

    reindex(path)


if __name__ == "__main__":
    main()
