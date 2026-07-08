"""Integration tests for the PostgreSQL backend.

These tests require a real PostgreSQL instance on localhost:5433.
They are skipped gracefully if PostgreSQL is not available.
"""

import os

import pytest

from whitemagic.core.memory.unified_types import Memory, MemoryType


class TestPostgresBackend:
    """Tests for the PostgreSQL backend.

    These tests are skipped if PostgreSQL is not running on localhost:5433.
    """

    @pytest.fixture(autouse=True)
    def _check_pg_available(self) -> None:
        """Skip tests if PostgreSQL is not available."""
        try:
            import psycopg2
            password = os.environ.get("WM_PG_PASSWORD", "")
            conn = psycopg2.connect(
                host="127.0.0.1", port=5433, dbname="whitemagic",
                user="whitemagic", password=password,
                connect_timeout=2,
            )
            conn.close()
        except Exception:
            pytest.skip("PostgreSQL not available on localhost:5433")

    def test_pg_store_and_recall(self) -> None:
        """Test basic store and recall in PostgreSQL."""
        from whitemagic.core.memory.backends.postgres_backend import PostgresBackend

        backend = PostgresBackend()

        mem = Memory(
            id="pg-test-001",
            content="PostgreSQL test memory",
            memory_type=MemoryType.LONG_TERM,
            importance=0.9,
            galaxy="test",
        )
        backend.store(mem)

        result = backend.recall("pg-test-001")
        assert result is not None
        assert result.id == "pg-test-001"
        assert result.galaxy == "test"

        # Cleanup
        backend.delete("pg-test-001")
        backend.close()

    def test_pg_search_by_galaxy(self) -> None:
        """Test galaxy-filtered search in PostgreSQL."""
        from whitemagic.core.memory.backends.postgres_backend import PostgresBackend

        backend = PostgresBackend()

        for i in range(5):
            mem = Memory(
                id=f"pg-search-{i}",
                content=f"searchable content {i}",
                memory_type=MemoryType.LONG_TERM,
                importance=0.5 + i * 0.1,
                galaxy="test_search",
            )
            backend.store(mem)

        results = backend.search(galaxy="test_search", limit=10)
        assert len(results) == 5

        # Cleanup
        for i in range(5):
            backend.delete(f"pg-search-{i}")
        backend.close()

    def test_pg_integrity_always_ok(self) -> None:
        """PostgreSQL should always report healthy (MVCC)."""
        from whitemagic.core.memory.backends.postgres_backend import PostgresBackend

        backend = PostgresBackend()
        assert backend.integrity_check() == "ok"
        assert backend.quick_integrity_check() is True
        backend.close()
