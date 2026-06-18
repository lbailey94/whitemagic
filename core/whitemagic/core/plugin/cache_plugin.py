# Copyright 2026 WhiteMagic Contributors
"""Cache Plugin — System-Wide Cache Controller (E4).
Wraps the CacheRegistry for unified monitoring and flushing.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class CachePlugin:
    """CachePlugin: cache plugin."""
    name = "cache"
    version = "1.0.0"
    description = "Cache Registry — Centralized control for all system caches and buffers"

    def __init__(self) -> None:
        self._registry: Any | None = None
        self._running = False

    def start(self) -> None:
        """
        Perform the start operation.
        
        Returns:
            None
        """
        from whitemagic.core.memory.cache_registry import get_cache_registry
        self._registry = get_cache_registry()
        self._running = True
        logger.info("CachePlugin started")

    def stop(self) -> None:
        """
        Perform the stop operation.
        
        Returns:
            None
        """
        self._running = False
        logger.info("CachePlugin stopped")

    def flush(self) -> None:
        """Trigger a manual flush of all caches."""
        if self._registry:
            self._registry.flush_all()

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.
        
        Returns:
            dict[str, Any]
        """
        if not self._registry:
            return {"running": False}
        return {
            "name": self.name,
            "running": self._running,
            "registry_status": self._registry.get_status()
        }

def register():
    """
    Perform the register operation.
    """
    try:
        from whitemagic.core.plugin import get_registry
        get_registry().register(CachePlugin())
    except (ImportError, ModuleNotFoundError):
        pass
