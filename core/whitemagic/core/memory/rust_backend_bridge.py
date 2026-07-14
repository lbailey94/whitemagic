# ruff: noqa: BLE001
"""
Rust Backend FFI Bridge
Integrates the Rust memory backend with the existing Python SQLiteBackend
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# fall back to legacy whitemagic_rust_backend if available
try:
    import whitemagic_rs
    if hasattr(whitemagic_rs, 'sqlite_backend') and hasattr(whitemagic_rs.sqlite_backend, 'PySQLiteBackend'):
        _RustBackendClass = whitemagic_rs.sqlite_backend.PySQLiteBackend
        RUST_AVAILABLE = True
        logger.info("Rust PyO3 SQLite backend available (whitemagic_rs.sqlite_backend)")
    else:
        raise ImportError("PySQLiteBackend not found in whitemagic_rs")
except ImportError:
    try:
        from whitemagic_rust_backend import RustBackend as _RustBackendClass
        RUST_AVAILABLE = True
        logger.info("Rust backend available (whitemagic_rust_backend)")
    except ImportError:
        _RustBackendClass = None
        RUST_AVAILABLE = False
        logger.warning("Rust backend not available - falling back to Python sqlite3")

class RustBackendBridge:
    """Bridge class for integrating Rust backend with Python codebase"""

    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._rust_backend = None

        if RUST_AVAILABLE and _RustBackendClass is not None:
            try:
                self._rust_backend = _RustBackendClass(self.db_path)
                logger.info("Rust backend initialized successfully")
            except Exception as e:
                logger.warning("Failed to initialize Rust backend: %s, falling back to Python", e, exc_info=True)
                self._rust_backend = None

    def is_available(self) -> bool:
        """Check if Rust backend is available and initialized"""
        return self._rust_backend is not None

    def store_memory(self, memory: dict[str, Any]) -> str:
        """Store a memory using Rust backend if available.

        Accepts a dict with keys matching the Memory dataclass fields.
        Returns the memory ID on success.
        """
        if self._rust_backend:
            # PySQLiteBackend.store_memory takes positional args
            if hasattr(self._rust_backend, 'store_memory'):
                result = self._rust_backend.store_memory(
                    memory.get('id', ''),
                    memory.get('content', ''),
                    memory.get('memory_type', 'short_term'),
                    memory.get('created_at', ''),
                    memory.get('updated_at', ''),
                    memory.get('accessed_at', ''),
                    memory.get('access_count', 0),
                    memory.get('emotional_valence', 0.0),
                    memory.get('importance', 0.5),
                    memory.get('neuro_score', 1.0),
                    memory.get('novelty_score', 1.0),
                    memory.get('recall_count', 0),
                    memory.get('half_life_days', 30.0),
                    memory.get('is_protected', False),
                    json.dumps(memory.get('metadata', {})),
                    memory.get('title', ''),
                    memory.get('galactic_distance', 0.0),
                    memory.get('retention_score', 0.5),
                )
                return memory.get('id', '') if result else ''
            # Legacy RustBackend.store takes a dict
            return self._rust_backend.store(memory)
        raise RuntimeError("Rust backend not available")

    def recall_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Recall a memory using Rust backend if available.

        Returns a dict with memory fields, or None if not found.
        """
        if self._rust_backend:
            if hasattr(self._rust_backend, 'recall'):
                # PySQLiteBackend.recall returns content string
                content = self._rust_backend.recall(memory_id)
                if content:
                    return {'id': memory_id, 'content': content}
                return None
            # Legacy RustBackend.recall returns a dict
            return self._rust_backend.recall(memory_id)
        raise RuntimeError("Rust backend not available")

    def count_all(self) -> int:
        """Get total memory count using Rust backend if available"""
        if self._rust_backend:
            return self._rust_backend.count_all()
        raise RuntimeError("Rust backend not available")

    def count_by_type(self, memory_type: str) -> int:
        """Get memory count by type using Rust backend if available"""
        if self._rust_backend:
            return self._rust_backend.count_by_type(memory_type)
        raise RuntimeError("Rust backend not available")

    def find_by_content_hash(self, content_hash: str) -> str | None:
        """Find memory by content hash using Rust backend if available"""
        if self._rust_backend:
            return self._rust_backend.find_by_content_hash(content_hash)
        raise RuntimeError("Rust backend not available")

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics using Rust backend if available"""
        if self._rust_backend:
            return self._rust_backend.get_stats()
        raise RuntimeError("Rust backend not available")


def get_rust_backend(db_path: Path) -> RustBackendBridge | None:
    """
    Get a Rust backend bridge instance if available.

    Returns None if Rust backend is not available or fails to initialize.
    """
    if RUST_AVAILABLE:
        try:
            return RustBackendBridge(db_path)
        except Exception as e:
            logger.warning("Failed to create Rust backend bridge: %s", e, exc_info=True)
    return None
