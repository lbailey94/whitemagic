"""
Conftest for the galactic tests.

Provides a seeded temp DB with realistic data so tests are self-contained
and don't depend on the live monolith substrate (which is empty
post-galaxy-migration).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from whitemagic.core.memory.db_manager import safe_connect


def _seed_substrate_db(db_path: Path) -> None:
    """Create and seed a substrate DB with enough data for all galactic tests.

    Includes:
    - 120 memories across all 5 galactic zones, mixed SHORT_TERM/LONG_TERM
    - 20 associations
    - 15 dharma_audit events (cli_command + voice_expressed types)
    - FTS5 index populated for search tests
    - Searchable content including "Hermes Gate" for search tests
    """
    conn = safe_connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            content TEXT,
            title TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            memory_type TEXT DEFAULT 'SHORT_TERM',
            importance REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            accessed_at TIMESTAMP,
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
            content_hash TEXT
        );
        CREATE TABLE associations (
            source_id TEXT,
            target_id TEXT,
            strength REAL,
            last_traversed_at TIMESTAMP,
            traversal_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            direction TEXT,
            relation_type TEXT,
            edge_type TEXT,
            valid_from TIMESTAMP,
            valid_until TIMESTAMP,
            ingestion_time TIMESTAMP
        );
        CREATE TABLE memory_embeddings (
            memory_id TEXT,
            embedding BLOB,
            model TEXT,
            dim INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE dharma_audit (
            id INTEGER PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT,
            ethical_score REAL,
            harmony_score REAL,
            consent_level TEXT,
            boundary_type TEXT,
            concerns TEXT,
            context TEXT,
            decision TEXT
        );
        CREATE VIRTUAL TABLE memories_fts USING fts5(
            title, content, content='memories', content_rowid='rowid'
        );
        """
    )

    # Insert 120 memories: 60 SHORT_TERM + 60 LONG_TERM
    # Spread across all 5 galactic zones (24 per zone)
    zones = [
        (0.00, 0.15),   # CORE
        (0.15, 0.40),   # INNER_RIM
        (0.40, 0.65),   # MID_BAND
        (0.65, 0.85),   # OUTER_RIM
        (0.85, 1.01),   # FAR_EDGE
    ]
    mem_rows = []
    for i in range(120):
        zone_idx = i // 24
        lo, hi = zones[zone_idx]
        dist = lo + (hi - lo) * ((i % 24) / 24.0)
        mem_type = "SHORT_TERM" if i % 2 == 0 else "LONG_TERM"
        title = f"Memory_{i:03d}"
        if i == 0:
            title = "Hermes Gate Initialization"
        elif i == 1:
            title = "Hermes Gate Protocol"
        content = f"Content for memory {i:03d} with some searchable text"
        if i < 2:
            content = f"Hermes Gate configuration and protocol details {i}"
        tags = "alpha,beta" if i % 3 == 0 else "gamma"
        created = f"2025-11-{(i % 30) + 1:02d}T00:00:00"
        updated = f"2025-12-{(i % 30) + 1:02d}T00:00:00"
        importance = 0.3 + (i % 10) * 0.07
        mem_rows.append(
            (f"mem_{i:03d}", content, title, tags, created, updated,
             mem_type, importance, 0.0, float(i % 5) * 0.1, float(i % 7) * 0.1,
             dist)
        )

    conn.executemany(
        "INSERT INTO memories (id, content, title, tags, created_at, updated_at, "
        "memory_type, importance, emotional_valence, neuro_score, novelty_score, "
        "galactic_distance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        mem_rows,
    )

    # Insert 20 associations
    assoc_rows = []
    for i in range(20):
        src = f"mem_{i:03d}"
        tgt = f"mem_{(i + 1) % 120:03d}"
        strength = 0.3 + (i % 10) * 0.07
        rel = "associative" if i % 2 == 0 else "temporal"
        assoc_rows.append((src, tgt, strength, rel))
    conn.executemany(
        "INSERT INTO associations (source_id, target_id, strength, relation_type) "
        "VALUES (?, ?, ?, ?)",
        assoc_rows,
    )

    # Insert 15 dharma_audit events
    event_rows = []
    for i in range(10):
        event_rows.append((
            f"echo test command {i}",
            "cli_command",
            0.8 + i * 0.02,
            f"CLI audit entry {i}",
            f"echo test {i}",
        ))
    for i in range(5):
        event_rows.append((
            f"voice expressed thought {i}",
            "voice_expressed",
            0.7 + i * 0.05,
            f"Narrator event {i}",
            f"voice expression {i}",
        ))
    conn.executemany(
        "INSERT INTO dharma_audit (action, boundary_type, ethical_score, concerns, context) "
        "VALUES (?, ?, ?, ?, ?)",
        event_rows,
    )

    # Populate FTS5 index
    conn.execute(
        "INSERT INTO memories_fts (rowid, title, content) "
        "SELECT rowid, title, content FROM memories"
    )

    conn.commit()
    conn.close()


@pytest.fixture(scope="session")
def _seeded_db(tmp_path_factory):
    """Create a seeded substrate DB once per session."""
    tmp_dir = tmp_path_factory.mktemp("galactic_seeded")
    db_path = tmp_dir / "whitemagic.db"
    _seed_substrate_db(db_path)
    return db_path


@pytest.fixture(autouse=True)
def use_live_substrate(monkeypatch, _seeded_db):
    """Point galactic tests at a seeded temp DB.

    The monolith DB at ~/.whitemagic/memory/whitemagic.db is empty
    post-galaxy-migration. We use a self-contained seeded DB instead
    so tests don't depend on live state.
    """
    monkeypatch.setenv("WM_MEMORY_DB", str(_seeded_db))
    monkeypatch.delenv("WM_STATE_ROOT", raising=False)
    yield


@pytest.fixture
def seeded_substrate_db(_seeded_db):
    """Provide the seeded DB path for tests that need it directly."""
    return _seeded_db

