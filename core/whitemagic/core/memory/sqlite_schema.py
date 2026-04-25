"""SQLite Schema Manager — Schema management for Unified Memory."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT,
    title TEXT,
    tags TEXT,
    tags_text TEXT,
    memory_type TEXT DEFAULT 'SHORT_TERM',
    importance REAL DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    accessed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT,
    emotional_valence REAL DEFAULT 0.0,
    neuro_score REAL DEFAULT 0.0,
    novelty_score REAL DEFAULT 0.5,
    recall_count INTEGER DEFAULT 0,
    half_life_days REAL DEFAULT 30.0,
    is_protected INTEGER DEFAULT 0,
    galactic_distance REAL DEFAULT 0.0,
    retention_score REAL DEFAULT 0.5,
    last_retention_sweep TIMESTAMP,
    metadata TEXT,
    event_time TIMESTAMP,
    ingestion_time TIMESTAMP,
    is_private INTEGER DEFAULT 0,
    model_exclude INTEGER DEFAULT 0,
    holographic_coords TEXT,
    dharma_audit_trace TEXT,
    embedding BLOB
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT,
    tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS holographic_coords (
    memory_id TEXT PRIMARY KEY,
    x REAL,
    y REAL,
    z REAL,
    w REAL,
    v REAL,
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

CREATE TABLE IF NOT EXISTS zodiac_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT,
    entry TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS associations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT,
    target_id TEXT,
    association_type TEXT,
    strength REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title, content, tags_text, content='memories', content_rowid='rowid'
);
'''


class SQLiteSchemaManager:
    """Schema manager for SQLite memory backend."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize schema on a given connection."""
        conn.executescript(SCHEMA_SQL)

    def ensure_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            self.init_schema(conn)
        finally:
            conn.close()
