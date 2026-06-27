# ruff: noqa: BLE001
"""
Session Seen Registry — "Have I seen this before?" within a session.

Session-scoped version of the seen registry, tracking what has been
viewed during the current session only.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SessionSeenRegistry:
    """Tracks what has been seen in the current session."""

    def __init__(self) -> None:
        self._seen: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _hash(path: str) -> str:
        return hashlib.sha256(path.encode()).hexdigest()[:16]

    def mark_seen(self, path: str, context: str = "") -> bool:
        """Mark a path as seen. Returns True if newly seen."""
        key = self._hash(path)
        if key in self._seen:
            self._seen[key]["times_seen"] += 1
            return False
        self._seen[key] = {
            "path": path,
            "context": context,
            "first_seen": time.time(),
            "times_seen": 1,
        }
        return True

    def has_seen(self, path: str) -> bool:
        return self._hash(path) in self._seen

    def all_seen(self) -> list[str]:
        return [r["path"] for r in self._seen.values()]

    def summary(self) -> dict[str, Any]:
        return {"total_seen": len(self._seen)}


_registry: SessionSeenRegistry | None = None


def get_session_seen_registry() -> SessionSeenRegistry:
    global _registry
    if _registry is None:
        _registry = SessionSeenRegistry()
    return _registry
