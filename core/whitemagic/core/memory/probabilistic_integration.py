# ruff: noqa: BLE001
"""Integration layer connecting MemoryAnalytics to UnifiedMemory.

Registers store and search hooks so that every memory operation
automatically feeds the probabilistic data structures (HLL + CMS)
without modifying the core UnifiedMemory class.

Usage:
    from whitemagic.core.memory.probabilistic_integration import init_analytics
    init_analytics()  # Call once at startup

    # Later, query analytics:
    from whitemagic.core.memory.probabilistic_integration import get_analytics
    analytics = get_analytics()
    print(analytics.estimate_distinct_count())
"""
from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.memory.probabilistic import MemoryAnalytics
from whitemagic.core.memory.unified import (
    Memory,
    register_search_hook,
    register_store_hook,
)

logger = logging.getLogger(__name__)

_analytics: MemoryAnalytics | None = None
_initialized = False


def init_analytics(
    hll_precision: int = 14,
    cms_width: int = 4096,
    cms_depth: int = 5,
) -> MemoryAnalytics:
    """Initialize memory analytics and register hooks.

    Call once at startup. Subsequent calls return the existing instance.
    """
    global _analytics, _initialized
    if _initialized and _analytics is not None:
        return _analytics

    _analytics = MemoryAnalytics(
        hll_precision=hll_precision,
        cms_width=cms_width,
        cms_depth=cms_depth,
    )

    register_store_hook(_on_memory_stored)
    register_search_hook(_on_memory_searched)

    _initialized = True
    logger.info(
        "MemoryAnalytics initialized: HLL(p=%d) + CMS(%dx%d), ~%d bytes",
        hll_precision, cms_width, cms_depth, _analytics.memory_bytes(),
    )
    return _analytics


def get_analytics() -> MemoryAnalytics | None:
    """Get the singleton analytics instance, or None if not initialized."""
    return _analytics


def _on_memory_stored(memory: Memory) -> None:
    """Hook called after every memory store operation."""
    if _analytics is None:
        return
    try:
        tags = memory.tags if isinstance(memory.tags, (set, list)) else []
        source = str(memory.metadata.get("source", "")) if memory.metadata else ""
        _analytics.observe_memory(
            memory_id=str(memory.id),
            tags=tags,
            source=source,
        )
    except Exception as exc:
        logger.debug("MemoryAnalytics store hook error: %s", exc)


def _on_memory_searched(results: list[Memory]) -> None:
    """Hook called after every memory search/recall operation."""
    if _analytics is None:
        return
    try:
        for memory in results:
            _analytics.observe_access(str(memory.id))
    except Exception as exc:
        logger.debug("MemoryAnalytics search hook error: %s", exc)


def analytics_summary() -> dict[str, Any]:
    """Get a summary of memory analytics, or empty dict if not initialized."""
    if _analytics is None:
        return {"status": "not_initialized"}
    return _analytics.summary()
