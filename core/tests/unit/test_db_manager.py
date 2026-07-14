"""Tests for db_manager safe_connect, integrity checking, and corruption detection."""

import sqlite3
from pathlib import Path

import pytest

from whitemagic.core.memory.db_manager import (
    ConnectionPool,
    _is_transient_error,
    check_db_integrity,
    safe_connect,
)


@pytest.fixture()
def tmp_db(tmp_path: Path) -> str:
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


class TestSafeConnect:
    """Tests for the safe_connect helper."""

    def test_safe_connect_sets_wal_mode(self, tmp_db: str) -> None:
        conn = safe_connect(tmp_db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()
        assert mode[0].lower() == "wal"
        conn.close()

    def test_safe_connect_sets_busy_timeout(self, tmp_db: str) -> None:
        conn = safe_connect(tmp_db)
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()
        assert timeout[0] == 5000
        conn.close()

    def test_safe_connect_does_not_force_foreign_keys(self, tmp_db: str) -> None:
        conn = safe_connect(tmp_db)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk[0] == 0
        conn.close()

    def test_safe_connect_read_only(self, tmp_db: str) -> None:
        # First create the DB with a table
        conn = safe_connect(tmp_db)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()
        # Now open read-only
        ro = safe_connect(tmp_db, read_only=True)
        row = ro.execute("SELECT id FROM test").fetchone()
        assert row[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            ro.execute("INSERT INTO test VALUES (2)")
        ro.close()

    def test_safe_connect_row_factory(self, tmp_db: str) -> None:
        conn = safe_connect(tmp_db)
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        row = conn.execute("SELECT * FROM test").fetchone()
        assert row["name"] == "hello"
        conn.close()


class TestIntegrityCheck:
    """Tests for integrity checking methods."""

    def test_pool_integrity_check_healthy(self, tmp_db: str) -> None:
        pool = ConnectionPool(tmp_db)
        result = pool.integrity_check()
        assert result == "ok"
        pool.close_all()

    def test_pool_quick_integrity_check_healthy(self, tmp_db: str) -> None:
        pool = ConnectionPool(tmp_db)
        assert pool.quick_integrity_check() is True
        pool.close_all()

    def test_pool_quick_integrity_check_corrupted(self, tmp_db: str) -> None:
        # Create a valid DB with enough data to have multiple pages
        conn = safe_connect(tmp_db)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        for i in range(100):
            conn.execute("INSERT INTO test VALUES (?, ?)", (i, "x" * 200))
        conn.commit()
        conn.close()
        # Corrupt the database by overwriting b-tree page headers with garbage
        # Page 1 is the schema page; corrupting pages 2+ triggers integrity errors
        with open(tmp_db, "r+b") as f:
            f.seek(4096)  # Start of page 2
            f.write(b"\xff\xfe\xfd\xfc" * 256)  # 1024 bytes of garbage
        # The pool should detect corruption
        pool = ConnectionPool(tmp_db)
        assert pool.quick_integrity_check() is False
        pool.close_all()

    def test_check_db_integrity_cached(self, tmp_db: str) -> None:
        # Reset the integrity check cache (may be set by prior tests)
        import whitemagic.core.memory.db_manager as _dbm
        _dbm._last_integrity_check = 0.0
        # First call does the check
        result1 = check_db_integrity(tmp_db)
        assert result1 == "ok"
        # Second call should be cached
        result2 = check_db_integrity(tmp_db)
        assert "cached" in result2


class TestTransientErrorDetection:
    """Tests for the enhanced _is_transient_error."""

    def test_locked_is_transient(self) -> None:
        err = sqlite3.OperationalError("database is locked")
        assert _is_transient_error(err) is True

    def test_busy_is_transient(self) -> None:
        err = sqlite3.OperationalError("database is busy")
        assert _is_transient_error(err) is True

    def test_malformed_is_transient(self) -> None:
        err = sqlite3.DatabaseError("database disk image is malformed")
        assert _is_transient_error(err) is True

    def test_non_transient_error(self) -> None:
        err = sqlite3.OperationalError("no such table: foo")
        assert _is_transient_error(err) is False

    def test_syntax_error_not_transient(self) -> None:
        err = sqlite3.OperationalError("near 'SELECT': syntax error")
        assert _is_transient_error(err) is False
