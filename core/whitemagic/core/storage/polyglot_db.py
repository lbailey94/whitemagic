# ruff: noqa: BLE001
"""Polyglot Database Layer - Unified interface to Rust, Elixir, and SQLite backends.

Provides:
- Automatic backend selection based on workload
- Connection pooling for SQLite
- Fallback chain: Rust -> Elixir -> SQLite
- Blackboard integration for all operations
"""

import json
import logging
import sqlite3
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Available database backends."""
    RUST = "rust"
    ELIXIR = "elixir"
    SQLITE = "sqlite"
    AUTO = "auto"


class PolyglotDB:
    """Unified database interface with polyglot backend support."""

    def __init__(self, backend: BackendType = BackendType.AUTO):
        self.backend_type = backend
        self.rust_db = None
        self.elixir_port = None
        self.sqlite_pool = None
        self.blackboard = None

        # Try to initialize backends
        self._init_rust()
        self._init_elixir()
        self._init_sqlite()
        self._init_blackboard()

        # Select active backend
        if backend == BackendType.AUTO:
            self.active_backend = self._select_best_backend()
        else:
            self.active_backend = backend

        logger.info("PolyglotDB initialized with %s backend", self.active_backend.value)

    def _init_rust(self):
        """Initialize Rust backend (DashMap + RocksDB)."""
        try:
            from whitemagic_rs import GalacticDB
            self.rust_db = GalacticDB()
            logger.debug("Rust GalacticDB initialized")
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Rust backend unavailable: %s", e, exc_info=True)

    def _init_elixir(self):
        """Initialize Elixir backend (ETS + GenServer)."""
        try:
            import erlport
            from erlport.erlang import call
            from erlport.erlterms import Atom

            # Start Elixir node
            self.elixir_port = erlport.erlang.Atom(b'whitemagic@localhost')

            # Test connection
            result = call(Atom(b'Elixir.WhiteMagicCore.GalacticStore'), Atom(b'stats'), [])
            logger.debug("Elixir GalacticStore initialized: %s", result, exc_info=True)
        except Exception as e:
            logger.debug("Elixir backend unavailable: %s", e, exc_info=True)

    def _init_sqlite(self):
        """Initialize SQLite backend with connection pooling."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import QueuePool

            from whitemagic.config.paths import MEMORY_DIR

            db_path = MEMORY_DIR / "whitemagic.db"

            # Create engine with connection pool
            self.sqlite_pool = create_engine(
                f"sqlite:///{db_path}",
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False},
            )
            logger.debug("SQLite connection pool initialized")
        except Exception as e:
            logger.warning("SQLite pool initialization failed: %s", e, exc_info=True)
            # Fallback to direct connection
            try:
                import sqlite3

                from whitemagic.config.paths import MEMORY_DIR
                db_path = MEMORY_DIR / "whitemagic.db"
                self.sqlite_pool = sqlite3.connect(str(db_path), check_same_thread=False)
                logger.debug("SQLite direct connection initialized")
            except Exception as e2:
                logger.error("SQLite backend unavailable: %s", e2, exc_info=True)

    def _init_blackboard(self):
        """Initialize blackboard for cross-tool communication."""
        try:
            from whitemagic.agents.blackboard import get_blackboard
            self.blackboard = get_blackboard()
            logger.debug("Blackboard integration enabled")
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Blackboard unavailable: %s", e, exc_info=True)

    def _select_best_backend(self) -> BackendType:
        """Select best available backend."""
        if self.rust_db is not None:
            return BackendType.RUST
        elif self.elixir_port is not None:
            return BackendType.ELIXIR
        elif self.sqlite_pool is not None:
            return BackendType.SQLITE
        else:
            raise RuntimeError("No database backend available")

    def store(self, memory_id: str, content: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Store a memory using active backend."""
        try:
            # Post to blackboard
            if self.blackboard:
                self.blackboard.post("db.write", {
                    "memory_id": memory_id,
                    "backend": self.active_backend.value,
                })

            if self.active_backend == BackendType.RUST and self.rust_db:
                self.rust_db.store(memory_id, content, json.dumps(metadata))
                return {"status": "success", "backend": "rust"}

            elif self.active_backend == BackendType.ELIXIR and self.elixir_port:
                from erlport.erlang import call
                from erlport.erlterms import Atom

                call(
                    Atom(b'Elixir.WhiteMagicCore.GalacticStore'),
                    Atom(b'store_memory'),
                    [memory_id, content, metadata]
                )
                return {"status": "success", "backend": "elixir"}

            elif self.active_backend == BackendType.SQLITE and self.sqlite_pool:
                # Use SQLAlchemy or direct SQLite
                if hasattr(self.sqlite_pool, 'connect'):
                    # SQLAlchemy engine
                    with self.sqlite_pool.connect() as conn:
                        conn.execute(
                            "INSERT OR REPLACE INTO memories (id, content, metadata) VALUES (?, ?, ?)",
                            (memory_id, content, json.dumps(metadata))
                        )
                        conn.commit()
                else:
                    # Direct SQLite connection
                    cursor = self.sqlite_pool.cursor()
                    cursor.execute(
                        "INSERT OR REPLACE INTO memories (id, content, metadata) VALUES (?, ?, ?)",
                        (memory_id, content, json.dumps(metadata))
                    )
                    self.sqlite_pool.commit()

                return {"status": "success", "backend": "sqlite"}

            else:
                return {"status": "error", "error": "No backend available"}

        except (sqlite3.Error, sqlite3.OperationalError) as e:
            logger.error("Store failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}

    def get(self, memory_id: str) -> dict[str, Any]:
        """Retrieve a memory using active backend."""
        try:
            # Post to blackboard
            if self.blackboard:
                self.blackboard.post("db.read", {
                    "memory_id": memory_id,
                    "backend": self.active_backend.value,
                })

            if self.active_backend == BackendType.RUST and self.rust_db:
                result = self.rust_db.get(memory_id)
                if result:
                    return {"status": "success", "memory": json.loads(result), "backend": "rust"}
                return {"status": "error", "error": "Not found"}

            elif self.active_backend == BackendType.ELIXIR and self.elixir_port:
                from erlport.erlang import call
                from erlport.erlterms import Atom

                result = call(
                    Atom(b'Elixir.WhiteMagicCore.GalacticStore'),
                    Atom(b'get_memory'),
                    [memory_id]
                )
                return {"status": "success", "memory": result, "backend": "elixir"}

            elif self.active_backend == BackendType.SQLITE and self.sqlite_pool:
                if hasattr(self.sqlite_pool, 'connect'):
                    with self.sqlite_pool.connect() as conn:
                        result = conn.execute(
                            "SELECT content, metadata FROM memories WHERE id = ?",
                            (memory_id,)
                        ).fetchone()
                else:
                    cursor = self.sqlite_pool.cursor()
                    result = cursor.execute(
                        "SELECT content, metadata FROM memories WHERE id = ?",
                        (memory_id,)
                    ).fetchone()

                if result:
                    return {
                        "status": "success",
                        "memory": {
                            "id": memory_id,
                            "content": result[0],
                            "metadata": json.loads(result[1])
                        },
                        "backend": "sqlite"
                    }
                return {"status": "error", "error": "Not found"}

            else:
                return {"status": "error", "error": "No backend available"}

        except Exception as e:
            logger.error("Get failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}

    def batch_write(self, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """Batch write multiple memories (optimized for parallel workloads)."""
        try:
            # Post to blackboard
            if self.blackboard:
                self.blackboard.post("db.batch_write", {
                    "count": len(memories),
                    "backend": self.active_backend.value,
                })

            if self.active_backend == BackendType.RUST and self.rust_db:
                # Rust backend handles parallel writes efficiently
                batch_data = [
                    (m["id"], m["content"], json.dumps(m.get("metadata", {})))
                    for m in memories
                ]
                count = self.rust_db.batch_write(json.dumps(batch_data))
                return {"status": "success", "count": count, "backend": "rust"}

            elif self.active_backend == BackendType.ELIXIR and self.elixir_port:
                from erlport.erlang import call
                from erlport.erlterms import Atom

                result = call(
                    Atom(b'Elixir.WhiteMagicCore.GalacticStore'),
                    Atom(b'batch_write'),
                    [memories]
                )
                return {"status": "success", "count": result, "backend": "elixir"}

            elif self.active_backend == BackendType.SQLITE and self.sqlite_pool:
                # Use transaction for atomic batch write
                if hasattr(self.sqlite_pool, 'connect'):
                    with self.sqlite_pool.connect() as conn:
                        with conn.begin():
                            conn.executemany(
                                "INSERT OR REPLACE INTO memories (id, content, metadata) VALUES (?, ?, ?)",
                                [(m["id"], m["content"], json.dumps(m.get("metadata", {}))) for m in memories]
                            )
                else:
                    cursor = self.sqlite_pool.cursor()
                    cursor.executemany(
                        "INSERT OR REPLACE INTO memories (id, content, metadata) VALUES (?, ?, ?)",
                        [(m["id"], m["content"], json.dumps(m.get("metadata", {}))) for m in memories]
                    )
                    self.sqlite_pool.commit()

                return {"status": "success", "count": len(memories), "backend": "sqlite"}

            else:
                return {"status": "error", "error": "No backend available"}

        except (sqlite3.Error, sqlite3.OperationalError) as e:
            logger.error("Batch write failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}

    def stats(self) -> dict[str, Any]:
        """Get database statistics."""
        try:
            if self.active_backend == BackendType.RUST and self.rust_db:
                stats_json = self.rust_db.stats()
                return {"status": "success", "stats": json.loads(stats_json), "backend": "rust"}

            elif self.active_backend == BackendType.ELIXIR and self.elixir_port:
                from erlport.erlang import call
                from erlport.erlterms import Atom

                stats = call(
                    Atom(b'Elixir.WhiteMagicCore.GalacticStore'),
                    Atom(b'stats'),
                    []
                )
                return {"status": "success", "stats": stats, "backend": "elixir"}

            elif self.active_backend == BackendType.SQLITE and self.sqlite_pool:
                if hasattr(self.sqlite_pool, 'connect'):
                    with self.sqlite_pool.connect() as conn:
                        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                else:
                    cursor = self.sqlite_pool.cursor()
                    count = cursor.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

                return {
                    "status": "success",
                    "stats": {"memory_count": count},
                    "backend": "sqlite"
                }

            else:
                return {"status": "error", "error": "No backend available"}

        except Exception as e:
            logger.error("Stats failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}


# Global instance
_polyglot_db = None


def get_polyglot_db(backend: BackendType = BackendType.AUTO) -> PolyglotDB:
    """Get global polyglot database instance."""
    global _polyglot_db
    if _polyglot_db is None:
        _polyglot_db = PolyglotDB(backend)
    return _polyglot_db
