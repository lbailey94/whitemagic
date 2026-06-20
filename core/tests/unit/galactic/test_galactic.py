"""
Tests for the galactic substrate module.

These tests connect to the LIVE substrate DB at ~/.whitemagic/memory/whitemagic.db
when it's available. If the DB doesn't exist (e.g., CI runner without the
state), tests are skipped via pytest.importorskip-style logic.

The substrate is real: 12,238 memories, 21,087 associations, 12,638 embeddings
as of v23.0.0-alpha.1 (per the chronology doc). These tests are integration
tests against that real state, not against mocks.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def substrate_path() -> Path:
    """Resolve the substrate DB path; skip if not present.

    Function-scoped (not module-scoped) because the conftest at this
    directory's level monkeypatches the env at function scope, and the
    resolution depends on the env.
    """
    from whitemagic.core.galactic import _resolve_db_path

    p = _resolve_db_path()
    if not p.exists():
        pytest.skip(f"Substrate DB not found at {p}")
    return p


@pytest.fixture(scope="module")
def db_conn(substrate_path: Path):
    """Read-only connection to the live substrate DB."""
    conn = sqlite3.connect(f"file:{substrate_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def temp_substrate_db():
    """Build an in-memory temp DB with the same schema as the live substrate.

    Used for unit tests that need to verify query shapes without depending
    on the live state. The schema is minimal (memories, associations,
    memory_embeddings, dharma_audit) but enough to exercise the code paths.
    """
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test.db"
        conn = sqlite3.connect(str(p))
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
        yield p
        conn.close()


# ─── Tests: zone classification (pure functions) ──────────────────


def test_galactic_zone_classification():
    from whitemagic.core.galactic import classify_zone, Memory

    # Direct unit test of the zone classification.
    for distance, expected_zone in [
        (0.0, "CORE"),
        (0.149, "CORE"),
        (0.15, "INNER_RIM"),
        (0.39, "INNER_RIM"),
        (0.40, "MID_BAND"),
        (0.64, "MID_BAND"),
        (0.65, "OUTER_RIM"),
        (0.84, "OUTER_RIM"),
        (0.85, "FAR_EDGE"),
        (1.0, "FAR_EDGE"),
    ]:
        # Reconstruct a minimal Row-like object that supports both
        # row["col"] (Memory.from_row) and row.col (sqlite3.Row style).
        class _Row(dict):
            def __getattr__(self, key):
                try:
                    return self[key]
                except KeyError:
                    return None

        row = _Row()
        for col in [
            "id", "content", "title", "tags", "created_at", "updated_at",
            "memory_type", "importance", "access_count", "accessed_at",
            "emotional_valence", "neuro_score", "novelty_score", "recall_count",
            "half_life_days", "is_protected", "galactic_distance", "retention_score",
            "last_retention_sweep", "metadata", "event_time", "ingestion_time",
            "is_private", "model_exclude", "content_hash",
        ]:
            row[col] = None
        row["id"] = "test"
        row["memory_type"] = "SHORT_TERM"
        row["galactic_distance"] = distance
        row["importance"] = 0.5
        row["emotional_valence"] = 0.0
        row["neuro_score"] = 0.0
        row["novelty_score"] = 0.5
        row["created_at"] = "2025-12-01T00:00:00"
        row["updated_at"] = "2025-12-01T00:00:00"
        mem = Memory.from_row(row)
        assert mem.galactic_zone == expected_zone, (
            f"distance={distance} should map to {expected_zone}, got {mem.galactic_zone}"
        )
        # Also exercise the standalone function directly.
        assert classify_zone(distance) == expected_zone


# ─── Tests: Memory dataclass (pure) ──────────────────────────────


def test_memory_to_dict_roundtrip():
    from whitemagic.core.galactic import Memory

    m = Memory(
        id="abc",
        title="hello",
        content="world",
        memory_type="LONG_TERM",
        importance=0.8,
        emotional_valence=0.3,
        neuro_score=0.7,
        novelty_score=0.6,
        galactic_distance=0.2,
        galactic_zone="INNER_RIM",
        created_at="2025-12-01T00:00:00",
        updated_at="2025-12-01T01:00:00",
        tags=["alpha", "beta"],
        metadata={"k": "v"},
    )
    d = m.to_dict()
    assert d["id"] == "abc"
    assert d["title"] == "hello"
    assert d["memory_type"] == "LONG_TERM"
    assert d["galactic_zone"] == "INNER_RIM"
    assert d["tags"] == ["alpha", "beta"]
    assert d["metadata"] == {"k": "v"}


# ─── Tests: live substrate (require ~/.whitemagic/memory/whitemagic.db) ─


def test_substrate_health_returns_alive(substrate_path):
    from whitemagic.core.galactic import substrate_health

    h = substrate_health()
    assert h["status"] == "alive"
    assert h["db_path"] == str(substrate_path)
    assert h["db_size_bytes"] > 0
    assert h["total_memories"] > 0
    assert h["total_associations"] > 0
    # We have at least 12K+ memories per Phase 5 audit.
    assert h["total_memories"] >= 100, f"expected >= 100 memories, got {h['total_memories']}"


def test_galaxy_stats_returns_valid_distribution(substrate_path):
    from whitemagic.core.galactic import galaxy_stats, GALACTIC_ZONES

    stats = galaxy_stats()
    assert stats.total_memories > 0
    assert stats.total_associations >= 0
    # All 5 zones should be in the dict (even if some are 0).
    expected_zones = set(GALACTIC_ZONES.values())
    assert set(stats.by_zone.keys()) == expected_zones
    assert sum(stats.by_zone.values()) == stats.total_memories
    assert 0.0 <= stats.avg_importance <= 1.0
    assert 0.0 <= stats.avg_neuro_score <= 1.0
    assert stats.sweep_duration_ms >= 0
    assert stats.oldest_memory is not None
    assert stats.newest_memory is not None


def test_memory_recent_returns_n(substrate_path):
    from whitemagic.core.galactic import memory_recent

    m = memory_recent(limit=5)
    assert len(m) == 5
    # All should be Memory instances with non-empty ids.
    for mem in m:
        assert mem.id
        assert mem.memory_type in {"SHORT_TERM", "LONG_TERM", "WORKING"}


def test_memory_recent_filters_by_type(substrate_path):
    from whitemagic.core.galactic import memory_recent

    all_mems = memory_recent(limit=20)
    short_term = memory_recent(limit=20, memory_type="SHORT_TERM")
    long_term = memory_recent(limit=20, memory_type="LONG_TERM")
    assert all(m.memory_type == "SHORT_TERM" for m in short_term)
    assert all(m.memory_type == "LONG_TERM" for m in long_term)
    # The two should be disjoint.
    short_ids = {m.id for m in short_term}
    long_ids = {m.id for m in long_term}
    assert short_ids.isdisjoint(long_ids)


def test_memory_by_id_roundtrip(substrate_path):
    from whitemagic.core.galactic import memory_recent, memory_by_id

    recent = memory_recent(limit=1)
    if not recent:
        pytest.skip("no memories to test")
    mem_id = recent[0].id
    fetched = memory_by_id(mem_id)
    assert fetched is not None
    assert fetched.id == mem_id
    assert fetched.title == recent[0].title


def test_memory_by_id_returns_none_for_missing(substrate_path):
    from whitemagic.core.galactic import memory_by_id

    assert memory_by_id("definitely-not-a-real-id") is None


def test_memory_search_returns_matches(substrate_path):
    from whitemagic.core.galactic import memory_search

    # The FTS5 index in the live substrate is unpopulated (0 entries in
    # memories_fts), so the search falls back to LIKE matching. Use a
    # substring that's known to match many Hermes gate decisions.
    results = memory_search("Hermes Gate", limit=10)
    assert len(results) >= 1
    # The matches should have "Hermes Gate" in the title or content.
    for r in results:
        text = (r.title or "") + " " + (r.content or "")
        assert "Hermes Gate" in text or "hermes gate" in text.lower()


def test_memory_search_respects_limit(substrate_path):
    from whitemagic.core.galactic import memory_search

    results = memory_search("a", limit=3)
    assert len(results) <= 3


def test_associations_for_returns_valid(substrate_path):
    from whitemagic.core.galactic import memory_recent, associations_for

    recent = memory_recent(limit=50)
    # Find a memory that has outgoing associations.
    for mem in recent:
        assocs = associations_for(mem.id, direction="outgoing", limit=5)
        if assocs:
            assert all("other_id" in a for a in assocs)
            assert all(0.0 <= a["strength"] <= 1.0 for a in assocs)
            return  # one good test is enough
    pytest.skip("no associations found in the first 50 recent memories")


def test_constellation_count(substrate_path):
    from whitemagic.core.galactic import constellation_count

    n = constellation_count()
    # The substrate has 0+ constellations. We just want it to not error.
    assert n >= 0


# ─── Tests: in-memory schema fixtures (no live DB needed) ─────────


def test_get_db_path_returns_path():
    from whitemagic.core.galactic import get_db_path

    p = get_db_path()
    assert isinstance(p, Path)
    assert "whitemagic.db" in str(p)


def test_connect_raises_on_missing_db(tmp_path, monkeypatch):
    """If the DB path doesn't exist, connect() should raise FileNotFoundError."""
    # Point the resolver at a non-existent file.
    from whitemagic.core import galactic

    fake = tmp_path / "nonexistent.db"
    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: fake)
    with pytest.raises(FileNotFoundError):
        with galactic.connect() as conn:
            conn.execute("SELECT 1")


def test_galaxy_stats_with_temp_db(temp_substrate_db, monkeypatch):
    """Verify the full galaxy_stats pipeline against a synthetic DB."""
    from whitemagic.core import galactic

    # Populate the temp DB with a known distribution.
    p = temp_substrate_db
    conn = sqlite3.connect(str(p))
    conn.executescript(
        """
        INSERT INTO memories (id, title, content, memory_type, importance,
            emotional_valence, neuro_score, galactic_distance, created_at)
        VALUES
            ('m1', 'alpha', 'first',  'SHORT_TERM', 0.7, 0.5, 0.6, 0.05, '2025-11-01'),
            ('m2', 'beta',  'second', 'LONG_TERM',  0.8, 0.3, 0.7, 0.20, '2025-11-02'),
            ('m3', 'gamma', 'third',  'SHORT_TERM', 0.5, 0.0, 0.4, 0.50, '2025-11-03'),
            ('m4', 'delta', 'fourth', 'LONG_TERM',  0.6, 0.0, 0.5, 0.70, '2025-11-04'),
            ('m5', 'eps',   'fifth',  'SHORT_TERM', 0.4, 0.0, 0.3, 0.90, '2025-11-05');
        INSERT INTO associations (source_id, target_id, strength, relation_type)
        VALUES ('m1', 'm2', 0.8, 'associative'),
               ('m1', 'm3', 0.5, 'temporal');
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: p)
    stats = galactic.galaxy_stats()
    assert stats.total_memories == 5
    assert stats.total_associations == 2
    assert stats.by_zone["CORE"] == 1
    assert stats.by_zone["INNER_RIM"] == 1
    assert stats.by_zone["MID_BAND"] == 1
    assert stats.by_zone["OUTER_RIM"] == 1
    assert stats.by_zone["FAR_EDGE"] == 1
    assert stats.by_type["SHORT_TERM"] == 3
    assert stats.by_type["LONG_TERM"] == 2
    assert stats.oldest_memory == "2025-11-01"
    assert stats.newest_memory == "2025-11-05"


def test_memory_recent_with_temp_db(temp_substrate_db, monkeypatch):
    from whitemagic.core import galactic

    p = temp_substrate_db
    conn = sqlite3.connect(str(p))
    conn.executescript(
        """
        INSERT INTO memories (id, title, memory_type, created_at, updated_at)
        VALUES
            ('old', 'oldest', 'SHORT_TERM', '2025-01-01', '2025-01-01'),
            ('new', 'newest', 'SHORT_TERM', '2026-12-31', '2026-12-31');
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: p)
    recent = galactic.memory_recent(limit=10)
    assert len(recent) == 2
    assert recent[0].id == "new"  # Most recent first


def test_memory_search_fts_with_temp_db(temp_substrate_db, monkeypatch):
    from whitemagic.core import galactic

    p = temp_substrate_db
    conn = sqlite3.connect(str(p))
    # FTS5 contentless table — need to manually populate the FTS index.
    conn.executescript(
        """
        INSERT INTO memories (id, title, content, memory_type, created_at)
        VALUES
            ('m1', 'hollow oak', 'a tree in the forest', 'LONG_TERM', '2025-01-01'),
            ('m2', 'river stone', 'a smooth round rock', 'LONG_TERM', '2025-01-01'),
            ('m3', 'old letter', 'a paper from 1900', 'SHORT_TERM', '2025-01-01');
        INSERT INTO memories_fts (rowid, title, content)
        SELECT rowid, title, content FROM memories;
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: p)
    # FTS5 should find the matching title.
    results = galactic.memory_search("hollow", limit=5)
    assert any(r.id == "m1" for r in results)
    # Fallback LIKE search should also work.
    results_like = galactic.memory_search("stone", limit=5)
    assert any(r.id == "m2" for r in results_like)


def test_memory_search_empty_query_returns_empty(temp_substrate_db, monkeypatch):
    from whitemagic.core import galactic

    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: temp_substrate_db)
    assert galactic.memory_search("") == []
    assert galactic.memory_search("", limit=10) == []


def test_associations_for_no_results(temp_substrate_db, monkeypatch):
    from whitemagic.core import galactic

    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: temp_substrate_db)
    assert galactic.associations_for("nonexistent", limit=10) == []
    assert galactic.associations_for("nonexistent", direction="incoming") == []


def test_event_search_with_temp_db(temp_substrate_db, monkeypatch):
    from whitemagic.core import galactic

    p = temp_substrate_db
    conn = sqlite3.connect(str(p))
    conn.executescript(
        """
        INSERT INTO dharma_audit
            (timestamp, action, ethical_score, boundary_type, concerns)
        VALUES
            ('2025-12-01 12:00:00', 'deploy',     0.9, 'release', 'none'),
            ('2025-12-02 12:00:00', 'delete',     0.3, 'destructive', 'data loss'),
            ('2025-12-03 12:00:00', 'test',       0.8, 'normal', 'none');
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: p)
    all_events = galactic.event_search(limit=10)
    assert len(all_events) == 3
    destructive = galactic.event_search(event_type="destructive")
    assert len(destructive) == 1
    assert destructive[0]["action"] == "delete"
    recent = galactic.event_search(since="2025-12-02 00:00:00")
    assert len(recent) == 2
    text = galactic.event_search(query="data loss")
    assert len(text) == 1
    assert text[0]["action"] == "delete"


def test_galactic_zones_constant_has_five_zones():
    from whitemagic.core.galactic import GALACTIC_ZONES

    assert len(GALACTIC_ZONES) == 5
    zones = set(GALACTIC_ZONES.values())
    assert zones == {"CORE", "INNER_RIM", "MID_BAND", "OUTER_RIM", "FAR_EDGE"}


def test_substrate_health_when_missing(tmp_path, monkeypatch):
    from whitemagic.core import galactic

    fake = tmp_path / "nope.db"
    monkeypatch.setattr(galactic, "_resolve_db_path", lambda: fake)
    h = galactic.substrate_health()
    assert h["db_exists"] is False
    assert h["status"] == "missing"
    assert h["total_memories"] == 0
