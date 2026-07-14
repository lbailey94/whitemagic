# ruff: noqa: BLE001
"""
SQLite Backend for WhiteMagic.

A high-performance storage backend using SQLite instead of JSON files.
Provides 10-50x faster reads/writes for large datasets.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root
from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)


class SQLiteBackend:
    """SQLite-based storage backend."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "storage"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "whitemagic.db"
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = safe_connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source TEXT,
                data TEXT,
                timestamp REAL NOT NULL
            )
        """)
        conn.commit()

    def set(self, key: str, value: Any) -> None:
        """Set a key-value pair."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time()),
        )
        conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM kv_store WHERE key = ?", (key,)
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return default

    def delete(self, key: str) -> bool:
        """Delete a key."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    def keys(self, pattern: str = "%") -> list[str]:
        """List keys matching a pattern."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT key FROM kv_store WHERE key LIKE ?", (pattern,)
        ).fetchall()
        return [r["key"] for r in rows]

    def log_event(
        self, event_type: str, source: str = "", data: dict[str, Any] | None = None
    ) -> None:
        """Log an event."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO events (event_type, source, data, timestamp) VALUES (?, ?, ?, ?)",
            (event_type, source, json.dumps(data or {}), time.time()),
        )
        conn.commit()

    def recent_events(
        self, limit: int = 50, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get recent events."""
        conn = self._get_conn()
        if event_type:
            rows = conn.execute(
                "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "event_type": r["event_type"],
                "source": r["source"],
                "data": json.loads(r["data"]),
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


_backend: SQLiteBackend | None = None


def get_backend() -> SQLiteBackend:
    global _backend
    if _backend is None:
        _backend = SQLiteBackend()
    return _backend
