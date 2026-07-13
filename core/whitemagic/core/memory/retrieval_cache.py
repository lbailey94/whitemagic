"""Phase 6 — Namespace-aware retrieval index cache.

Caches HNSW indexes and holographic spatial indexes per
``(user_id, galaxy)`` namespace. Invalidates on writes to keep
indexes fresh without full rebuilds.

Design:
  - Cache key: ``f"{user_id}/{galaxy}"``
  - Write invalidation: ``invalidate(user_id, galaxy)`` drops the cache entry
  - Automatic TTL expiry (default 300s) for stale entries
  - Thread-safe via RLock
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 300.0  # 5 minutes


class RetrievalIndexCache:
    """Namespace-aware cache for retrieval indexes (HNSW, holographic).

    Each entry stores:
      - ``hnsw_index``: HNSW index object or None
      - ``hnsw_ids``: ID list aligned with HNSW index
      - ``holographic_index``: SpatialIndex5D or None
      - ``created_at``: Monotonic timestamp for TTL
    """

    def __init__(self, ttl_seconds: float = _DEFAULT_TTL) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds

    def _key(self, user_id: str, galaxy: str) -> str:
        return f"{user_id}/{galaxy}"

    def get(self, user_id: str, galaxy: str) -> dict[str, Any] | None:
        """Get a cached index entry, or None if not present or expired."""
        key = self._key(user_id, galaxy)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.monotonic() - entry["created_at"] > self._ttl:
                del self._cache[key]
                return None
            return entry

    def put(self, user_id: str, galaxy: str, entry: dict[str, Any]) -> None:
        """Store an index entry in the cache."""
        key = self._key(user_id, galaxy)
        with self._lock:
            self._cache[key] = {
                "created_at": time.monotonic(),
                **entry,
            }

    def invalidate(self, user_id: str, galaxy: str) -> bool:
        """Invalidate a single namespace entry. Returns True if removed."""
        key = self._key(user_id, galaxy)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug("RetrievalIndexCache invalidated: %s", key)
                return True
            return False

    def invalidate_user(self, user_id: str) -> int:
        """Invalidate all entries for a user. Returns count removed."""
        prefix = f"{user_id}/"
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    def invalidate_all(self) -> int:
        """Invalidate all entries. Returns count removed."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            now = time.monotonic()
            valid = sum(
                1 for e in self._cache.values()
                if now - e["created_at"] <= self._ttl
            )
            return {
                "total_entries": len(self._cache),
                "valid_entries": valid,
                "expired_entries": len(self._cache) - valid,
                "ttl_seconds": self._ttl,
            }

    def prune_expired(self) -> int:
        """Remove expired entries. Returns count pruned."""
        with self._lock:
            now = time.monotonic()
            expired = [
                k for k, e in self._cache.items()
                if now - e["created_at"] > self._ttl
            ]
            for k in expired:
                del self._cache[k]
            return len(expired)


# Singleton
_instance: RetrievalIndexCache | None = None
_instance_lock = threading.Lock()


def get_retrieval_cache() -> RetrievalIndexCache:
    """Get the singleton RetrievalIndexCache instance."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = RetrievalIndexCache()
    return _instance
