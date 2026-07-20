"""Galaxy scan helper — shared utility for multi-galactic engine queries.

Provides utilities for engines that need to scan across all per-galaxy
SQLite databases instead of querying a single monolithic DB.

Usage:
    from whitemagic.core.memory.galaxy_scan import scan_query_all, get_galaxy_db_paths

    # Run a query across all galaxy DBs
    rows = scan_query_all("SELECT id, title FROM memories WHERE title IS NULL")

    # Discover all galaxy DB paths
    paths = get_galaxy_db_paths()
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)

_db_paths_cache: dict[str, str] | None = None
_db_paths_cache_time: float = 0.0
_db_paths_cache_ttl: float = 60.0


def get_galaxy_db_paths() -> dict[str, str]:
    """Discover all per-galaxy database paths on disk.

    Returns dict mapping galaxy name to database file path.
    Includes the monolithic DB as 'default' for backward compat.
    Results are cached for 60 seconds.
    """
    global _db_paths_cache, _db_paths_cache_time

    now = time.time()
    if _db_paths_cache is not None and (now - _db_paths_cache_time) < _db_paths_cache_ttl:
        return _db_paths_cache

    paths: dict[str, str] = {}

    try:
        from whitemagic.config.paths import DB_PATH

        paths["default"] = str(DB_PATH)
    except Exception:  # noqa: BLE001
        logger.debug("Ignored error in galaxy_scan.py:53")

    try:
        from whitemagic.core.user_profile import get_user_dir

        galaxies_dir = get_user_dir("local") / "galaxies"
    except Exception:  # noqa: BLE001
        try:
            from whitemagic.config.paths import DB_PATH

            galaxies_dir = Path(DB_PATH).parent / "galaxies"
        except Exception:  # noqa: BLE001
            _db_paths_cache = paths
            _db_paths_cache_time = now
            return paths

    if galaxies_dir.exists():
        for galaxy_dir in galaxies_dir.iterdir():
            if not galaxy_dir.is_dir():
                continue
            db_file = galaxy_dir / "whitemagic.db"
            if db_file.exists():
                paths[galaxy_dir.name] = str(db_file)

    _db_paths_cache = paths
    _db_paths_cache_time = now
    return paths


def invalidate_galaxy_db_paths_cache() -> None:
    """Invalidate the cached galaxy DB paths."""
    global _db_paths_cache, _db_paths_cache_time
    _db_paths_cache = None
    _db_paths_cache_time = 0.0


@contextmanager
def galaxy_connection(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for a single galaxy DB connection."""
    conn = safe_connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def scan_query_all(
    sql: str,
    params: tuple | list = (),
) -> list[sqlite3.Row]:
    """Run a SQL query across all galaxy DBs and concatenate results.

    Args:
        sql: SQL query string (uses ? placeholders).
        params: Query parameters.

    Returns:
        List of rows from all galaxy DBs concatenated.
    """
    all_rows: list[sqlite3.Row] = []
    for galaxy_name, db_path in get_galaxy_db_paths().items():
        try:
            with galaxy_connection(db_path) as conn:
                rows = conn.execute(sql, params).fetchall()
                all_rows.extend(rows)
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "Galaxy scan query failed for '%s': %s",
                galaxy_name,
                e,
                exc_info=True,
            )
    return all_rows


def scan_query_one(
    sql: str,
    params: tuple | list = (),
) -> sqlite3.Row | None:
    """Run a SQL query across galaxy DBs, return first non-empty result."""
    for galaxy_name, db_path in get_galaxy_db_paths().items():
        try:
            with galaxy_connection(db_path) as conn:
                row = conn.execute(sql, params).fetchone()
                if row:
                    return row
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "Galaxy scan query_one failed for '%s': %s",
                galaxy_name,
                e,
                exc_info=True,
            )
    return None


def scan_count_all(
    sql: str,
    params: tuple | list = (),
) -> int:
    """Run a COUNT query across all galaxy DBs and sum results.

    The SQL should return a single integer column (COUNT(*)).
    """
    total = 0
    for galaxy_name, db_path in get_galaxy_db_paths().items():
        try:
            with galaxy_connection(db_path) as conn:
                row = conn.execute(sql, params).fetchone()
                if row:
                    total += row[0]
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "Galaxy scan count failed for '%s': %s",
                galaxy_name,
                e,
                exc_info=True,
            )
    return total


def execute_across_galaxies(
    sql: str,
    params: tuple | list = (),
) -> int:
    """Execute a write SQL (INSERT/UPDATE/DELETE) across all galaxy DBs.

    Returns total rows affected across all galaxies.
    """
    total_affected = 0
    for galaxy_name, db_path in get_galaxy_db_paths().items():
        try:
            with galaxy_connection(db_path) as conn:
                cur = conn.execute(sql, params)
                conn.commit()
                total_affected += cur.rowcount
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "Galaxy execute failed for '%s': %s",
                galaxy_name,
                e,
                exc_info=True,
            )
    return total_affected
