"""Grimoire walkthrough handler."""
from typing import Any


def handle_grimoire_walkthrough(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a grimoire walkthrough event.

    Returns:
        dict[str, Any]
    """
    chapter = kwargs.get("chapter")
    quadrant = kwargs.get("quadrant")

    from whitemagic.core.intelligence.garden_gana_registry import (
        GARDEN_GANA_REGISTRY,
        Quadrant,
        get_by_gana,
    )

    if chapter:
        entry = get_by_gana(chapter)
        if entry:
            return {
                "status": "success",
                "chapter": entry.gana,
                "garden": entry.garden,
                "quadrant": entry.quadrant.value,
                "element": entry.element.value,
                "emotion": entry.primary_emotion,
                "keywords": entry.resonance_keywords,
                "description": entry.description,
            }
        return {"status": "error", "error_code": "not_found", "message": f"Chapter {chapter} not found"}

    if quadrant:
        try:
            q = Quadrant(quadrant)
        except ValueError:
            return {"status": "error", "error_code": "invalid_params", "message": f"Invalid quadrant: {quadrant}"}
        entries = [e for e in GARDEN_GANA_REGISTRY if e.quadrant == q]
        return {
            "status": "success",
            "quadrant": quadrant,
            "chapters": [
                {"gana": e.gana, "garden": e.garden, "element": e.element.value}
                for e in entries
            ],
        }

    # Default: return full grimoire index
    return {
        "status": "success",
        "chapters": [
            {
                "gana": e.gana,
                "garden": e.garden,
                "quadrant": e.quadrant.value,
                "element": e.element.value,
                "emotion": e.primary_emotion,
            }
            for e in GARDEN_GANA_REGISTRY
        ],
        "total": len(GARDEN_GANA_REGISTRY),
    }
