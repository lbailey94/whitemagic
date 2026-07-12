"""MCP handlers for Cache Coherence Registry (Bridge 2 — Cache Catharsis)."""

from typing import Any


def handle_cache_status(**kwargs: Any) -> dict[str, Any]:
    """Return current status of all registered caches."""
    from whitemagic.core.memory.cache_registry import get_cache_registry

    registry = get_cache_registry()
    caches = getattr(registry, "_caches", {})
    return {"status": "success", "registered_caches": list(caches.keys()), "count": len(caches)}


def handle_cache_flush(**kwargs: Any) -> dict[str, Any]:
    """Trigger an immediate cache catharsis (flush stale entries)."""
    from whitemagic.core.memory.cache_registry import get_cache_registry

    registry = get_cache_registry()
    registry.flush_all()
    return {"status": "success", "message": "All caches flushed"}


def handle_cache_tune(**kwargs: Any) -> dict[str, Any]:
    """Analyze cache stats and return TTL tuning recommendations.

    Combines cache stats and auto_tune_ttls() recommendations into a single
    response so agents can assess cache health and apply adjustments.
    """
    from whitemagic.core.memory.cache_registry import get_cache_registry

    registry = get_cache_registry()
    stats = registry.get_all_stats()
    recommendations = registry.auto_tune_ttls()
    return {
        "status": "success",
        "stats": stats,
        "recommendations": recommendations,
    }
