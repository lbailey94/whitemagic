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
        return any(msg in err_str for msg in ["locked", "busy", "protocol", "disk i/o"])
    if isinstance(error, sqlite3.DatabaseError):
        err_str = str(error).lower()
        if "malformed" in err_str or "disk image" in err_str or "disk i/o" in err_str:
            return True
    return False


def retry_with_backoff(
    func: Any,
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
) -> Any:
    """Decorator for retrying operations with exponential backoff.

    Usage:
        @retry_with_backoff
        def my_db_operation():
            ...
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """
        Perform the wrapper operation.

        Returns:
            Any
        """
        last_error = None
        delay = base_delay
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not _is_transient_error(e) or attempt == max_retries:
                    raise
                last_error = e
                logger.debug("Transient DB error, retrying in %.2fs: %s", delay, e, exc_info=True)
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

# ── Safe connection helper for raw callers ───────────────────────────────
# Many modules across the codebase open raw sqlite3.connect() without setting
# WAL mode or other pragmas. When a WAL-mode database is opened with default
# rollback-journal mode, concurrent access can corrupt the database.
# This helper ensures every connection uses consistent settings.

_WAL_PRAGMAS = (
    ("PRAGMA journal_mode=WAL",),
    ("PRAGMA synchronous=NORMAL",),
    ("PRAGMA busy_timeout=5000",),
    ("PRAGMA temp_store=MEMORY",),
    # mmap the database file — OS page-cache handles RAM, SQLite avoids
    # double-buffering.  256MB covers all 22 galaxy DBs (largest ~23MB).
    ("PRAGMA mmap_size=268435456",),
    # Page cache: 65536 pages × 4KB = 256MB for hot data
    ("PRAGMA cache_size=-65536",),
)

# Security pragmas — defend against schema-level attacks (CVE-2025-7709 class)
# trusted_schema=OFF prevents triggers/views/CHECK constraints from invoking
# functions with side effects when loaded from a potentially corrupted DB file.
# See: https://sqlite.org/security.html §9a
_SECURITY_PRAGMAS = (
    ("PRAGMA trusted_schema=OFF",),
)


def safe_connect(
    db_path: str,
    *,
    read_only: bool = False,
    timeout: float = 30.0,
    uri: bool = False,
    retries: int = 3,
    **kwargs: Any,
) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and standard pragmas.

    ALL modules that need a direct sqlite3.connect() should use this instead
    to ensure consistent journal mode and prevent database corruption.

    Includes retry logic for transient disk I/O errors.

    Args:
        db_path: Path to the SQLite database file.
        read_only: If True, open in read-only mode (no WAL switch attempted).
        timeout: Busy timeout in seconds.
        uri: If True, treat db_path as a URI (enables query params like ?mode=ro).
        retries: Number of retry attempts for transient errors.
        **kwargs: Additional kwargs passed to sqlite3.connect().
    """
    delay = 0.1
    for attempt in range(retries + 1):
        try:
            if read_only:
                uri_path = f"file:{db_path}?mode=ro"
                kwargs.setdefault("check_same_thread", False)
                conn = sqlite3.connect(uri_path, uri=True, timeout=timeout, **kwargs)
            else:
                kwargs.setdefault("check_same_thread", False)
                conn = sqlite3.connect(db_path, timeout=timeout, uri=uri, **kwargs)
            conn.row_factory = sqlite3.Row
            if not read_only:
                for pragma, in _WAL_PRAGMAS:
                    try:
                        conn.execute(pragma)
                    except sqlite3.OperationalError:
                        pass
                for pragma, in _SECURITY_PRAGMAS:
                    try:
                        conn.execute(pragma)
                    except (sqlite3.OperationalError, sqlite3.NotSupportedError):
                        pass
            else:
                try:
                    conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
                except sqlite3.OperationalError:
                    pass
                for pragma, in _SECURITY_PRAGMAS:
                    try:
                        conn.execute(pragma)
                    except (sqlite3.OperationalError, sqlite3.NotSupportedError):
                        pass
            return conn
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            if _is_transient_error(e) and attempt < retries:
                logger.debug("safe_connect retry %d/%d: %s", attempt + 1, retries, e)
                time.sleep(delay)
                delay = min(delay * 2, 2.0)
                continue
            raise


@contextmanager
def pooled_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Get a pooled connection to the database.

    Prefer this over safe_connect() when the module doesn't need a persistent
    connection. Uses the shared connection pool to limit total open connections.

    Args:
        db_path: Path to the database. Defaults to the main WM database.
    """
    if db_path is None:
        from whitemagic.config.paths import DB_PATH
        db_path = str(DB_PATH)
    pool = get_db_pool(db_path)
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.release_connection(conn)

class ConnectionPool:
    """Thread-safe SQLite connection pool."""

    def __init__(self, db_path: str, max_connections: int = 10) -> None:
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: queue.Queue[sqlite3.Connection] = queue.Queue(maxsize=max_connections)
        self._lock = threading.RLock()
        self._connections_created = 0

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with best-practice settings.

        If WM_DB_PASSPHRASE is set and sqlcipher3 is available, uses
        SQLCipher for encryption at rest (AES-256-CBC).
        """
        passphrase = os.environ.get("WM_DB_PASSPHRASE", "")
        if passphrase and _SQLCIPHER_AVAILABLE:
            import sqlcipher3  # type: ignore[import-untyped]
            conn = cast("sqlite3.Connection", sqlcipher3.connect(self.db_path, check_same_thread=False))
            # SQLCipher PRAGMA key doesn't support ? binding; escape quotes to prevent injection
            safe_passphrase = passphrase.replace("'", "''")
            conn.execute("PRAGMA key='" + safe_passphrase + "'")
            logger.debug("SQLCipher encryption active for %s", self.db_path)
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        # P6a: Memory-mapped I/O — 256MB mmap window for read-heavy workloads
        # Bypasses read() syscalls entirely; OS page cache serves data directly
        conn.execute("PRAGMA mmap_size=268435456")
        # P6b: 64MB page cache (negative = KB, so -65536 = 64MB)
        # Default is ~2MB; larger cache avoids re-reading hot pages
        conn.execute("PRAGMA cache_size=-65536")
        # P6c: Temp tables and indices in RAM (no temp file I/O)
        conn.execute("PRAGMA temp_store=MEMORY")
        # P6d: Busy timeout for write contention under WAL
        conn.execute("PRAGMA busy_timeout=5000")
        # P6f: WAL auto-checkpoint at 1000 pages (~4MB) for predictable checkpoint timing
        # Default is 1000, but explicit setting avoids environment-dependent defaults
        conn.execute("PRAGMA wal_autocheckpoint=1000")
        # P6e: Foreign keys for referential integrity
        conn.execute("PRAGMA foreign_keys=ON")
        # Row factory for dictionary-like access
        conn.row_factory = sqlite3.Row
        return conn

    def integrity_check(self) -> str:
        """Run PRAGMA integrity_check on the database.

        Returns 'ok' if healthy, or the first error message if corrupted.
        Should be called periodically to detect corruption early.
        """
        try:
            with self.connection() as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                return result[0] if result else "unknown"
        except sqlite3.DatabaseError as e:
            return str(e)

    def quick_integrity_check(self) -> bool:
        """Fast integrity check — returns True if healthy, False if corrupted."""
        try:
            with self.connection() as conn:
                result = conn.execute("PRAGMA quick_check").fetchone()
                return result is not None and result[0] == "ok"
        except sqlite3.DatabaseError:
            return False

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
                    # Wait for a connection to be available
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
                    # Wait for a connection to be available (async-friendly)
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
_registry_lock = threading.RLock()

# Async registry lock for PSR-013
_async_registry_lock = asyncio.Lock()


def get_db_pool(db_path: str, max_connections: int = 5) -> ConnectionPool:
    """Get or create a connection pool for a specific database."""
    with _registry_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(db_path, max_connections)
        return _pools[db_path]


async def get_db_pool_async(db_path: str, max_connections: int = 10) -> ConnectionPool:
    """Get or create a connection pool for a specific database asynchronously."""
    async with _async_registry_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(db_path, max_connections)
        return _pools[db_path]


# Global connection pool for the default database
_default_pool: ConnectionPool | None = None
_default_pool_lock = threading.RLock()


async def get_default_pool_async() -> ConnectionPool | None:
    """Get the default connection pool asynchronously."""
    global _default_pool
    if _default_pool is None:
        from whitemagic.config.paths import DB_PATH
        if DB_PATH.exists():
            _default_pool = await get_db_pool_async(str(DB_PATH))
    return _default_pool


# ── Integrity monitoring ─────────────────────────────────────────────────
_last_integrity_check: float = 0.0
_integrity_check_interval: float = 300.0  # 5 minutes
_integrity_lock = threading.RLock()


def check_db_integrity(db_path: str | None = None) -> str:
    """Run an integrity check on the database. Caches results for 5 minutes.

    Args:
        db_path: Path to the database. Defaults to the main WM database.

    Returns:
        'ok' if healthy, or the first error message if corrupted.
    """
    global _last_integrity_check
    if db_path is None:
        from whitemagic.config.paths import DB_PATH
        db_path = str(DB_PATH)
    now = time.time()
    with _integrity_lock:
        if now - _last_integrity_check < _integrity_check_interval:
            return "ok (cached)"
        _last_integrity_check = now
    pool = get_db_pool(db_path)
    result = pool.integrity_check()
    if result != "ok":
        logger.error("Database integrity check FAILED for %s: %s", db_path, result)
        logger.info("Attempting automatic database repair for %s", db_path)
        repair_result = repair_db(db_path)
        if repair_result.get("status") == "success":
            logger.info("Database auto-repair succeeded for %s", db_path)
            return "ok"
        else:
            logger.error("Database auto-repair failed: %s", repair_result)
    return result


def repair_db(db_path: str | None = None) -> dict[str, Any]:
    """Repair a corrupted SQLite database by rebuilding from dump.

    Uses .dump → recreate → .restore to produce a clean, compacted file.
    Creates a backup before repair. Clears WAL and SHM files.

    Returns:
        Dict with 'status', 'backup_path', 'details'.
    """
    import shutil
    import subprocess

    if db_path is None:
        from whitemagic.config.paths import DB_PATH
        db_path = str(DB_PATH)

    backup_path = db_path + ".bak"
    wal_path = db_path + "-wal"
    shm_path = db_path + "-shm"

    # Step 1: Backup
    shutil.copy2(db_path, backup_path)

    # Step 2: Clear WAL/SHM (they may contain corrupt data)
    for sidecar in (wal_path, shm_path):
        if os.path.exists(sidecar):
            os.remove(sidecar)

    # Step 3: Dump to SQL script
    dump_path = db_path + ".dump.sql"
    result = subprocess.run(
        ["sqlite3", db_path, ".dump"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        return {
            "status": "error",
            "error": f"sqlite3 .dump failed: {result.stderr[:500]}",
            "backup_path": backup_path,
        }

    with open(dump_path, "w") as f:
        f.write(result.stdout)

    # Step 4: Create new database from dump
    new_path = db_path + ".new"
    if os.path.exists(new_path):
        os.remove(new_path)
    result = subprocess.run(
        ["sqlite3", new_path],
        input=result.stdout, capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        return {
            "status": "error",
            "error": f"sqlite3 restore failed: {result.stderr[:500]}",
            "backup_path": backup_path,
        }

    # Step 5: Replace old database
    os.replace(new_path, db_path)
    os.remove(dump_path)

    # Step 6: Verify
    conn = safe_connect(db_path, read_only=True)
    check = conn.execute("PRAGMA integrity_check").fetchone()
    conn.close()

    # Reset integrity cache
    global _last_integrity_check
    with _integrity_lock:
        _last_integrity_check = 0.0

    if check and check[0] == "ok":
        logger.info("Database repaired successfully: %s", db_path)
        return {
            "status": "success",
            "backup_path": backup_path,
            "integrity_check": "ok",
        }
    else:
        return {
            "status": "warning",
            "backup_path": backup_path,
            "integrity_check": check[0] if check else "unknown",
            "message": "Repair completed but integrity check still reports issues",
        }
