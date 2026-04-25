"""Database Manager — Thread-safe SQLite connection pool.

Provides connection pooling, WAL mode, memory-mapped I/O, retry logic,
and optional SQLCipher encryption at rest.
"""
from __future__ import annotations

import asyncio
import logging
import os
import queue
import sqlite3
import threading
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, cast

logger = logging.getLogger(__name__)

# Transient error codes that warrant retry
_TRANSIENT_ERRORS = {
    sqlite3.SQLITE_BUSY: "database is locked",
    sqlite3.SQLITE_LOCKED: "table is locked",
    sqlite3.SQLITE_PROTOCOL: "locking protocol error",
}


def _is_transient_error(error: Exception) -> bool:
    """Check if error is transient and worth retrying."""
    if isinstance(error, sqlite3.OperationalError):
        for code in _TRANSIENT_ERRORS:
            if str(code) in str(error) or f"({code})" in str(error):
                return True
        err_str = str(error).lower()
        return any(msg in err_str for msg in ["locked", "busy", "protocol"])
    return False


def retry_with_backoff(
    func: Any,
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
) -> Any:
    """Decorator for retrying operations with exponential backoff."""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_error = None
        delay = base_delay
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not _is_transient_error(e) or attempt == max_retries:
                    raise
                last_error = e
                logger.debug("Transient DB error, retrying in %.2fs: %s", delay, e)
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
        if last_error:
            raise last_error
        raise RuntimeError("DB operation failed after retries")
    return wrapper


try:
    import sqlcipher3  # type: ignore[import-untyped]  # noqa: F401
    _SQLCIPHER_AVAILABLE = True
except ImportError:
    _SQLCIPHER_AVAILABLE = False


class ConnectionPool:
    """Thread-safe SQLite connection pool."""

    def __init__(self, db_path: str, max_connections: int = 10) -> None:
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: queue.Queue[sqlite3.Connection] = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._connections_created = 0

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with best-practice settings."""
        passphrase = os.environ.get("WM_DB_PASSPHRASE", "")
        if passphrase and _SQLCIPHER_AVAILABLE:
            import sqlcipher3  # type: ignore[import-untyped]
            conn = cast("sqlite3.Connection", sqlcipher3.connect(self.db_path, check_same_thread=False))
            safe_passphrase = passphrase.replace("'", "''")
            conn.execute("PRAGMA key='" + safe_passphrase + "'")
            logger.debug("SQLCipher encryption active for %s", self.db_path)
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # --- P6: Aggressive PRAGMA tuning (v13.3.3) ---
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA mmap_size=268435456")   # 256MB mmap window
        conn.execute("PRAGMA cache_size=-65536")      # 64MB page cache
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool or create a new one."""
        try:
            return self._pool.get(block=False)
        except queue.Empty:
            with self._lock:
                if self._connections_created < self.max_connections:
                    conn = self._create_connection()
                    self._connections_created += 1
                    return conn
                else:
                    return self._pool.get(block=True, timeout=5)

    def release_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        try:
            self._pool.put(conn, block=False)
        except queue.Full:
            conn.close()
            with self._lock:
                self._connections_created -= 1

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for easy connection handling."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.release_connection(conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            conn = self._pool.get()
            conn.close()
        self._connections_created = 0

    # -----------------------------------------------------------------------
    # Async versions for PSR-013
    # -----------------------------------------------------------------------

    async def get_connection_async(self) -> sqlite3.Connection:
        """Get a connection from the pool asynchronously."""
        try:
            return self._pool.get(block=False)
        except queue.Empty:
            with self._lock:
                if self._connections_created < self.max_connections:
                    conn = self._create_connection()
                    self._connections_created += 1
                    return conn
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None, lambda: self._pool.get(block=True, timeout=5)
                    )

    async def release_connection_async(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool asynchronously."""
        try:
            self._pool.put(conn, block=False)
        except queue.Full:
            conn.close()
            with self._lock:
                self._connections_created -= 1

    @asynccontextmanager
    async def connection_async(self) -> AsyncGenerator[sqlite3.Connection, None]:
        """Async context manager for easy connection handling."""
        conn = await self.get_connection_async()
        try:
            yield conn
        finally:
            await self.release_connection_async(conn)


# Registry of pools by db_path
_pools: dict[str, ConnectionPool] = {}
_registry_lock = threading.Lock()


# Backward compat: SimpleDBPool alias
SimpleDBPool = ConnectionPool


def get_db_pool(db_path: str, max_connections: int = 10) -> ConnectionPool:
    """Get or create a connection pool for a specific database."""
    with _registry_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(db_path, max_connections)
        return _pools[db_path]


async def get_db_pool_async(db_path: str, max_connections: int = 10) -> ConnectionPool:
    """Get or create a connection pool for a specific database asynchronously."""
    # Note: asyncio.Lock() requires an event loop; use threading lock as fallback
    with _registry_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(db_path, max_connections)
        return _pools[db_path]


# Global connection pool for the default database
_default_pool: ConnectionPool | None = None
_default_pool_lock = threading.Lock()


async def get_default_pool_async() -> ConnectionPool | None:
    """Get the default connection pool asynchronously."""
    global _default_pool
    if _default_pool is None:
        from whitemagic.config.paths import DB_PATH
        if DB_PATH.exists():
            _default_pool = await get_db_pool_async(str(DB_PATH))
    return _default_pool
