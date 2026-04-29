"""Memory Lifecycle Manager — Stub implementation."""

from __future__ import annotations

from typing import Any


class MemoryLifecycleManager:
    """Stub for memory lifecycle management."""

    def __init__(self, pool: Any) -> None:
        self.pool = pool

    def evaluate(self, memory_id: str) -> str:
        return "active"

    def archive(self, memory_id: str) -> None:
        """Archive a memory — graceful no-op fallback."""
        logger.debug("MemoryLifecycleManager.archive: no-op for %s", memory_id)

    def promote(self, memory_id: str) -> None:
        """Promote a memory — graceful no-op fallback."""
        logger.debug("MemoryLifecycleManager.promote: no-op for %s", memory_id)
