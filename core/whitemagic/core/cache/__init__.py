"""WhiteMagic Unified Cache package."""

from whitemagic.core.cache.unified_cache_bridge import (
    UnifiedCacheBridge,
    get_unified_cache,
    is_rust_cache_available,
)

__all__ = ["UnifiedCacheBridge", "get_unified_cache", "is_rust_cache_available"]
