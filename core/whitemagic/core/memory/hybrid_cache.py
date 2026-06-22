"""Intelligent caching layer for hybrid_recall() - H002 optimization.

Implements multi-level caching with LRU eviction:
- Query result cache (full results)
- Embedding cache (encoded queries)
- Strategy cache (search strategy decisions)

Target: 80%+ cache hit rate, 20× speedup on cached queries.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """Get value from cache, return None if miss or expired."""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            value, timestamp = self.cache[key]

            # Check TTL
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[key]
                self.misses += 1
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return value

    def put(self, key: str, value: Any) -> None:
        """Put value in cache, evict LRU if needed."""
        with self.lock:
            # Update existing
            if key in self.cache:
                self.cache[key] = (value, time.time())
                self.cache.move_to_end(key)
                return

            # Add new
            self.cache[key] = (value, time.time())

            # Evict LRU if over capacity
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0.0
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "ttl_seconds": self.ttl_seconds,
            }


class HybridRecallCache:
    """Multi-level cache for hybrid_recall() optimization."""

    def __init__(
        self,
        query_cache_size: int = 500,
        embedding_cache_size: int = 1000,
        strategy_cache_size: int = 200,
        ttl_seconds: int = 300,
    ):
        # Query result cache (most expensive to recompute)
        self.query_cache = LRUCache(query_cache_size, ttl_seconds)

        # Embedding cache (encoded query vectors)
        self.embedding_cache = LRUCache(embedding_cache_size, ttl_seconds)

        # Strategy cache (search strategy decisions)
        self.strategy_cache = LRUCache(strategy_cache_size, ttl_seconds)

        logger.info(
            f"HybridRecallCache initialized: "
            f"query={query_cache_size}, embedding={embedding_cache_size}, "
            f"strategy={strategy_cache_size}, ttl={ttl_seconds}s"
        )

    @staticmethod
    def _hash_query(query: str, **kwargs: Any) -> str:
        """Generate cache key from query and parameters."""
        # Normalize query
        normalized = query.strip().lower()

        # Include relevant kwargs in key
        key_parts = [normalized]
        for k in sorted(kwargs.keys()):
            if k in ("limit", "memory_type", "include_cold", "rrf_k"):
                key_parts.append(f"{k}={kwargs[k]}")

        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_query_result(self, query: str, **kwargs: Any) -> list[Any] | None:
        """Get cached query results."""
        key = self._hash_query(query, **kwargs)
        return self.query_cache.get(key)

    def put_query_result(self, query: str, results: list[Any], **kwargs: Any) -> None:
        """Cache query results."""
        key = self._hash_query(query, **kwargs)
        self.query_cache.put(key, results)

    def get_embedding(self, query: str) -> Any | None:
        """Get cached query embedding."""
        key = hashlib.md5(query.strip().lower().encode()).hexdigest()
        return self.embedding_cache.get(key)

    def put_embedding(self, query: str, embedding: Any) -> None:
        """Cache query embedding."""
        key = hashlib.md5(query.strip().lower().encode()).hexdigest()
        self.embedding_cache.put(key, embedding)

    def get_strategy(self, query: str) -> str | None:
        """Get cached search strategy."""
        key = hashlib.md5(query.strip().lower().encode()).hexdigest()
        return self.strategy_cache.get(key)

    def put_strategy(self, query: str, strategy: str) -> None:
        """Cache search strategy."""
        key = hashlib.md5(query.strip().lower().encode()).hexdigest()
        self.strategy_cache.put(key, strategy)

    def clear_all(self) -> None:
        """Clear all caches."""
        self.query_cache.clear()
        self.embedding_cache.clear()
        self.strategy_cache.clear()

    def stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "query_cache": self.query_cache.stats(),
            "embedding_cache": self.embedding_cache.stats(),
            "strategy_cache": self.strategy_cache.stats(),
        }


# Global cache instance
_cache_instance: HybridRecallCache | None = None
_cache_lock = threading.Lock()


def get_hybrid_cache() -> HybridRecallCache:
    """Get or create the global HybridRecallCache singleton."""
    global _cache_instance
    with _cache_lock:
        if _cache_instance is None:
            _cache_instance = HybridRecallCache()
        return _cache_instance
