"""PostgreSQL backend for WhiteMagic memory — concurrency tier.

PostgreSQL provides true MVCC concurrency, eliminating the WAL-mode
race conditions that caused SQLite corruption. This backend is used
for:
- Multi-user scenarios (multiple agents writing simultaneously)
- Remote/shared memory instances
- High-concurrency write workloads

Runs on localhost by default, locked to a single port (5433 to avoid
conflicts with system PostgreSQL on 5432).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from whitemagic.core.memory.backends.base import BaseBackend
from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG_AVAILABLE = True
except ImportError:
    _PSYCOPG_AVAILABLE = False
    psycopg2 = None  # type: ignore[assignment]

# Default connection config — localhost only, locked to port 5433
DEFAULT_PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "whitemagic",
    "user": "whitemagic",
    "password": "",  # Set via WM_PG_PASSWORD env var
}


class PostgresBackend(BaseBackend):
    """PostgreSQL backend for high-concurrency memory operations.

    Connection is locked to localhost:5433 by default.
    Set WM_PG_PASSWORD environment variable for authentication.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not _PSYCOPG_AVAILABLE:
            raise ImportError(
                "psycopg2 is not installed. Install with: pip install psycopg2-binary"
            )

        import os
        cfg = dict(DEFAULT_PG_CONFIG)
        if config:
            cfg.update(config)

        # Allow env var overrides
        cfg["host"] = os.environ.get("WM_PG_HOST", cfg["host"])
        cfg["port"] = int(os.environ.get("WM_PG_PORT", cfg["port"]))
        cfg["dbname"] = os.environ.get("WM_PG_DB", cfg["dbname"])
        cfg["user"] = os.environ.get("WM_PG_USER", cfg["user"])
        cfg["password"] = os.environ.get("WM_PG_PASSWORD", cfg["password"])

        self._config = cfg
        self._conn: Any = None
        self._init_db()

    def _get_conn(self) -> Any:
        """Get or create the PostgreSQL connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self._config)
            self._conn.autocommit = False
            # Use dict cursor for easier row access
            self._conn.cursor_factory = psycopg2.extras.RealDictCursor
        return self._conn

    def _init_db(self) -> None:
        """Initialize PostgreSQL schema."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    memory_type TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    accessed_at TIMESTAMPTZ DEFAULT NOW(),
                    access_count INTEGER DEFAULT 0,
                    emotional_valence REAL DEFAULT 0.0,
                    importance REAL DEFAULT 0.5,
                    neuro_score REAL DEFAULT 1.0,
                    novelty_score REAL DEFAULT 1.0,
                    recall_count INTEGER DEFAULT 0,
                    half_life_days REAL DEFAULT 30.0,
                    is_protected BOOLEAN DEFAULT FALSE,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    title TEXT,
                    galactic_distance REAL DEFAULT 0.0,
                    retention_score REAL DEFAULT 0.5,
                    last_retention_sweep TIMESTAMPTZ,
                    content_hash TEXT,
                    event_time TEXT,
                    ingestion_time TIMESTAMPTZ DEFAULT NOW(),
                    is_private BOOLEAN DEFAULT FALSE,
                    model_exclude BOOLEAN DEFAULT FALSE,
                    galaxy TEXT DEFAULT 'universal'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
                    tag TEXT,
                    PRIMARY KEY (memory_id, tag)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS associations (
                    source_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
                    target_id TEXT,
                    strength REAL DEFAULT 0.5,
                    PRIMARY KEY (source_id, target_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memory_coords (
                    memory_id TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
                    x REAL, y REAL, z REAL, w REAL, v REAL
                )
            """)
            # Indexes for common queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_galaxy ON memories(galaxy)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(content_hash)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
            # Full-text search using PostgreSQL's built-in tsvector
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_fts
                ON memories USING gin(to_tsvector('english', coalesce(content,'') || ' ' || coalesce(title,'')))
            """)
        conn.commit()
        logger.info("PostgreSQL backend initialized on %s:%s", self._config["host"], self._config["port"])

    def store(self, memory: Memory, content_hash: str | None = None) -> str:
        """Store or update a memory."""
        conn = self._get_conn()
        content_json = json.dumps(memory.content) if not isinstance(memory.content, str) else memory.content
        metadata_json = json.dumps(memory.metadata) if memory.metadata else "{}"

        with conn.cursor() as cur:
            # UPSERT
            cur.execute("""
                INSERT INTO memories (
                    id, content, memory_type, created_at, updated_at, accessed_at,
                    access_count, emotional_valence, importance,
                    neuro_score, novelty_score, recall_count, half_life_days, is_protected,
                    metadata, title, galactic_distance, retention_score,
                    content_hash, galaxy, is_private, model_exclude
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    memory_type = EXCLUDED.memory_type,
                    updated_at = EXCLUDED.updated_at,
                    accessed_at = EXCLUDED.accessed_at,
                    access_count = EXCLUDED.access_count,
                    emotional_valence = EXCLUDED.emotional_valence,
                    importance = EXCLUDED.importance,
                    metadata = EXCLUDED.metadata,
                    title = EXCLUDED.title,
                    galaxy = EXCLUDED.galaxy,
                    content_hash = EXCLUDED.content_hash
            """, [
                memory.id,
                content_json,
                memory.memory_type.name,
                memory.created_at.isoformat() if hasattr(memory.created_at, 'isoformat') else str(memory.created_at),
                (memory.last_modified or memory.created_at).isoformat() if hasattr(memory.last_modified or memory.created_at, 'isoformat') else str(memory.last_modified or memory.created_at),
                memory.accessed_at.isoformat() if hasattr(memory.accessed_at, 'isoformat') else str(memory.accessed_at),
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
            cur.execute("DELETE FROM tags WHERE memory_id = %s", [memory.id])
            if memory.tags:
                for tag in memory.tags:
                    cur.execute(
                        "INSERT INTO tags (memory_id, tag) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [memory.id, tag],
                    )

            # Update associations
            cur.execute("DELETE FROM associations WHERE source_id = %s", [memory.id])
            if memory.associations:
                for target, strength in memory.associations.items():
                    cur.execute(
                        "INSERT INTO associations (source_id, target_id, strength) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        [memory.id, target, strength],
                    )

        conn.commit()
        return memory.id

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a single memory by ID."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM memories WHERE id = %s", [memory_id])
            row = cur.fetchone()
            if not row:
                return None

            # Get tags
            cur.execute("SELECT tag FROM tags WHERE memory_id = %s", [memory_id])
            tags = {r["tag"] for r in cur.fetchall()}

            return self._row_to_memory(row, tags)

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
        """Search memories using PostgreSQL full-text search."""
        conn = self._get_conn()
        conditions = []
        params: list[Any] = []

        if galaxy:
            conditions.append("galaxy = %s")
            params.append(galaxy)
        if min_importance > 0:
            conditions.append("importance >= %s")
            params.append(min_importance)
        if memory_type:
            mt = memory_type.name if isinstance(memory_type, MemoryType) else str(memory_type)
            conditions.append("memory_type = %s")
            params.append(mt)
        if query:
            conditions.append("to_tsvector('english', coalesce(content,'') || ' ' || coalesce(title,'')) @@ plainto_tsquery('english', %s)")
            params.append(query)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        sql = f"SELECT * FROM memories WHERE {where_clause} ORDER BY importance DESC LIMIT %s"
        params.append(limit)

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

            # Batch fetch tags for all results
            if rows:
                ids = [r["id"] for r in rows]
                cur.execute("SELECT memory_id, tag FROM tags WHERE memory_id = ANY(%s)", [ids])
                tag_map: dict[str, set[str]] = {}
                for tag_row in cur.fetchall():
                    tag_map.setdefault(tag_row["memory_id"], set()).add(tag_row["tag"])
            else:
                tag_map = {}

        results = [self._row_to_memory(row, tag_map.get(row["id"], set())) for row in rows]

        # Post-filter by tags if specified
        if tags:
            results = [m for m in results if tags.issubset(m.tags)]

        return results

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE id = %s", [memory_id])
        conn.commit()
        return True

    def find_by_content_hash(self, content_hash: str) -> str | None:
        """Find a memory by content hash."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM memories WHERE content_hash = %s", [content_hash])
            row = cur.fetchone()
            return row["id"] if row else None

    def store_coords(self, memory_id: str, x: float, y: float, z: float, w: float, v: float) -> None:
        """Store 5D holographic coordinates."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_coords (memory_id, x, y, z, w, v)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (memory_id) DO UPDATE SET x=EXCLUDED.x, y=EXCLUDED.y, z=EXCLUDED.z, w=EXCLUDED.w, v=EXCLUDED.v
            """, [memory_id, x, y, z, w, v])
        conn.commit()

    def get_all_coords(self) -> dict[str, tuple[float, float, float, float, float]]:
        """Get all holographic coordinates."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT memory_id, x, y, z, w, v FROM memory_coords")
            return {
                row["memory_id"]: (row["x"], row["y"], row["z"], row["w"], row["v"])
                for row in cur.fetchall()
            }

    def get_stats(self) -> dict[str, Any]:
        """Return statistics."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM memories")
            total = cur.fetchone()["total"]
            cur.execute("SELECT galaxy, COUNT(*) as cnt FROM memories GROUP BY galaxy ORDER BY cnt DESC")
            by_galaxy = {row["galaxy"]: row["cnt"] for row in cur.fetchall()}
        return {
            "total_memories": total,
            "by_galaxy": by_galaxy,
            "backend": "postgresql",
        }

    def integrity_check(self) -> str:
        """PostgreSQL is always consistent (MVCC)."""
        return "ok"

    def quick_integrity_check(self) -> bool:
        """PostgreSQL is always consistent (MVCC)."""
        return True

    def close(self) -> None:
        """Close the connection."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def _row_to_memory(self, row: Any, tags: set[str] | None = None) -> Memory:
        """Convert a PostgreSQL row to a Memory object."""
        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        content = row.get("content", "")
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Ignored TypeError in postgres_backend.py:374")

        mt_str = row.get("memory_type", "SHORT_TERM")
        try:
            mt = MemoryType[mt_str]
        except (KeyError, ValueError):
            mt = MemoryType.SHORT_TERM

        return Memory(
            id=row["id"],
            content=content,
            memory_type=mt,
            created_at=row.get("created_at"),
            tags=tags or set(),
            emotional_valence=row.get("emotional_valence", 0.0),
            importance=row.get("importance", 0.5),
            metadata=metadata,
            title=row.get("title"),
            galaxy=row.get("galaxy", "universal"),
        )
