"""SQLite Backend for Unified Memory — Compatibility wrapper.

This implementation wraps the simple SQLiteBackend from core.memory.core
and adds stub methods for advanced features that are not yet fully
implemented, allowing the memory system to work end-to-end.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.core.memory.core import MemoryManager, SQLiteBackend as SimpleBackend
from whitemagic.core.memory.unified_types import Memory, MemoryType
from whitemagic.utils.fast_json import dumps_str as _fast_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


class _ConnectionPool:
    """Minimal connection pool compatible with dream cycle expectations."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def connection(self):
        import contextlib

        @contextlib.contextmanager
        def _ctx():
            conn = sqlite3.connect(self._db_path)
            try:
                yield conn
            finally:
                conn.close()

        return _ctx()


class SQLiteBackend:
    """Compatibility SQLite backend that wraps the simple core backend."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._simple = SimpleBackend(str(db_path))
        self._manager = MemoryManager(self._simple)
        self.pool = _ConnectionPool(str(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Ensure extended schema exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            # First create base tables if not exist
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    title TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT,
                    tag TEXT
                );
                CREATE TABLE IF NOT EXISTS associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT,
                    target_id TEXT,
                    association_type TEXT,
                    strength REAL DEFAULT 0.5
                );
                CREATE TABLE IF NOT EXISTS holographic_coords (
                    memory_id TEXT PRIMARY KEY,
                    x REAL, y REAL, z REAL, w REAL, v REAL
                );
                CREATE TABLE IF NOT EXISTS zodiac_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT,
                    actor_id TEXT,
                    entry TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            # Add missing columns to memories table
            cursor = conn.execute("PRAGMA table_info(memories)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            new_cols = [
                ("memory_type", "TEXT DEFAULT 'SHORT_TERM'"),
                ("importance", "REAL DEFAULT 0.5"),
                ("access_count", "INTEGER DEFAULT 0"),
                ("accessed_at", "TIMESTAMP"),
                ("emotional_valence", "REAL DEFAULT 0.0"),
                ("neuro_score", "REAL DEFAULT 0.0"),
                ("novelty_score", "REAL DEFAULT 0.5"),
                ("recall_count", "INTEGER DEFAULT 0"),
                ("half_life_days", "REAL DEFAULT 30.0"),
                ("is_protected", "INTEGER DEFAULT 0"),
                ("galactic_distance", "REAL DEFAULT 0.0"),
                ("retention_score", "REAL DEFAULT 0.5"),
                ("last_retention_sweep", "TIMESTAMP"),
                ("metadata", "TEXT"),
                ("event_time", "TIMESTAMP"),
                ("ingestion_time", "TIMESTAMP"),
                ("is_private", "INTEGER DEFAULT 0"),
                ("model_exclude", "INTEGER DEFAULT 0"),
                ("content_hash", "TEXT"),
            ]
            for col_name, col_type in new_cols:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE memories ADD COLUMN {col_name} {col_type}")
            conn.commit()
        finally:
            conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    # --- Core methods ---

    def store(self, memory: Memory, content_hash: str | None = None) -> str:
        """Store a memory."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Check if exists
            row = conn.execute(
                "SELECT id FROM memories WHERE id = ?", (memory.id,)
            ).fetchone()
            if row:
                # Update
                conn.execute(
                    """UPDATE memories SET content=?, title=?, tags=?, memory_type=?,
                       importance=?, access_count=?, emotional_valence=?, neuro_score=?,
                       novelty_score=?, recall_count=?, half_life_days=?, is_protected=?,
                       galactic_distance=?, retention_score=?, metadata=?, updated_at=?,
                       is_private=?, model_exclude=?, content_hash=?
                       WHERE id=?""",
                    (
                        memory.content, memory.title, ",".join(memory.tags) if memory.tags else "",
                        memory.memory_type.name if hasattr(memory.memory_type, "name") else str(memory.memory_type),
                        memory.importance, memory.access_count, memory.emotional_valence,
                        memory.neuro_score, memory.novelty_score, memory.recall_count,
                        memory.half_life_days, 1 if memory.is_protected else 0,
                        memory.galactic_distance, memory.retention_score,
                        _fast_dumps(memory.metadata) if memory.metadata else None,
                        datetime.now().isoformat(),
                        1 if memory.is_private else 0, 1 if memory.model_exclude else 0,
                        content_hash, memory.id,
                    ),
                )
            else:
                # Insert
                conn.execute(
                    """INSERT INTO memories (
                        id, content, title, tags, memory_type, importance, access_count,
                        accessed_at, created_at, updated_at, emotional_valence, neuro_score,
                        novelty_score, recall_count, half_life_days, is_protected,
                        galactic_distance, retention_score, metadata, event_time,
                        ingestion_time, is_private, model_exclude, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        memory.id, memory.content, memory.title,
                        ",".join(memory.tags) if memory.tags else "",
                        memory.memory_type.name if hasattr(memory.memory_type, "name") else str(memory.memory_type),
                        memory.importance, memory.access_count,
                        memory.accessed_at.isoformat() if memory.accessed_at else None,
                        memory.created_at.isoformat(),
                        (memory.last_modified or memory.created_at).isoformat(),
                        memory.emotional_valence, memory.neuro_score,
                        memory.novelty_score, memory.recall_count,
                        memory.half_life_days, 1 if memory.is_protected else 0,
                        memory.galactic_distance, memory.retention_score,
                        _fast_dumps(memory.metadata) if memory.metadata else None,
                        memory.metadata.get("event_time") if memory.metadata else None,
                        datetime.now().isoformat(),
                        1 if memory.is_private else 0, 1 if memory.model_exclude else 0,
                        content_hash,
                    ),
                )
            conn.commit()
            return memory.id
        finally:
            conn.close()

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a memory by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_memory(row)
        finally:
            conn.close()

    def search(self, query: str | None = None, tags: set[str] | None = None,
               memory_type: MemoryType | None = None, min_importance: float = 0.0,
               limit: int = 20) -> list[Memory]:
        """Search memories."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            sql = "SELECT * FROM memories WHERE 1=1"
            params: list[Any] = []
            if query:
                sql += " AND (content LIKE ? OR title LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type.name if hasattr(memory_type, "name") else str(memory_type))
            sql += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_memory(r) for r in rows]
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            types = {}
            for row in conn.execute("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type"):
                types[row[0]] = row[1]
            return {"total_memories": total, "by_type": types}
        finally:
            conn.close()

    def list_recent(self, limit: int = 10, memory_type: MemoryType | None = None) -> list[Memory]:
        return self.search(memory_type=memory_type, limit=limit)

    def fetch_memory_contents(self, memory_type: str | None = None, limit: int = 10000) -> list[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            sql = "SELECT content FROM memories"
            params: list[Any] = []
            if memory_type:
                sql += " WHERE memory_type = ?"
                params.append(memory_type)
            sql += " LIMIT ?"
            params.append(limit)
            return [r[0] for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def find_by_content_hash(self, content_hash: str) -> str | None:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT id FROM memories WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    # --- Stubs for advanced features ---

    def store_coords(self, memory_id: str, x: float, y: float, z: float, w: float, v: float) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO holographic_coords
                   (memory_id, x, y, z, w, v) VALUES (?, ?, ?, ?, ?, ?)""",
                (memory_id, x, y, z, w, v),
            )
            conn.commit()
        finally:
            conn.close()

    def get_coords(self, memory_id: str) -> tuple[float, float, float, float, float] | None:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT x, y, z, w, v FROM holographic_coords WHERE memory_id = ?", (memory_id,)
            ).fetchone()
            return tuple(row) if row else None
        finally:
            conn.close()

    def get_all_coords(self) -> dict[str, tuple[float, float, float, float, float]]:
        conn = sqlite3.connect(self.db_path)
        try:
            return {
                row[0]: (row[1], row[2], row[3], row[4], row[5])
                for row in conn.execute("SELECT memory_id, x, y, z, w, v FROM holographic_coords")
            }
        finally:
            conn.close()

    def update_galactic_distance(self, memory_id: str, distance: float) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE memories SET galactic_distance = ? WHERE id = ?", (distance, memory_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_weakest_memories(self, limit: int = 100) -> list[Memory]:
        return self.search(limit=limit)

    def archive_to_edge(self, memory_id: str, galactic_distance: float = 0.95) -> None:
        self.update_galactic_distance(memory_id, galactic_distance)

    def list_all_paginated(self, batch_size: int = 500):
        """Yield pages of all memories as Memory objects."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            offset = 0
            while True:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY id LIMIT ? OFFSET ?",
                    (batch_size, offset),
                ).fetchall()
                if not rows:
                    break
                yield [self._row_to_memory(r) for r in rows]
                offset += batch_size
        finally:
            conn.close()

    def batch_update_galactic(self, updates: list[tuple[str, float, float]]) -> None:
        """Batch update galactic_distance and retention_score.

        updates: list of (memory_id, galactic_distance, retention_score)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executemany(
                "UPDATE memories SET galactic_distance = ?, retention_score = ? WHERE id = ?",
                [(d, r, m) for m, d, r in updates],
            )
            conn.commit()
        finally:
            conn.close()

    def consolidate(self) -> int:
        """Run consolidation on this backend — graceful fallback."""
        logger.debug("SQLiteBackend.consolidate: using no-op fallback")
        return 0

    def get_constellation_memberships(self, memory_id: str) -> list[Any]:
        """Return constellation memberships — graceful fallback."""
        logger.debug("SQLiteBackend.get_constellation_memberships: using empty fallback for %s", memory_id)
        return []

    def count_with_rust(self, memory_type: str | None = None) -> int:
        """Count memories — falls back to Python count when Rust is unavailable."""
        logger.debug("SQLiteBackend.count_with_rust: falling back to Python count")
        try:
            return self._simple.count(memory_type)
        except Exception:
            return 0

    # --- Helpers ---

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        tags = set()
        if row["tags"]:
            tags = {t.strip() for t in str(row["tags"]).split(",") if t.strip()}
        metadata = {}
        if row["metadata"]:
            try:
                metadata = _json_loads(row["metadata"])
            except Exception:
                pass
        return Memory(
            id=row["id"],
            content=row["content"] or "",
            title=row["title"] or "",
            tags=tags,
            memory_type=getattr(MemoryType, row["memory_type"], MemoryType.SHORT_TERM) if row["memory_type"] else MemoryType.SHORT_TERM,
            importance=row["importance"] or 0.5,
            access_count=row["access_count"] or 0,
            emotional_valence=row["emotional_valence"] or 0.0,
            neuro_score=row["neuro_score"] or 0.0,
            novelty_score=row["novelty_score"] or 0.5,
            recall_count=row["recall_count"] or 0,
            half_life_days=row["half_life_days"] or 30.0,
            is_protected=bool(row["is_protected"]),
            galactic_distance=row["galactic_distance"] or 0.0,
            retention_score=row["retention_score"] or 0.5,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            last_modified=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            metadata=metadata,
            is_private=bool(row["is_private"]),
            model_exclude=bool(row["model_exclude"]),
        )
