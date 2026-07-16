"""Multi-galaxy DB scanner — utilities for scanning all galaxy DBs.

Provides functions to iterate over all active galaxy databases, read
holographic coordinates, associations, and memories from every galaxy
in a unified manner. This replaces the old monolithic DB_PATH pattern
where modules only read from a single database.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)


def get_galaxy_db_dir() -> Path:
    """Get the directory containing all galaxy DBs."""
    from whitemagic.config.paths import WM_ROOT
    return WM_ROOT / "users" / "local" / "galaxies"


def list_galaxy_dbs() -> list[tuple[str, Path]]:
    """List all galaxy databases on disk.
    
    Returns:
        List of (galaxy_name, db_path) tuples.
    """
    gd = get_galaxy_db_dir()
    if not gd.exists():
        return []
    
    result = []
    for d in sorted(gd.iterdir()):
        if not d.is_dir():
            continue
        db = d / "whitemagic.db"
        if db.exists():
            result.append((d.name, db))
    return result


def scan_all_coords() -> dict[str, tuple[str, tuple[float, ...]]]:
    """Read holographic coordinates from ALL galaxy DBs.
    
    Returns:
        Dict mapping memory_id → (galaxy_name, (x, y, z, w, v[, u]))
    """
    result = {}
    for gname, db_path in list_galaxy_dbs():
        try:
            conn = safe_connect(str(db_path), read_only=True)
            try:
                rows = conn.execute(
                    "SELECT memory_id, x, y, z, w, COALESCE(v, 0.5), COALESCE(u, 0.5) FROM holographic_coords"
                ).fetchall()
            except sqlite3.OperationalError:
                rows = conn.execute(
                    "SELECT memory_id, x, y, z, w, COALESCE(v, 0.5) FROM holographic_coords"
                ).fetchall()
                rows = [(r[0], r[1], r[2], r[3], r[4], r[5], 0.5) for r in rows]
            
            for row in rows:
                mid = row[0]
                coords = tuple(row[1:])
                result[mid] = (gname, coords)
            conn.close()
        except Exception as e:
            logger.debug("Failed to read coords from %s: %s", gname, e)
    
    return result


def count_all_memories() -> int:
    """Count total memories across ALL galaxy DBs."""
    total = 0
    for gname, db_path in list_galaxy_dbs():
        try:
            conn = safe_connect(str(db_path), read_only=True)
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            total += count
            conn.close()
        except Exception:
            pass
    return total


def get_galaxy_conn(galaxy_name: str) -> sqlite3.Connection | None:
    """Get a connection to a specific galaxy DB."""
    gd = get_galaxy_db_dir()
    db = gd / galaxy_name / "whitemagic.db"
    if not db.exists():
        return None
    conn = safe_connect(str(db))
    return conn


def iter_galaxy_memories(galaxy_name: str, batch_size: int = 1000) -> Iterator[dict[str, Any]]:
    """Iterate over memories in a specific galaxy in batches."""
    conn = get_galaxy_conn(galaxy_name)
    if conn is None:
        return
    
    try:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(memories)").fetchall()]
        offset = 0
        while True:
            rows = conn.execute(
                f"SELECT {','.join(cols)} FROM memories LIMIT {batch_size} OFFSET {offset}"
            ).fetchall()
            if not rows:
                break
            for row in rows:
                yield dict(zip(cols, row))
            offset += len(rows)
    finally:
        conn.close()


def insert_association(galaxy_name: str, source_id: str, target_id: str,
                       assoc_type: str, strength: float, edge_type: str = "intra_galaxy") -> bool:
    """Insert an association into a specific galaxy DB."""
    conn = get_galaxy_conn(galaxy_name)
    if conn is None:
        return False
    
    try:
        # Ensure edge_type column exists
        try:
            conn.execute("SELECT edge_type FROM associations LIMIT 0")
        except sqlite3.OperationalError:
            try:
                conn.execute("ALTER TABLE associations ADD COLUMN edge_type TEXT DEFAULT 'intra_galaxy'")
            except sqlite3.OperationalError:
                pass  # Column might already exist
        
        existing = conn.execute(
            "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
            (source_id, target_id),
        ).fetchone()[0]
        
        if existing > 0:
            return False
        
        try:
            conn.execute(
                "INSERT OR IGNORE INTO associations (source_id, target_id, relation_type, strength, edge_type) VALUES (?, ?, ?, ?, ?)",
                (source_id, target_id, assoc_type, strength, edge_type),
            )
        except sqlite3.OperationalError:
            conn.execute(
                "INSERT OR IGNORE INTO associations (source_id, target_id, strength) VALUES (?, ?, ?)",
                (source_id, target_id, strength),
            )
        conn.commit()
        return True
    except Exception as e:
        logger.debug("Failed to insert association in %s: %s", galaxy_name, e)
        return False
    finally:
        conn.close()
