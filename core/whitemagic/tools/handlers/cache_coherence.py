"""MCP handlers for Cache Coherence Registry (Bridge 2 — Cache Catharsis)."""

from typing import Any


def handle_cache_status(**kwargs: Any) -> dict[str, Any]:
    """Return current status of all registered caches."""
    from whitemagic.core.memory.cache_registry import get_cache_registry

    registry = get_cache_registry()
    return {"status": "success", **registry.status()}


def handle_cache_flush(**kwargs: Any) -> dict[str, Any]:
    """Trigger an immediate cache catharsis (flush stale entries)."""
    tag = kwargs.get("tag")
    from whitemagic.core.memory.cache_registry import get_cache_registry

    registry = get_cache_registry()
    result = registry.flush_stale(tag=tag)
    return {"status": "success", **result}
