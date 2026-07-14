"""DuckDB backend for WhiteMagic memory — analytical tier.

DuckDB provides columnar storage with excellent analytical query
performance. This backend is used for:
- Cross-galaxy aggregation queries
- Pattern detection and statistical analysis
- Bulk analytical reads (no single-row point lookups)

It mirrors the SQLite schema but in columnar format. Data is synced
from SQLite periodically or on-demand.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from whitemagic.core.memory.backends.base import BaseBackend
from whitemagic.core.memory.unified_types import Memory, MemoryType
from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)

try:
    import duckdb
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False
    duckdb = None  # type: ignore[assignment]


class DuckDBBackend(BaseBackend):
    """DuckDB analytical backend for cross-galaxy queries.

    Not a primary write path — syncs from SQLite backends.
    Optimized for analytical queries: GROUP BY, aggregation, pattern detection.
    """

    def __init__(self, db_path: str | Path) -> None:
        if not _DUCKDB_AVAILABLE:
            raise ImportError(
                "duckdb is not installed. Install with: pip install duckdb"
            )
        self.db_path = str(db_path)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Any = None
        self._init_db()

    def _get_conn(self) -> Any:
        """Get or create the DuckDB connection."""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path, read_only=False)
        return self._conn

    def _init_db(self) -> None:
        """Initialize DuckDB schema."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id VARCHAR PRIMARY KEY,
                content VARCHAR,
                memory_type VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                accessed_at TIMESTAMP,
                access_count INTEGER,
                emotional_valence DOUBLE,
                importance DOUBLE,
                neuro_score DOUBLE,
                novelty_score DOUBLE,
                recall_count INTEGER,
                half_life_days DOUBLE,
                is_protected BOOLEAN,
                metadata JSON,
                title VARCHAR,
                galactic_distance DOUBLE,
                retention_score DOUBLE,
                content_hash VARCHAR,
                galaxy VARCHAR,
                is_private BOOLEAN,
                model_exclude BOOLEAN,
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                memory_id VARCHAR,
                tag VARCHAR,
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                source_id VARCHAR,
                target_id VARCHAR,
                strength DOUBLE,
            )
        """)
        # Index for galaxy filtering
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_galaxy ON memories(galaxy)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        logger.debug("DuckDB backend initialized at %s", self.db_path)

    def store(self, memory: Memory, content_hash: str | None = None) -> str:
        """Store or update a memory in DuckDB."""
        conn = self._get_conn()
        content_json = json.dumps(memory.content) if not isinstance(memory.content, str) else memory.content
        metadata_json = json.dumps(memory.metadata) if memory.metadata else "{}"

        # DuckDB uses INSERT OR REPLACE via DELETE + INSERT
        conn.execute("DELETE FROM memories WHERE id = ?", [memory.id])
        conn.execute("""
            INSERT INTO memories (
                id, content, memory_type, created_at, updated_at, accessed_at,
                access_count, emotional_valence, importance,
                neuro_score, novelty_score, recall_count, half_life_days, is_protected,
                metadata, title, galactic_distance, retention_score,
                content_hash, galaxy, is_private, model_exclude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            memory.id,
            content_json,
            memory.memory_type.name,
            memory.created_at,
            (memory.last_modified or memory.created_at),
            memory.accessed_at,
            memory.access_count,
            memory.emotional_valence,
            memory.importance,
            memory.neuro_score,
            memory.novelty_score,
            memory.recall_count,
            memory.half_life_days,
            memory.is_protected,
            metadata_json,
            memory.title,
            memory.galactic_distance,
            memory.retention_score,
            content_hash,
            getattr(memory, 'galaxy', 'universal'),
            memory.is_private,
            memory.model_exclude,
        ])

        # Update tags
        conn.execute("DELETE FROM tags WHERE memory_id = ?", [memory.id])
        if memory.tags:
            for tag in memory.tags:
                conn.execute("INSERT INTO tags (memory_id, tag) VALUES (?, ?)", [memory.id, tag])

        return memory.id

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a single memory by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM memories WHERE id = ?", [memory_id]).fetchone()
        if not row:
            return None
        return self._row_to_memory(row)

    def search(
        self,
        query: str = "",
        tags: set[str] | None = None,
        memory_type: MemoryType | str | None = None,
        limit: int = 20,
        galaxy: str | None = None,
        min_importance: float = 0.0,
        **kwargs: Any,
    ) -> list[Memory]:
        """Search memories in DuckDB."""
        conn = self._get_conn()
        conditions = []
        params: list[Any] = []

        if galaxy:
            conditions.append("galaxy = ?")
            params.append(galaxy)
        if min_importance > 0:
            conditions.append("importance >= ?")
            params.append(min_importance)
        if memory_type:
            mt = memory_type.name if isinstance(memory_type, MemoryType) else str(memory_type)
            conditions.append("memory_type = ?")
            params.append(mt)
        if query:
            conditions.append("content ILIKE ?")
            params.append(f"%{query}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM memories WHERE {where_clause} ORDER BY importance DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        results = [self._row_to_memory(row) for row in rows]

        # Filter by tags if specified (post-filter since DuckDB tag join is expensive)
        if tags:
            results = [m for m in results if tags.issubset(m.tags)]

        return results

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        conn = self._get_conn()
        conn.execute("DELETE FROM memories WHERE id = ?", [memory_id])
        conn.execute("DELETE FROM tags WHERE memory_id = ?", [memory_id])
        conn.execute("DELETE FROM associations WHERE source_id = ?", [memory_id])
        return True

    def get_stats(self) -> dict[str, Any]:
        """Return statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        by_galaxy = conn.execute(
            "SELECT galaxy, COUNT(*) FROM memories GROUP BY galaxy ORDER BY COUNT(*) DESC"
        ).fetchall()
        return {
            "total_memories": total,
            "by_galaxy": {row[0]: row[1] for row in by_galaxy},
            "backend": "duckdb",
        }

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def sync_from_sqlite(self, sqlite_path: str) -> int:
        """Sync all memories from a SQLite database into DuckDB.

        Returns the number of memories synced.
        """
        import sqlite3

        conn = self._get_conn()
        sqlite_conn = safe_connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row

        rows = sqlite_conn.execute("SELECT * FROM memories").fetchall()
        count = 0
        for row in rows:
            memory = self._sqlite_row_to_memory(row)
            self.store(memory, content_hash=row["content_hash"])
            count += 1

        # Sync tags
        tag_rows = sqlite_conn.execute("SELECT * FROM tags").fetchall()
        for row in tag_rows:
            conn.execute(
                "INSERT INTO tags (memory_id, tag) VALUES (?, ?)",
                [row["memory_id"], row["tag"]],
            )

        sqlite_conn.close()
        logger.info("Synced %d memories from SQLite (%s) to DuckDB (%s)", count, sqlite_path, self.db_path)
        return count

    def cross_galaxy_stats(self) -> dict[str, Any]:
        """Analytical query: statistics across all galaxies."""
        conn = self._get_conn()
        result = conn.execute("""
            SELECT
                galaxy,
                COUNT(*) as count,
                AVG(importance) as avg_importance,
                AVG(emotional_valence) as avg_valence,
                MIN(created_at) as earliest,
                MAX(created_at) as latest,
                AVG(access_count) as avg_access
            FROM memories
            GROUP BY galaxy
            ORDER BY count DESC
        """).fetchall()
        return {
            row[0]: {
                "count": row[1],
                "avg_importance": round(row[2], 3) if row[2] else 0,
                "avg_valence": round(row[3], 3) if row[3] else 0,
                "earliest": str(row[4]),
                "latest": str(row[5]),
                "avg_access": round(row[6], 1) if row[6] else 0,
            }
            for row in result
        }

    def _row_to_memory(self, row: Any) -> Memory:
        """Convert a DuckDB row to a Memory object."""
        # DuckDB returns tuples, not dicts — need to map by position
        metadata = json.loads(row[14]) if row[14] else {}
        content = row[1]
        # Try to parse JSON content
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Ignored TypeError in duckdb_backend.py:297")

        return Memory(
            id=row[0],
            content=content,
            memory_type=MemoryType[row[2]] if row[2] in MemoryType.__members__ else MemoryType.SHORT_TERM,
            created_at=row[3],
            tags=set(),
            emotional_valence=row[7] or 0.0,
            importance=row[8] or 0.5,
            metadata=metadata,
            title=row[15],
            galaxy=row[19] or "universal",
        )

    def _sqlite_row_to_memory(self, row: Any) -> Memory:
        """Convert a SQLite Row to a Memory object."""
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        content = row["content"]
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Ignored TypeError in duckdb_backend.py:319")

        mt_str = row["memory_type"] or "SHORT_TERM"
        try:
            mt = MemoryType[mt_str]
        except (KeyError, ValueError):
            mt = MemoryType.SHORT_TERM

        return Memory(
            id=row["id"],
            content=content,
            memory_type=mt,
            created_at=row["created_at"],
            tags=set(),
            emotional_valence=row["emotional_valence"] or 0.0,
            importance=row["importance"] or 0.5,
            metadata=metadata,
            title=row["title"],
            galaxy=row["galaxy"] or "universal",
        )
