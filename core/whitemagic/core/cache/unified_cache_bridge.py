"""Unified Cache Bridge — Rust-first cache with Python fallback.

Provides a single cache interface for all WhiteMagic subsystems:
- Semantic cache (dispatch middleware)
- Query cache (memory operations)
- Prefetch cache (speculative prefetcher)
- Embedding cache
- CLI cache

Rust backend: sub-microsecond reads via parking_lot RwLock + HashMap.
Python fallback: OrderedDict LRU with threading.RLock.

Usage:
    from whitemagic.core.cache.unified_cache_bridge import get_unified_cache

    cache = get_unified_cache()

    # Get (returns None on miss)
    value = cache.get("semantic", "my_cache_key")

    # Set with TTL
    cache.set("semantic", "my_cache_key", json.dumps(result), ttl=3600)

    # Stats
    stats = cache.stats()
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RUST_CACHE_AVAILABLE = False
_RUST_CACHE_CLASS = None

try:
    import whitemagic_rs

    if hasattr(whitemagic_rs, "PyUnifiedCache"):
        _RUST_CACHE_CLASS = whitemagic_rs.PyUnifiedCache
        _RUST_CACHE_AVAILABLE = True
        logger.info("Rust UnifiedCache available — sub-microsecond cache reads")
except ImportError:
    pass


class _PyCacheEntry:
    __slots__ = ("value", "expires_at", "access_count", "last_access")

    def __init__(self, value: str, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at
        self.access_count = 0
        self.last_access = time.time()


class PyUnifiedCache:
    """Pure-Python fallback cache — OrderedDict LRU with TTL."""

    def __init__(self, max_size: int = 10000, persist_path: str | None = None) -> None:
        self.max_size = max_size
        self.persist_path = persist_path
        self._cache: OrderedDict[str, _PyCacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0
        self._sets = 0
        if persist_path:
            self._load_from_disk()

    @staticmethod
    def make_key(namespace: str, raw_key: str) -> str:
        h = hashlib.sha256(f"{namespace}|{raw_key}".encode()).hexdigest()[:16]
        return f"{namespace}:{h}"

    def get(self, namespace: str, key: str) -> str | None:
        cache_key = self.make_key(namespace, key)
        now = time.time()
        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None
            entry = self._cache[cache_key]
            if now > entry.expires_at:
                del self._cache[cache_key]
                self._expirations += 1
                self._misses += 1
                return None
            entry.access_count += 1
            entry.last_access = now
            self._cache.move_to_end(cache_key)
            self._hits += 1
            return entry.value

    def set(self, namespace: str, key: str, value: str, ttl_seconds: float) -> None:
        cache_key = self.make_key(namespace, key)
        now = time.time()
        with self._lock:
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
            self._cache[cache_key] = _PyCacheEntry(value, now + ttl_seconds)
            self._sets += 1

    def invalidate(self, namespace: str, key: str) -> bool:
        cache_key = self.make_key(namespace, key)
        with self._lock:
            return self._cache.pop(cache_key, None) is not None

    def invalidate_namespace(self, namespace: str) -> int:
        prefix = f"{namespace}:"
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expirations = 0
            self._sets = 0

    def cleanup_expired(self) -> int:
        now = time.time()
        with self._lock:
            keys = [k for k, v in self._cache.items() if now > v.expires_at]
            for k in keys:
                del self._cache[k]
                self._expirations += 1
            return len(keys)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / max(total, 1)) * 100
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "evictions": self._evictions,
                "expirations": self._expirations,
                "sets": self._sets,
                "total_requests": total,
                "backend": "python",
            }

    def len(self) -> int:
        with self._lock:
            return len(self._cache)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._cache) == 0

    def persist(self) -> int:
        if not self.persist_path:
            return 0
        with self._lock:
            snapshot = [
                (k, {"value": v.value, "expires_at": v.expires_at})
                for k, v in self._cache.items()
            ]
        Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w") as f:
            json.dump(snapshot, f)
        return len(snapshot)

    def _load_from_disk(self) -> int:
        if not self.persist_path or not Path(self.persist_path).exists():
            return 0
        now = time.time()
        try:
            with open(self.persist_path) as f:
                snapshot = json.load(f)
            loaded = 0
            with self._lock:
                for key, data in snapshot:
                    if now <= data["expires_at"]:
                        self._cache[key] = _PyCacheEntry(
                            data["value"], data["expires_at"]
                        )
                        loaded += 1
            return loaded
        except (OSError, json.JSONDecodeError):
            return 0

    def __repr__(self) -> str:
        s = self.stats()
        return (
            f"UnifiedCache(size={s['size']}, hits={s['hits']}, misses={s['misses']}, "
            f"hit_rate={s['hit_rate']}%, backend={s['backend']})"
        )


class UnifiedCacheBridge:
    """Transparent bridge: uses Rust cache if available, Python fallback otherwise.

    All WhiteMagic subsystems should use this bridge for caching.
    Namespaces isolate different cache layers:
        - "semantic" — dispatch semantic cache (mw_semantic_cache)
        - "query" — memory query cache (QueryCache)
        - "prefetch" — speculative prefetch cache (PrefetchCache)
        - "embedding" — embedding vector cache
        - "cli" — CLI command cache
        - "edge" — edge inference cache
    """

    def __init__(self, max_size: int = 10000, persist: bool = True) -> None:
        self._backend = "rust" if _RUST_CACHE_AVAILABLE else "python"
        persist_path = None
        if persist:
            try:
                from whitemagic.config.paths import CACHE_DIR

                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                persist_path = str(CACHE_DIR / "unified_cache.json")
            except (OSError, PermissionError, RuntimeError):
                persist = False

        if _RUST_CACHE_AVAILABLE:
            self._cache = _RUST_CACHE_CLASS(
                max_size=max_size, persist_path=persist_path
            )
        else:
            self._cache = PyUnifiedCache(max_size=max_size, persist_path=persist_path)

        self._state_board_fn = None
        try:
            import whitemagic_rs as _wrs

            if hasattr(_wrs, "board_write_cache_stats"):
                self._state_board_fn = _wrs.board_write_cache_stats
        except ImportError:
            pass

        logger.info("UnifiedCacheBridge initialized (backend=%s)", self._backend)

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_rust(self) -> bool:
        return self._backend == "rust"

    def get(self, namespace: str, key: str) -> str | None:
        return self._cache.get(namespace, key)

    def get_json(self, namespace: str, key: str) -> Any | None:
        """Get and deserialize JSON value."""
        raw = self._cache.get(namespace, key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set(
        self, namespace: str, key: str, value: str, ttl_seconds: float = 3600.0
    ) -> None:
        self._cache.set(namespace, key, value, ttl_seconds)
        self._publish_stats()

    def set_json(
        self, namespace: str, key: str, value: Any, ttl_seconds: float = 3600.0
    ) -> None:
        """Serialize and set a JSON value."""
        try:
            raw = json.dumps(value, default=str)
        except (TypeError, ValueError):
            return
        self._cache.set(namespace, key, raw, ttl_seconds)
        self._publish_stats()

    def invalidate(self, namespace: str, key: str) -> bool:
        return self._cache.invalidate(namespace, key)

    def invalidate_namespace(self, namespace: str) -> int:
        return self._cache.invalidate_namespace(namespace)

    def clear(self) -> None:
        self._cache.clear()

    def cleanup_expired(self) -> int:
        return self._cache.cleanup_expired()

    def stats(self) -> dict[str, Any]:
        if self.is_rust:
            hits, misses, hit_rate, size, evictions, expirations, sets = (
                self._cache.stats()
            )
            return {
                "size": size,
                "max_size": None,
                "hits": hits,
                "misses": misses,
                "hit_rate": round(hit_rate, 2),
                "evictions": evictions,
                "expirations": expirations,
                "sets": sets,
                "total_requests": hits + misses,
                "backend": "rust",
            }
        return self._cache.stats()

    def persist(self) -> int:
        if self.is_rust:
            try:
                return self._cache.persist()
            except (OSError, ValueError, RuntimeError):
                return 0
        return self._cache.persist()

    def _publish_stats(self) -> None:
        """Publish cache stats to the StateBoard shared memory (cross-process)."""
        if self._state_board_fn is None:
            return
        try:
            s = self.stats()
            self._state_board_fn(
                hits=int(s.get("hits", 0)),
                misses=int(s.get("misses", 0)),
                size=int(s.get("size", 0)),
                evictions=int(s.get("evictions", 0)),
                hit_rate=float(s.get("hit_rate", 0.0)),
                sets=int(s.get("sets", 0)),
                backend=1 if self.is_rust else 0,
                expirations=int(s.get("expirations", 0)),
                total_requests=int(s.get("total_requests", 0)),
            )
        except (OSError, ValueError, RuntimeError):
            logger.debug("Swallowed exception", exc_info=True)

    def read_state_board_cache_stats(self) -> dict[str, float] | None:
        """Read cache stats from the StateBoard (cross-process visibility).

        Returns None if StateBoard is not available.
        Other processes (CLI, dashboard) can read these stats without IPC.
        """
        try:
            import whitemagic_rs as _wrs

            if hasattr(_wrs, "board_read_cache_stats"):
                return _wrs.board_read_cache_stats()
        except ImportError:
            pass
        return None

    def tune_ttl(self, namespace: str, current_ttl: float = 86400.0) -> dict[str, Any]:
        """Get TTL tuning recommendation from Julia cache analytics.

        Uses the Julia cache_analytics module to analyze access patterns
        and recommend an optimal TTL. Falls back to Python heuristic
        if Julia is not available.
        """
        s = self.stats()
        try:
            from whitemagic.core.acceleration.julia_bridge import julia_cache_efficiency

            eff = julia_cache_efficiency(
                hits=int(s.get("hits", 0)),
                misses=int(s.get("misses", 0)),
                evictions=int(s.get("evictions", 0)),
                expirations=int(s.get("expirations", 0)),
                size=int(s.get("size", 0)),
                max_size=int(s.get("max_size", 10000) or 10000),
            )
            if eff:
                return {"namespace": namespace, "efficiency": eff, "backend": "julia"}
        except (ImportError, OSError, ValueError, RuntimeError):
            pass

        # Python fallback: simple heuristic
        hit_rate = s.get("hit_rate", 0.0)
        evictions = s.get("evictions", 0)
        if hit_rate < 30.0 and evictions > 100:
            recommendation = "increase_ttl"
        elif hit_rate > 80.0 and evictions < 10:
            recommendation = "decrease_ttl"
        else:
            recommendation = "maintain"
        return {
            "namespace": namespace,
            "efficiency": {
                "score": round(hit_rate / 100.0, 4),
                "hit_rate": round(hit_rate, 2),
                "recommendation": recommendation,
            },
            "backend": "python",
        }

    def __repr__(self) -> str:
        return f"UnifiedCacheBridge(backend={self._backend})"


_unified_cache: UnifiedCacheBridge | None = None
_cache_lock = threading.Lock()


def get_unified_cache() -> UnifiedCacheBridge:
    """Get the global UnifiedCacheBridge instance."""
    global _unified_cache
    if _unified_cache is None:
        with _cache_lock:
            if _unified_cache is None:
                _unified_cache = UnifiedCacheBridge()
    return _unified_cache


def is_rust_cache_available() -> bool:
    """Check if Rust cache backend is available."""
    return _RUST_CACHE_AVAILABLE
