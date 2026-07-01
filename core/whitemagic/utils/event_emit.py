"""Shared Gan Ying event emission — replaces 18 duplicate _emit functions.

Usage:
    from whitemagic.utils.event_emit import make_emitter

    _emit = make_emitter("memory")

    _emit("memory.created", {"id": "123"})
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def make_emitter(source: str = "system"):
    """Create a best-effort event emitter bound to a source name.

    Args:
        source: The source label for emitted events (e.g. "memory", "broker").

    Returns:
        A function(event_type: str, data: dict) -> None that emits events
        via the Gan Ying bus, swallowing import/connection errors.
    """

    def _emit(event_type: str, data: dict[str, Any]) -> None:
        """Best-effort Gan Ying event emission."""
        try:
            from whitemagic.core.resonance import emit_event

            emit_event(event_type, data, source=source)
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Silenced %s emit error: %s", source, e, exc_info=True)

    return _emit


def emit(event_type: str, data: dict[str, Any], source: str = "system") -> None:
    """Best-effort Gan Ying event emission (direct call)."""
    try:
        from whitemagic.core.resonance import emit_event

        emit_event(event_type, data, source=source)
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug("Silenced emit error: %s", e, exc_info=True)
