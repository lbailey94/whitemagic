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
    """Registry for managing multiple system caches."""
    def __init__(self):
        self._caches: dict[str, Callable[[], None]] = {}

    def register(self, name: str, flush_func: Callable[[], None]):
        """Register a cache flush function."""
        self._caches[name] = flush_func
        logger.info(f"💾 Cache registered: {name}")

    def flush_all(self):
        """Invoke all registered flush functions."""
        logger.info("🌊 Flushing all system caches...")
        for name, flush in self._caches.items():
            try:
                flush()
                logger.debug(f"  Flushed: {name}")
            except Exception as e:
                logger.error("  Failed to flush %s: %s", name, e, exc_info=True)

    def get_status(self) -> dict[str, Any]:
        """Get the status of registered caches."""
        return {
            "registered_count": len(self._caches),
            "caches": list(self._caches.keys())
        }

# Global singleton
_registry: CacheRegistry | None = None

def get_cache_registry() -> CacheRegistry:
    """
    Get the cache registry.

    Returns:
        CacheRegistry
    """
    global _registry
    if _registry is None:
        _registry = CacheRegistry()
    return _registry
