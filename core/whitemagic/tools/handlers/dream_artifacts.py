"""Handlers for Dream Artifact tools.

Tools:
  dream.list    — List dream artifacts
  dream.read    — Read a single dream artifact
  dream.promote — Promote a dream to memory
  dream.expire  — Mark a dream as expired
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.tools.unified_api import make_result

logger = logging.getLogger(__name__)


def handle_dream_list(params: dict[str, Any]) -> dict[str, Any]:
    """List dream artifacts."""
    try:
        from whitemagic.core.dreaming.dream_artifacts import list_dreams

        status_filter = params.get("status")
        dreams = list_dreams(status_filter=status_filter)
        return make_result(
            "dream.list",
            {
                "count": len(dreams),
                "status_filter": status_filter,
                "dreams": dreams,
            },
        )
    except Exception as exc:
        logger.error("dream.list error: %s", exc, exc_info=True)
        return make_result("dream.list", {}, error=str(exc))


def handle_dream_read(params: dict[str, Any]) -> dict[str, Any]:
    """Read a single dream artifact by ID."""
    try:
        from whitemagic.core.dreaming.dream_artifacts import read_dream, revisit_dream

        dream_id = params.get("dream_id", "")
        if not dream_id:
            return make_result("dream.read", {}, error="Missing 'dream_id' parameter")
        data = read_dream(dream_id)
        if data is None:
            return make_result("dream.read", {}, error=f"Dream not found: {dream_id}")
        # Auto-increment revisit count on read
        revisit_dream(dream_id)
        return make_result("dream.read", {"dream": data})
    except Exception as exc:
        logger.error("dream.read error: %s", exc, exc_info=True)
        return make_result("dream.read", {}, error=str(exc))


def handle_dream_promote(params: dict[str, Any]) -> dict[str, Any]:
    """Promote a dream artifact to a real memory."""
    try:
        from whitemagic.core.dreaming.dream_artifacts import promote_dream

        dream_id = params.get("dream_id", "")
        memory_id = params.get("memory_id")
        if not dream_id:
            return make_result(
                "dream.promote", {}, error="Missing 'dream_id' parameter"
            )
        result = promote_dream(dream_id, memory_id=memory_id)
        if result is None:
            return make_result(
                "dream.promote", {}, error=f"Dream not found: {dream_id}"
            )
        return make_result(
            "dream.promote",
            {
                "dream_id": dream_id,
                "status": result.get("status"),
                "promoted_to_memory_id": result.get("promoted_to_memory_id"),
            },
        )
    except Exception as exc:
        logger.error("dream.promote error: %s", exc, exc_info=True)
        return make_result("dream.promote", {}, error=str(exc))


def handle_dream_expire(params: dict[str, Any]) -> dict[str, Any]:
    """Expire a dream artifact (soft delete)."""
    try:
        from whitemagic.core.dreaming.dream_artifacts import expire_dream

        dream_id = params.get("dream_id", "")
        if not dream_id:
            return make_result("dream.expire", {}, error="Missing 'dream_id' parameter")
        result = expire_dream(dream_id)
        if result is None:
            return make_result("dream.expire", {}, error=f"Dream not found: {dream_id}")
        return make_result(
            "dream.expire",
            {
                "dream_id": dream_id,
                "status": result.get("status"),
            },
        )
    except Exception as exc:
        logger.error("dream.expire error: %s", exc, exc_info=True)
        return make_result("dream.expire", {}, error=str(exc))
