"""Holographic Coordinates Manager — 6D vector storage for memory embeddings.

Handles storage and retrieval of holographic coordinates (x, y, z, w, v, u) for
memory embeddings. Extracted from sqlite_backend.py for better separation of concerns.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


class HolographicCoordsManager:
    """Manages holographic coordinate storage for SQLite backend."""

    def __init__(self, pool):
        self.pool = pool

    def store_coords(self, memory_id: str, x: float, y: float, z: float, w: float, v: float = 0.5, u: float = 0.5) -> None:
        """Store holographic coordinates (6D: x, y, z, w, v, u)."""
        with self.pool.connection() as conn:
            with conn:
                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v, u)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (memory_id, x, y, z, w, v, u),
                    )
                except sqlite3.OperationalError:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (memory_id, x, y, z, w, v),
                    )

    def get_coords(self, memory_id: str) -> tuple | None:
        """Get holographic coordinates for a memory (6D: x, y, z, w, v, u)."""
        with self.pool.connection() as conn:
            try:
                row = conn.execute(
                    "SELECT x, y, z, w, COALESCE(v, 0.5), COALESCE(u, 0.5) FROM holographic_coords WHERE memory_id = ?",
                    (memory_id,),
                ).fetchone()
            except sqlite3.OperationalError:
                row = conn.execute(
                    "SELECT x, y, z, w, COALESCE(v, 0.5) FROM holographic_coords WHERE memory_id = ?",
                    (memory_id,),
                ).fetchone()
                if row:
                    return (row[0], row[1], row[2], row[3], row[4], 0.5)
                return None
            if row:
                return (row[0], row[1], row[2], row[3], row[4], row[5])
            return None

    def get_all_coords(self) -> dict[str, tuple]:
        """Get all holographic coordinates (6D: x, y, z, w, v, u)."""
        with self.pool.connection() as conn:
            try:
                cursor = conn.execute("SELECT memory_id, x, y, z, w, COALESCE(v, 0.5), COALESCE(u, 0.5) FROM holographic_coords")
                return {row[0]: (row[1], row[2], row[3], row[4], row[5], row[6]) for row in cursor}
            except sqlite3.OperationalError:
                cursor = conn.execute("SELECT memory_id, x, y, z, w, COALESCE(v, 0.5) FROM holographic_coords")
                return {row[0]: (row[1], row[2], row[3], row[4], row[5], 0.5) for row in cursor}
