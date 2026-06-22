"""Holographic Coordinates Manager — 5D vector storage for memory embeddings.

Handles storage and retrieval of holographic coordinates (x, y, z, w, v) for
memory embeddings. Extracted from sqlite_backend.py for better separation of concerns.
"""

import logging

logger = logging.getLogger(__name__)


class HolographicCoordsManager:
    """Manages holographic coordinate storage for SQLite backend."""

    def __init__(self, pool):
        self.pool = pool

    def store_coords(self, memory_id: str, x: float, y: float, z: float, w: float, v: float = 0.5) -> None:
        """Store holographic coordinates (5D: x, y, z, w, v)."""
        with self.pool.connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (memory_id, x, y, z, w, v),
                )

    def get_coords(self, memory_id: str) -> tuple | None:
        """Get holographic coordinates for a memory (5D: x, y, z, w, v)."""
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT x, y, z, w, COALESCE(v, 0.5) FROM holographic_coords WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row:
                return (row[0], row[1], row[2], row[3], row[4])
            return None

    def get_all_coords(self) -> dict[str, tuple]:
        """Get all holographic coordinates (5D: x, y, z, w, v)."""
        with self.pool.connection() as conn:
            cursor = conn.execute("SELECT memory_id, x, y, z, w, COALESCE(v, 0.5) FROM holographic_coords")
            return {row[0]: (row[1], row[2], row[3], row[4], row[5]) for row in cursor}
