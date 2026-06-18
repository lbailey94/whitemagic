"""Aspirational tool handlers — Grimoire auto-cast, session context, wisdom council."""
from typing import Any


def handle_navigate_grimoire(**kwargs: Any) -> dict[str, Any]:
    """Auto-cast: find the best Gana chapter for the current task."""
# ruff: noqa: BLE001
    query = kwargs.get("query", "")
    if not query:
        return {"status": "error", "error_code": "invalid_params", "message": "query is required"}

    from whitemagic.core.intelligence.garden_gana_registry import (
        calculate_resonance,
        get_by_garden,
    )

    resonance = calculate_resonance(query)
    if not resonance:
        return {
            "status": "success",
            "query": query,
            "recommendation": "gana_horn",
            "reason": "No strong resonance detected — default to Session Initiation",
            "resonance": {},
        }

    # Top match
    top_garden = list(resonance.keys())[0]
    entry = get_by_garden(top_garden)
    if not entry:
        return {"status": "error", "error_code": "internal_error", "message": f"Garden {top_garden} not found in registry"}

    return {
        "status": "success",
        "query": query,
        "recommended_gana": entry.gana_tool,
        "gana_name": entry.gana,
        "garden": entry.garden,
        "element": entry.element.value,
        "emotion": entry.primary_emotion,
        "keywords_matched": resonance[top_garden]["score"],
        "resonance": resonance,
        "reason": f"Query resonates with '{entry.garden}' — {entry.description}",
    }


def handle_get_session_context(**kwargs: Any) -> dict[str, Any]:
    """Retrieve full session state with all metadata."""
    context = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "session": {},
        "memory": {},
        "resonance": {},
        "health": {},
    }

    try:
        from whitemagic.core.memory.manager import MemoryManager
        mm = MemoryManager()
        context["memory"]["db_path"] = str(mm.db_path) if hasattr(mm, "db_path") else "unknown"
        context["memory"]["initialized"] = True
    except Exception as e:
        context["memory"]["error"] = str(e)

    try:
        from whitemagic.core.resonance import get_bus
        bus = get_bus()
        context["resonance"]["queue_size"] = bus.queue.qsize() if hasattr(bus, "queue") else 0
        context["resonance"]["history_count"] = len(bus._history) if hasattr(bus, "_history") else 0
    except Exception as e:
        context["resonance"]["error"] = str(e)

    try:
        from whitemagic.core.health_monitor import HealthMonitor
        hm = HealthMonitor()
        health = hm.check_system_health(deep_scan=False)
        context["health"] = health
    except Exception as e:
        context["health"]["error"] = str(e)

    return {"status": "success", "context": context}


def handle_consult_wisdom_council(**kwargs: Any) -> dict[str, Any]:
    """Multi-perspective deliberation — Wisdom Council."""
    query = kwargs.get("query", "")
    if not query:
        return {"status": "error", "error_code": "invalid_params", "message": "query is required"}

    # Simulate perspectives from the 28 Ganas
    perspectives = []
    # Select 3-5 relevant Ganas based on query resonance
    from whitemagic.core.intelligence.garden_gana_registry import (
        GARDEN_GANA_REGISTRY,
        calculate_resonance,
    )
    resonance = calculate_resonance(query)
    top_gardens = list(resonance.keys())[:5]

    for garden_name in top_gardens:
        for entry in GARDEN_GANA_REGISTRY:
            if entry.garden == garden_name:
                perspectives.append({
                    "gana": entry.gana,
                    "garden": entry.garden,
                    "perspective": f"From the garden of {entry.garden}: consider {entry.primary_emotion.lower()} as your guide.",
                    "resonance_score": resonance[garden_name]["score"],
                })
                break

    # Add mandatory perspectives
    perspectives.insert(0, {
        "gana": "Three Stars (Shen)",
        "garden": "reverence",
        "perspective": "The council asks: what is the deepest truth beneath this question?",
        "resonance_score": 1,
    })

    return {
        "status": "success",
        "query": query,
        "perspectives": perspectives,
        "consensus": "Deliberation complete. Review each perspective before deciding.",
    }
