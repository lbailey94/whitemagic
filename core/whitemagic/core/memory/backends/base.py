"""Base backend interface for WhiteMagic memory storage.

All backends (SQLite, DuckDB, PostgreSQL) implement this interface
so that UnifiedMemory can swap between them transparently.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)


class BackendType:
    """Backend type identifiers."""
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    POSTGRESQL = "postgresql"


class BaseBackend(ABC):
    """Abstract base class for memory backends.

    All backends must implement this interface. The store/recall/search
    methods operate on Memory objects, not raw SQL.
    """

    @abstractmethod
    def store(self, memory: Memory, content_hash: str | None = None) -> str:
        """Store or update a memory. Returns the memory ID."""
        ...

    @abstractmethod
    def recall(self, memory_id: str) -> Memory | None:
        """Recall a single memory by ID. Returns None if not found."""
        ...

    @abstractmethod
    def search(
        self,
        query: str = "",
        tags: set[str] | None = None,
        memory_type: MemoryType | str | None = None,
        limit: int = 20,
        galaxy: str | None = None,
        min_importance: float = 0.0,
        **kwargs: Any,
    ) -> list[Memory]:
        """Search memories. Returns a list of Memory objects."""
        ...

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if deleted."""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Return statistics about the backend (total memories, etc.)."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close all connections and release resources."""
        ...

    # Optional methods — backends can override for better performance
    def batch_recall(self, memory_ids: list[str]) -> dict[str, Memory]:
        """Recall multiple memories by ID. Default: loop over recall().

        Backends should override with a single SQL query for efficiency.
        """
        result: dict[str, Memory] = {}
        for mid in memory_ids:
            mem = self.recall(mid)
            if mem is not None:
                result[mid] = mem
        return result

    def find_by_content_hash(self, content_hash: str) -> str | None:
        """Find a memory ID by content hash. Returns None if not found."""
        return None

    def store_coords(self, memory_id: str, x: float, y: float, z: float, w: float, v: float) -> None:
        """Store 5D holographic coordinates for a memory."""
        pass

    def get_all_coords(self) -> dict[str, tuple[float, float, float, float, float]]:
        """Get all holographic coordinates. Returns {memory_id: (x, y, z, w, v)}."""
        return {}

    def integrity_check(self) -> str:
        """Check database integrity. Returns 'ok' or error message."""
        return "ok"

    def quick_integrity_check(self) -> bool:
        """Fast integrity check. Returns True if healthy."""
        return True
