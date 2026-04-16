"""MCP handlers for Grimoire 2.0."""

import logging
from typing import Any

from whitemagic.core.intelligence.grimoire_engine import get_grimoire_engine

logger = logging.getLogger(__name__)


def handle_grimoire_suggest(**kwargs: Any) -> dict[str, Any]:
    """Suggest spells for a given task context."""
    task = kwargs.get("task", "")
    if not task:
        return {"status": "error", "message": "task is required"}

    emotional_state = kwargs.get("emotional_state", "neutral")
    limit = int(kwargs.get("limit", 5))
    keywords = kwargs.get("keywords", [])

    grimoire = get_grimoire_engine()
    grimoire.awaken()
    grimoire.update_context(task=task, emotional_state=emotional_state, keywords=keywords)

    recommendations = grimoire.recommend_spells(max_results=limit)

    result_list = []
    for r in recommendations:
        result_list.append({
            "spell_name": r.spell_name,
            "chapter": r.chapter,
            "confidence": round(r.confidence, 3),
            "reason": r.reason,
            "auto_cast": r.auto_cast,
        })

    # Return with context info
    ctx = grimoire.context

    return {
        "status": "success",
        "task": task,
        "suggestions": result_list,
        "count": len(result_list),
        "unified_cycle_phase": {
            "wu_xing": ctx.wu_xing.value,
            "yin_yang": ctx.yin_yang.value,
        }
    }


def handle_grimoire_cast(**kwargs: Any) -> dict[str, Any]:
    """Mock auto-cast endpoint. The Grimoire Engine handles recommendations for manual processing via Dispatch."""
    return {"status": "error", "message": "Direct spell casting is handled natively via tool sequence in Grimoire 2.0. Use 'grimoire_suggest' then execute the individual tools."}


def handle_grimoire_recommend(**kwargs: Any) -> dict[str, Any]:
    """Alias for grimoire_suggest."""
    return handle_grimoire_suggest(**kwargs)


def handle_grimoire_auto_status(**kwargs: Any) -> dict[str, Any]:
    """Get Grimoire Engine Status."""
    grimoire = get_grimoire_engine()
    return {
        "status": "success",
        "active_state": grimoire.state.value,
        "wu_xing_affinity": grimoire.context.wu_xing.value,
        "yin_yang_affinity": grimoire.context.yin_yang.value,
    }
