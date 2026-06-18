"""
Rust Backend FFI Bridge
Integrates the Rust memory backend with the existing Python SQLiteBackend
"""
# ruff: noqa: BLE001

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try to import the Rust backend
try:
    from whitemagic_rust_backend import RustBackend
    RUST_AVAILABLE = True
    logger.info("Rust backend available - using accelerated database operations")
except ImportError:
    RUST_AVAILABLE = False
    logger.warning("Rust backend not available - falling back to Python sqlite3")

class RustBackendBridge:
    """Bridge class for integrating Rust backend with Python codebase"""

    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._rust_backend = None

        if RUST_AVAILABLE:
            try:
                self._rust_backend = RustBackend(self.db_path)
                logger.info("Rust backend initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Rust backend: {e}, falling back to Python")
                self._rust_backend = None

    def is_available(self) -> bool:
        """Check if Rust backend is available and initialized"""
        return self._rust_backend is not None

    def store_memory(self, memory: dict[str, Any]) -> str:
        """Store a memory using Rust backend if available"""
        if self._rust_backend:
            return self._rust_backend.store(memory)
        raise RuntimeError("Rust backend not available")

    def recall_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Recall a memory using Rust backend if available"""
        if self._rust_backend:
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
            logger.warning(f"Failed to create Rust backend bridge: {e}")
    return None
