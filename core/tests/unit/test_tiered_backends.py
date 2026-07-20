"""Tests for the tiered backend system: per-galaxy SQLite, DuckDB, PostgreSQL."""

import os
from pathlib import Path

import pytest

from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend
from whitemagic.core.memory.unified_types import Memory, MemoryType


@pytest.fixture()
def tmp_galaxy_backend(tmp_path: Path, monkeypatch) -> GalaxyAwareBackend:
    """Create a GalaxyAwareBackend with a temp default DB."""
    default_db = tmp_path / "default" / "whitemagic.db"
    default_db.parent.mkdir(parents=True, exist_ok=True)
    # Set WM_STATE_ROOT so galaxy dirs go to temp
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path / "wm_state"))
    backend = GalaxyAwareBackend(default_db)
    yield backend
    backend.close()


@pytest.fixture()
def sample_memory() -> Memory:
    """Create a sample memory for testing."""
    return Memory(
        id="test-mem-001",
        content="Test memory content about databases",
        memory_type=MemoryType.SHORT_TERM,
        tags={"test", "database"},
        emotional_valence=0.5,
        importance=0.8,
        metadata={"source": "test"},
        title="Test Memory",
        galaxy="sessions",
    )


class TestGalaxyAwareBackend:
    """Tests for per-galaxy SQLite routing."""

    def test_store_routes_to_galaxy_db(self, tmp_galaxy_backend: GalaxyAwareBackend, sample_memory: Memory) -> None:
        """Storing a memory with galaxy='sessions' should go to the sessions galaxy DB."""
        tmp_galaxy_backend.store(sample_memory, content_hash="abc123")

        # The memory should be in the sessions galaxy DB
        results = tmp_galaxy_backend.search(query="databases", galaxy="sessions", limit=10)
        assert len(results) == 1
        assert results[0].id == "test-mem-001"
        assert results[0].galaxy == "sessions"

    def test_store_different_galaxies_isolated(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """Memories in different galaxies should be in separate databases."""
        mem1 = Memory(id="mem-codex-iso-1", content="codex isolation content", memory_type=MemoryType.LONG_TERM, galaxy="codex_iso", importance=0.9)
        mem2 = Memory(id="mem-sessions-iso-1", content="session isolation content", memory_type=MemoryType.CITTA, galaxy="sessions_iso", importance=0.7)

        tmp_galaxy_backend.store(mem1)
        tmp_galaxy_backend.store(mem2)

        # Search codex galaxy only
        codex_results = tmp_galaxy_backend.search(galaxy="codex_iso", limit=10)
        assert len(codex_results) == 1
        assert codex_results[0].id == "mem-codex-iso-1"

        # Search sessions galaxy only
        sessions_results = tmp_galaxy_backend.search(galaxy="sessions_iso", limit=10)
        assert len(sessions_results) == 1
        assert sessions_results[0].id == "mem-sessions-iso-1"

    def test_search_all_galaxies(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """Search without galaxy should search all backends."""
        mem1 = Memory(id="mem-1", content="unique alpha content", memory_type=MemoryType.LONG_TERM, galaxy="codex", importance=0.9)
        mem2 = Memory(id="mem-2", content="unique beta content", memory_type=MemoryType.CITTA, galaxy="sessions", importance=0.8)

        tmp_galaxy_backend.store(mem1)
        tmp_galaxy_backend.store(mem2)

        results = tmp_galaxy_backend.search(limit=10)
        ids = {r.id for r in results}
        assert "mem-1" in ids
        assert "mem-2" in ids

    def test_recall_finds_across_galaxies(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """Recall should search all backends."""
        mem = Memory(id="cross-galaxy-mem", content="find me", memory_type=MemoryType.LONG_TERM, galaxy="research", importance=0.9)
        tmp_galaxy_backend.store(mem)

        result = tmp_galaxy_backend.recall("cross-galaxy-mem")
        assert result is not None
        assert result.id == "cross-galaxy-mem"
        assert result.galaxy == "research"

    def test_find_by_content_hash_across_galaxies(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """find_by_content_hash should search all backends."""
        mem = Memory(id="hash-test-mem", content="hashable content", memory_type=MemoryType.LONG_TERM, galaxy="codex", importance=0.5)
        tmp_galaxy_backend.store(mem, content_hash="hash-123")

        result = tmp_galaxy_backend.find_by_content_hash("hash-123")
        assert result == "hash-test-mem"

    def test_get_stats_aggregates(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """Stats should aggregate across all galaxy backends."""
        mem1 = Memory(id="s1", content="c1", memory_type=MemoryType.LONG_TERM, galaxy="codex", importance=0.5)
        mem2 = Memory(id="s2", content="c2", memory_type=MemoryType.LONG_TERM, galaxy="sessions", importance=0.5)
        mem3 = Memory(id="s3", content="c3", memory_type=MemoryType.LONG_TERM, galaxy="codex", importance=0.5)

        tmp_galaxy_backend.store(mem1)
        tmp_galaxy_backend.store(mem2)
        tmp_galaxy_backend.store(mem3)

        stats = tmp_galaxy_backend.get_stats()
        assert stats["total_memories"] >= 3
        assert stats["backend"] == "galaxy-aware-sqlite"

    def test_integrity_check_healthy(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """Integrity check should return 'ok' for healthy databases."""
        result = tmp_galaxy_backend.integrity_check()
        assert result == "ok"

    def test_list_galaxies(self, tmp_galaxy_backend: GalaxyAwareBackend) -> None:
        """List galaxies should show created galaxy backends."""
        mem = Memory(id="g1", content="c", memory_type=MemoryType.LONG_TERM, galaxy="dreams", importance=0.5)
        tmp_galaxy_backend.store(mem)

        galaxies = tmp_galaxy_backend.list_galaxies()
        assert "dreams" in galaxies


class TestDuckDBBackend:
    """Tests for the DuckDB analytical backend."""

    @pytest.fixture(scope="class")
    def duckdb_backend(self, tmp_path_factory):
        """Shared DuckDB backend to avoid 5s re-init per test."""
        from whitemagic.core.memory.backends.duckdb_backend import DuckDBBackend

        db_path = tmp_path_factory.mktemp("duckdb") / "analytics.duckdb"
        return DuckDBBackend(db_path)

    def test_duckdb_store_and_recall(self, duckdb_backend) -> None:
        """Test basic store and recall in DuckDB."""
        mem = Memory(
            id="duck-test-001",
            content="DuckDB analytical test",
            memory_type=MemoryType.LONG_TERM,
            importance=0.9,
            galaxy="codex",
        )
        duckdb_backend.store(mem)

        result = duckdb_backend.recall("duck-test-001")
        assert result is not None
        assert result.id == "duck-test-001"
        assert result.galaxy == "codex"

    def test_duckdb_search_by_galaxy(self, tmp_path: Path) -> None:
        """Test galaxy-filtered search in DuckDB."""
        from whitemagic.core.memory.backends.duckdb_backend import DuckDBBackend

        db_path = tmp_path / "analytics.duckdb"
        backend = DuckDBBackend(db_path)

        for i in range(5):
            mem = Memory(
                id=f"duck-{i}",
                content=f"content {i}",
                memory_type=MemoryType.LONG_TERM,
                importance=0.5 + i * 0.1,
                galaxy="codex" if i < 3 else "sessions",
            )
            backend.store(mem)

        codex_results = backend.search(galaxy="codex", limit=10)
        assert len(codex_results) == 3

        sessions_results = backend.search(galaxy="sessions", limit=10)
        assert len(sessions_results) == 2

        backend.close()

    def test_duckdb_cross_galaxy_stats(self, tmp_path: Path) -> None:
        """Test cross-galaxy analytical query."""
        from whitemagic.core.memory.backends.duckdb_backend import DuckDBBackend

        db_path = tmp_path / "analytics.duckdb"
        backend = DuckDBBackend(db_path)

        for i in range(10):
            mem = Memory(
                id=f"stat-{i}",
                content=f"statistical content {i}",
                memory_type=MemoryType.LONG_TERM,
                importance=0.3 + i * 0.07,
                emotional_valence=-0.5 + i * 0.1,
                galaxy="codex" if i < 6 else "sessions",
            )
            backend.store(mem)

        stats = backend.cross_galaxy_stats()
        assert "codex" in stats
        assert "sessions" in stats
        assert stats["codex"]["count"] == 6
        assert stats["sessions"]["count"] == 4

        backend.close()

    def test_duckdb_get_stats(self, tmp_path: Path) -> None:
        """Test get_stats in DuckDB."""
        from whitemagic.core.memory.backends.duckdb_backend import DuckDBBackend

        db_path = tmp_path / "analytics.duckdb"
        backend = DuckDBBackend(db_path)

        mem = Memory(id="s1", content="test", memory_type=MemoryType.LONG_TERM, galaxy="codex", importance=0.5)
        backend.store(mem)

        stats = backend.get_stats()
        assert stats["total_memories"] == 1
        assert stats["backend"] == "duckdb"
        assert "codex" in stats["by_galaxy"]

        backend.close()


