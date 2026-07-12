# ruff: noqa: BLE001
# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Cache Registry (Consolidated v2.2).
=====================================
Centralized hub for all system caches. Enables unified monitoring,
manual flushing, and automated "Dream Catharsis" (invalidation during REM).

Part of Milestone 4.4: The Living System.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

class CacheRegistry:
    """Registry for managing multiple system caches.

    Supports unified monitoring, manual flushing, automated Dream Catharsis
    (invalidation during REM), per-namespace version tracking, and stats
    collection from all registered caches.
    """

    def __init__(self):
        self._caches: dict[str, Callable[[], None]] = {}
        self._stats_funcs: dict[str, Callable[[], dict[str, Any]]] = {}
        self._cleanup_funcs: dict[str, Callable[[], int]] = {}
        self._invalidate_funcs: dict[str, Callable[[str], int]] = {}
        self._versions: dict[str, int] = {}
        self._redis_subscribed = False

    def _subscribe_redis(self) -> None:
        """Subscribe to Redis pub/sub for cross-process cache invalidation.

        Called lazily when REDIS_URL is set and WM_SILENT_INIT is not 1.
        Uses _from_redis=True on invalidate_namespace to prevent echo loops.
        """
        if self._redis_subscribed:
            return
        self._redis_subscribed = True
        try:
            from whitemagic.cache.redis import get_redis_cache
            get_redis_cache().subscribe_invalidation(
                lambda ns: self.invalidate_namespace(ns, _from_redis=True)
            )
        except Exception:
            pass

    def register(
        self,
        name: str,
        flush_func: Callable[[], None],
        stats_func: Callable[[], dict[str, Any]] | None = None,
        cleanup_func: Callable[[], int] | None = None,
        invalidate_func: Callable[[str], int] | None = None,
    ) -> None:
        """Register a cache with optional stats, cleanup, and invalidate callbacks.

        Args:
            name: Unique cache identifier.
            flush_func: Called by flush_all() -- clears entire cache.
            stats_func: Called by get_all_stats() -- returns cache stats dict.
            cleanup_func: Called by flush_stale() -- removes expired entries,
                returns count removed.
            invalidate_func: Called by invalidate_namespace() -- takes namespace
                string, returns count invalidated.
        """
        self._caches[name] = flush_func
        if stats_func is not None:
            self._stats_funcs[name] = stats_func
        if cleanup_func is not None:
            self._cleanup_funcs[name] = cleanup_func
        if invalidate_func is not None:
            self._invalidate_funcs[name] = invalidate_func
        self._versions.setdefault(name, 0)
        logger.info("Cache registered: %s", name)

    def flush_all(self) -> dict[str, Any]:
        """Invoke all registered flush functions.

        Returns a summary dict with per-cache flush results.
        """
        logger.info("Flushing all system caches...")
        results: dict[str, Any] = {}
        for name, flush in self._caches.items():
            try:
                flush()
                results[name] = "ok"
                logger.debug("  Flushed: %s", name)
            except Exception as e:
                results[name] = f"error: {e}"
                logger.error("  Failed to flush %s: %s", name, e, exc_info=True)
        return results

    def flush_stale(self) -> dict[str, Any]:
        """Remove expired/stale entries from all caches that support cleanup.

        Used by Dream Catharsis to release memory without losing hot entries.

        Returns:
            Summary dict with per-cache counts and total.
        """
        logger.info("Cache Catharsis -- flushing stale entries...")
        total = 0
        per_cache: dict[str, int] = {}
        for name, cleanup in self._cleanup_funcs.items():
            try:
                removed = cleanup()
                per_cache[name] = removed
                total += removed
                logger.debug("  Stale entries removed from %s: %d", name, removed)
            except Exception as e:
                per_cache[name] = -1
                logger.error("  Cleanup failed for %s: %s", name, e, exc_info=True)
        return {"total": total, "per_cache": per_cache}

    def invalidate_namespace(self, namespace: str, _from_redis: bool = False) -> dict[str, int]:
        """Invalidate a specific namespace across all caches that support it.

        Used by the write-invalidate protocol after memory writes.
        Also publishes to Redis pub/sub for cross-process invalidation
        (unless _from_redis=True, to prevent echo loops).

        Args:
            namespace: Namespace to invalidate (e.g. "query", "semantic",
                "hybrid_recall", or a galaxy name).
            _from_redis: If True, this call was triggered by Redis pub/sub
                — skip publishing to avoid echo.

        Returns:
            Dict mapping cache name to count of entries invalidated.
        """
        results: dict[str, int] = {}
        for name, inv_fn in self._invalidate_funcs.items():
            try:
                count = inv_fn(namespace)
                if count > 0:
                    results[name] = count
                    logger.debug("  Invalidated %d entries in %s for ns=%s", count, name, namespace)
            except Exception as e:
                logger.debug("  Invalidate failed for %s: %s", name, e)
        self._versions[namespace] = self._versions.get(namespace, 0) + 1

        # Publish to Redis for cross-process invalidation (unless echo)
        if not _from_redis:
            try:
                import os
                if os.environ.get("REDIS_URL") and os.environ.get("WM_SILENT_INIT") != "1":
                    self._subscribe_redis()
                    from whitemagic.cache.redis import get_redis_cache
                    get_redis_cache().publish_invalidation(namespace)
            except Exception:
                pass

        return results

    def get_version(self, namespace: str) -> int:
        """Get the current version counter for a namespace.

        Incremented each time invalidate_namespace() is called for this namespace.
        Used by graph.py and other components to detect stale cached data.
        """
        return self._versions.get(namespace, 0)

    def invalidate_spatial(
        self,
        coords: tuple[float, float, float, float],
        radius: float = 0.3,
    ) -> dict[str, int]:
        """Invalidate cache entries within a holographic spatial radius.

        Uses 4D holographic coordinates (x, y, z, w) to identify cache entries
        that are spatially close to a given point. Entries within the Euclidean
        radius are invalidated. This enables fine-grained invalidation when a
        memory is updated — only cache entries in the same region are flushed,
        rather than invalidating an entire namespace.

        Args:
            coords: (x, y, z, w) holographic coordinates of the updated memory.
            radius: Euclidean distance threshold for invalidation.

        Returns:
            Dict mapping cache name to count of entries invalidated.
        """
        results: dict[str, int] = {}
        x0, y0, z0, w0 = coords

        for name, inv_fn in self._invalidate_funcs.items():
            try:
                # Check if the invalidate function supports spatial coords
                # by inspecting its signature
                import inspect
                sig = inspect.signature(inv_fn)
                if len(sig.parameters) >= 2:
                    # Pass coords + radius as second arg
                    count = inv_fn(f"spatial:{x0:.2f},{y0:.2f},{z0:.2f},{w0:.2f}", radius)
                else:
                    # Fallback: invalidate entire namespace
                    count = inv_fn(f"spatial:{x0:.2f},{y0:.2f},{z0:.2f},{w0:.2f}")
                if count > 0:
                    results[name] = count
                    logger.debug(
                        "  Spatial invalidation: %d entries in %s (r=%.2f)",
                        count, name, radius,
                    )
            except Exception as e:
                logger.debug("  Spatial invalidate failed for %s: %s", name, e)

        return results

    def get_all_stats(self) -> dict[str, Any]:
        """Collect stats from all registered caches that support it."""
        stats: dict[str, Any] = {}
        total_hits = 0
        total_misses = 0
        for name, stats_fn in self._stats_funcs.items():
            try:
                s = stats_fn()
                stats[name] = s
                total_hits += int(s.get("hits", 0))
                total_misses += int(s.get("misses", 0))
            except Exception as e:
                stats[name] = {"error": str(e)}
        aggregate_rate = round(
            (total_hits / max(total_hits + total_misses, 1)) * 100, 2
        )
        return {
            "caches": stats,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "aggregate_hit_rate": aggregate_rate,
            "registered_count": len(self._caches),
        }

    def get_status(self) -> dict[str, Any]:
        """Get the status of registered caches."""
        return {
            "registered_count": len(self._caches),
            "caches": list(self._caches.keys()),
            "stats_enabled": list(self._stats_funcs.keys()),
            "cleanup_enabled": list(self._cleanup_funcs.keys()),
            "invalidate_enabled": list(self._invalidate_funcs.keys()),
        }

    def auto_tune_ttls(self) -> dict[str, Any]:
        """Analyze cache stats and return TTL tuning recommendations.

        For each cache with stats, evaluates hit rate and eviction count:
        - High hit rate + low evictions → suggest decreasing TTL (free memory)
        - Low hit rate + high evictions → suggest increasing TTL (keep data longer)
        - Otherwise → maintain

        Returns:
            Dict mapping cache name to tuning recommendation.
        """
        recommendations: dict[str, Any] = {}
        for name, stats_fn in self._stats_funcs.items():
            try:
                s = stats_fn()
                hit_rate = float(s.get("hit_rate", 0.0))
                evictions = int(s.get("evictions", 0))
                size = int(s.get("size", 0))

                if hit_rate > 80.0 and evictions < 10 and size > 100:
                    action = "decrease_ttl"
                    reason = f"High hit rate ({hit_rate:.1f}%) with low evictions ({evictions}) — can shorten TTL to free memory"
                elif hit_rate < 30.0 and evictions > 100:
                    action = "increase_ttl"
                    reason = f"Low hit rate ({hit_rate:.1f}%) with high evictions ({evictions}) — extend TTL to retain useful data"
                else:
                    action = "maintain"
                    reason = f"Balanced: hit_rate={hit_rate:.1f}%, evictions={evictions}, size={size}"

                recommendations[name] = {
                    "action": action,
                    "reason": reason,
                    "current_hit_rate": round(hit_rate, 2),
                    "current_evictions": evictions,
                    "current_size": size,
                }
            except Exception as e:
                recommendations[name] = {"action": "error", "reason": str(e)}
        return recommendations

# Global singleton
_registry: CacheRegistry | None = None


def get_cache_registry() -> CacheRegistry:
    """Get the global cache registry singleton."""
    global _registry
    if _registry is None:
        _registry = CacheRegistry()
        # Auto-subscribe to CACHE_INVALIDATE events from GanYingBus
        try:
            from whitemagic.core.resonance import EventType, get_bus
            bus = get_bus()

            def _on_cache_invalidate(event):
                if event.event_type == EventType.CACHE_INVALIDATE:
                    ns = event.data.get("namespace", "")
                    if ns:
                        _registry.invalidate_namespace(ns)

            bus.listen(EventType.CACHE_INVALIDATE, _on_cache_invalidate)
            logger.debug("CacheRegistry subscribed to CACHE_INVALIDATE events")
        except Exception:
            logger.debug("GanYingBus subscription skipped", exc_info=True)
    return _registry
