"""MemoryBackend protocol — the canonical interface for all memory backends.

Phase 2 of the Codebase Hardening Strategy.

This Protocol defines the full surface area that a memory backend must
expose: store, recall, search, delete, coordinates, associations,
integrity, and stats. It is a structural protocol (typing.Protocol), so
any class that implements these methods satisfies it without inheritance.

The existing BaseBackend ABC and its concrete implementations
(SQLiteBackend, GalaxyAwareBackend, DuckDBBackend, PostgresBackend)
already satisfy this protocol structurally.

The routing facade (to be implemented in a later slice) will also
satisfy this protocol, allowing UnifiedMemory.backend to point to it
without breaking any consumer that calls .backend.store(), .backend.recall(), etc.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from whitemagic.core.memory.unified_types import Memory, MemoryType


@runtime_checkable
class MemoryBackendProtocol(Protocol):
    """Structural protocol for all memory backend operations.

    Every method that UnifiedMemory exposes to its consumers must be
    declared here so that the routing facade can transparently replace
    the raw SQLiteBackend.

    Methods are grouped:
    - Core CRUD: store, recall, search, delete
    - Content dedup: find_by_content_hash
    - Coordinates: store_coords, get_all_coords, get_coords
    - Associations: add_association, decay_associations, prune_associations
    - Integrity: integrity_check, quick_integrity_check
    - Stats: get_stats
    - Lifecycle: close
    """

    # ── Core CRUD ────────────────────────────────────────────────────

    def store(self, memory: Memory, content_hash: str | None = None) -> str:
        """Store or update a memory. Returns the memory ID."""
        ...

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a single memory by ID. Returns None if not found."""
        ...

    def batch_recall(self, memory_ids: list[str]) -> dict[str, Memory]:
        """Recall multiple memories by ID in a single query.

        Returns a dict mapping found memory_id -> Memory.
        IDs not found are omitted from the result.
        """
        ...

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

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if deleted."""
        ...

    # ── Content dedup ────────────────────────────────────────────────

    def find_by_content_hash(self, content_hash: str) -> str | None:
        """Find a memory ID by content hash. Returns None if not found."""
        ...

    # ── Coordinates ──────────────────────────────────────────────────

    def store_coords(
        self, memory_id: str, x: float, y: float, z: float, w: float, v: float
    ) -> None:
        """Store 5D holographic coordinates for a memory."""
        ...

    def get_all_coords(self) -> dict[str, tuple[float, float, float, float, float]]:
        """Get all holographic coordinates. Returns {memory_id: (x, y, z, w, v)}."""
        ...

    # ── Integrity ────────────────────────────────────────────────────

    def integrity_check(self) -> str:
        """Check database integrity. Returns 'ok' or error message."""
        ...

    def quick_integrity_check(self) -> bool:
        """Fast integrity check. Returns True if healthy."""
        ...

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return statistics about the backend (total memories, etc.)."""
        ...

    # ── Lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Close all connections and release resources."""
        ...


def validate_galaxy_name(galaxy: str) -> str:
    """Validate and sanitize a galaxy name for filesystem use.

    Returns a safe filesystem name. The logical galaxy name should be
    preserved separately by the caller.

    Args:
        galaxy: The raw galaxy name (may contain unsafe characters).

    Returns:
        A sanitized name safe for use as a directory name.

    Raises:
        ValueError: If the galaxy name is empty or contains only
            unsafe characters.
    """
    if not galaxy or not galaxy.strip():
        raise ValueError("Galaxy name cannot be empty")

    # Reject path traversal patterns (but allow / as namespace separator)
    if ".." in galaxy:
        raise ValueError(f"Galaxy name '{galaxy}' contains path traversal characters")

    # Replace unsafe characters with underscore (including / and \)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in galaxy)

    if not safe or safe == "." or safe == "..":
        raise ValueError(f"Galaxy name '{galaxy}' produces invalid filesystem name")

    return safe


def validate_user_id(user_id: str) -> str:
    """Validate and sanitize a user_id for filesystem use.

    Args:
        user_id: The raw user ID.

    Returns:
        A sanitized user ID safe for use as a directory name.

    Raises:
        ValueError: If the user_id is empty or contains path traversal.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id cannot be empty")

    if ".." in user_id:
        raise ValueError(f"user_id '{user_id}' contains path traversal characters")

    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in user_id)

    if not safe or safe == "." or safe == "..":
        raise ValueError(f"user_id '{user_id}' produces invalid filesystem name")

    return safe
