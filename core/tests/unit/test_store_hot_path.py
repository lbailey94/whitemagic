"""Regression tests for the store hot path (2026-07-19 timeout fixes).

Two root causes fixed:
1. SQLiteBackend._auto_backup copied the full DB file on EVERY backend
   construction (sessions DB is 1.2GB -> ~25s). Now gated on
   _schema_current(): backups only happen when a migration will run.
2. GalaxyAwareBackend.recall constructed full backends for every on-disk
   galaxy during a miss (paying init/backup costs per galaxy). Now it
   probes read-only first and constructs only on a hit.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from whitemagic.core.memory.backends.galaxy_router import (
    GalaxyAwareBackend,
    _probe_db_for_id,
)
from whitemagic.core.memory.sqlite_backend import SQLiteBackend


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "whitemagic.db"


class TestBackupGating:
    def test_first_init_migrates_and_backs_up_when_noncurrent(self, db_path):
        # Pre-create a DB with data but an INCOMPLETE schema (missing columns)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT)"
        )
        conn.execute("INSERT INTO memories VALUES ('m1', 'hello')")
        conn.commit()
        conn.close()

        SQLiteBackend(db_path)
        # Schema was non-current -> migration ran -> backup must exist
        assert (db_path.with_suffix(".db.bak.1")).exists()

    def test_second_init_skips_backup_when_current(self, db_path):
        # First construction: schema non-current -> migration -> backup
        # (tiny file, but the gate correctly treats it as a migration)
        SQLiteBackend(db_path)
        bak = db_path.with_suffix(".db.bak.1")
        assert bak.exists()
        first_mtime = bak.stat().st_mtime_ns

        # Second construction: schema now current -> backup untouched
        SQLiteBackend(db_path)
        assert bak.stat().st_mtime_ns == first_mtime

    def test_schema_current_true_after_init(self, db_path):
        backend = SQLiteBackend(db_path)
        with backend.pool.connection() as conn:
            assert backend._schema_current(conn) is True

    def test_schema_current_false_when_column_missing(self, db_path, tmp_path):
        # A DB missing managed columns must report non-current
        good = SQLiteBackend(tmp_path / "good.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY)")
        conn.commit()
        try:
            assert good._schema_current(conn) is False
        finally:
            conn.close()


class TestProbeBeforeConstruct:
    def _make_galaxy_db(self, galaxies_dir: Path, name: str, mem_id: str | None) -> Path:
        gdir = galaxies_dir / name
        gdir.mkdir(parents=True)
        db = gdir / "whitemagic.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT)")
        if mem_id:
            conn.execute("INSERT INTO memories VALUES (?, 'x')", (mem_id,))
        conn.commit()
        conn.close()
        return db

    def test_probe_hit_and_miss(self, tmp_path):
        galaxies = tmp_path / "galaxies"
        self._make_galaxy_db(galaxies, "alpha", "target-id")
        self._make_galaxy_db(galaxies, "beta", None)
        assert _probe_db_for_id(galaxies / "alpha" / "whitemagic.db", "target-id")
        assert not _probe_db_for_id(galaxies / "beta" / "whitemagic.db", "target-id")

    def test_probe_missing_file_and_bad_db(self, tmp_path):
        assert not _probe_db_for_id(tmp_path / "nope.db", "x")
        bad = tmp_path / "bad.db"
        bad.write_text("not a sqlite db")
        assert not _probe_db_for_id(bad, "x")

    def test_recall_miss_does_not_construct_backends(self, tmp_path):
        """A recall miss across on-disk galaxies must not construct
        SQLiteBackends (no migration, no backup, no backup files)."""
        galaxies = tmp_path / "galaxies"
        for name in ("g1", "g2", "g3"):
            self._make_galaxy_db(galaxies, name, None)

        default_db = tmp_path / "main.db"
        router = GalaxyAwareBackend(default_db)
        # Point the router at our galaxies dir
        router._galaxies_dir = galaxies

        result = router.recall("nonexistent-id")
        assert result is None
        # Only the default backend should exist; no per-galaxy backends built
        assert len(router._galaxy_backends) == 0
        # And no backup files anywhere
        assert list(galaxies.rglob("*.bak.1")) == []


class TestReinforceHotPath:
    def test_repeated_store_of_same_content_is_fast(self, tmp_path, monkeypatch):
        """Storing near-duplicate content (surprise-gate REINFORCE path)
        must stay well under the 30s dispatch timeout."""
        import time

        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        from whitemagic.core.memory.unified import UnifiedMemory

        um = UnifiedMemory()
        t0 = time.perf_counter()
        m1 = um.store(
            content="Reinforce hot path probe: unique sentinel 8f3a2c.",
            title="hot path probe",
            importance=0.1,
        )
        first = time.perf_counter() - t0

        t0 = time.perf_counter()
        m2 = um.store(
            content="Reinforce hot path probe: unique sentinel 8f3a2c.",
            title="hot path probe",
            importance=0.1,
        )
        second = time.perf_counter() - t0

        # Dedup/reinforce returns the same memory id
        assert m2.id == m1.id
        # Generous bound: must stay far below the 30s dispatch timeout
        assert second < 10.0, f"reinforce path took {second:.1f}s"
