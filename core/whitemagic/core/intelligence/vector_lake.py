# ruff: noqa: BLE001
"""Vector Lake — cross-galaxy vector search facade (Group B — fresh implementation).

Provides a unified API for vector operations across the holographic
memory substrate. This is a facade over whitemagic.core.memory.holographic
and whitemagic.core.memory.vector, exposing a single get_vector_lake()
singleton.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_lake_instance: VectorLake | None = None
_lake_lock = Lock()


class VectorLake:
    """Unified vector lake over holographic memory."""

    def __init__(self) -> None:
        self._holographic = None
        self._vector = None

    def _ensure(self) -> None:
        if self._holographic is None:
            try:
                from whitemagic.core.memory.holographic import get_holographic_memory
                self._holographic = get_holographic_memory()  # type: ignore[assignment]
            except Exception as exc:
                logger.debug("Holographic memory unavailable: %s", exc, exc_info=True)
        if self._vector is None:
            try:
                from whitemagic.core.memory.vector import VectorSearch
                self._vector = VectorSearch()  # type: ignore[assignment]
            except Exception as exc:
                logger.debug("Vector search unavailable: %s", exc, exc_info=True)

    def get_holographic_sample(self, limit: int = 100) -> list[Any]:
        """Return a sample of memories from the holographic substrate."""
        self._ensure()
        if self._holographic is None:
            return []
        # Best-effort: try common accessor names
        for method_name in ("get_recent", "sample", "list_recent", "recent"):
            method = getattr(self._holographic, method_name, None)
            if method is not None:
                try:
                    return list(method(limit=limit))
                except TypeError:
                    try:
                        return list(method(limit))
                    except Exception:
                        pass
                except Exception as exc:
                    logger.debug("Method %s failed: %s", method_name, exc, exc_info=True)
        return []

    def vector_search(self, query: str, limit: int = 10) -> list[Any]:
        """Run vector similarity search."""
        self._ensure()
        if self._vector is None:
            return []
        method = getattr(self._vector, "search", None)
        if method is None:
            return []
        try:
            return list(method(query, limit=limit))
        except Exception as exc:
            logger.debug("Vector search failed: %s", exc, exc_info=True)
            return []


def get_vector_lake() -> VectorLake:
    """Return the process-wide VectorLake singleton."""
    global _lake_instance
    with _lake_lock:
        if _lake_instance is None:
            _lake_instance = VectorLake()
        return _lake_instance


__all__ = ["VectorLake", "get_vector_lake"]
