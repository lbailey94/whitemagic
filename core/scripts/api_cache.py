"""Simple TTL cache for REST API hot paths."""

from __future__ import annotations

import time
from typing import Any, Callable


class TTLCache:
    """Time-to-live cache with per-key expiration."""

    def __init__(self, default_ttl: float = 60.0):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key in self._store:
            value, expires_at = self._store[key]
            if time.time() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Cache a value with optional TTL override."""
        expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count removed."""
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._store[k]
        return len(keys_to_remove)

    def clear(self) -> int:
        """Clear all cached entries. Returns count cleared."""
        count = len(self._store)
        self._store.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        active = sum(1 for _, exp in self._store.values() if now < exp)
        expired = len(self._store) - active
        return {
            "total_entries": len(self._store),
            "active": active,
            "expired": expired,
        }


# Global cache instance for REST API
_api_cache = TTLCache(default_ttl=60.0)


def cached(key: str, ttl: float | None = None):
    """Decorator to cache endpoint results."""
    def decorator(fn: Callable):
        def wrapper(*args, **kwargs):
            cache_key = f"{key}:{args}:{sorted(kwargs.items())}"
            result = _api_cache.get(cache_key)
            if result is not None:
                return result
            result = fn(*args, **kwargs)
            _api_cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


def get_api_cache() -> TTLCache:
    """Get the global API cache instance."""
    return _api_cache
