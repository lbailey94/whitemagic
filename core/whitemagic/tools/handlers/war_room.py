"""War Room tool handlers."""
import logging
from typing import Any

from whitemagic.core.intelligence.wisdom.art_of_war import get_war_engine

logger = logging.getLogger(__name__)

def handle_art_of_war_chapter(**kwargs: Any) -> dict[str, Any]:
    """Get principles from a specific chapter of the Art of War."""
    try:
        chapter = int(kwargs.get("chapter") or kwargs.get("chapter_number") or 1)
        engine = get_war_engine()
        principles = engine.consult_chapter(chapter)

        return {
            "status": "success",
            "chapter": chapter,
            "principles": [
                {
                    "chapter": p.chapter,
                    "principle": p.principle,
                    "application": p.application,
                    "keywords": p.keywords
                }
                for p in principles
            ]
        }
    except Exception as e:
        logger.error(f"Error in handle_art_of_war_chapter: {e}")
        return {"status": "error", "message": str(e)}

def handle_art_of_war_wisdom(**kwargs: Any) -> dict[str, Any]:
    """Get Art of War wisdom for a situation."""
    try:
        situation = kwargs.get("situation", "")
        engine = get_war_engine()
        p = engine.get_war_wisdom(situation)
        return {
            "status": "success",
            "principle": {
                "chapter": p.chapter,
                "principle": p.principle,
                "application": p.application,
                "keywords": p.keywords
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_art_of_war_terrain(**kwargs: Any) -> dict[str, Any]:
    """Assess the 'terrain' of a given objective."""
    return handle_assess_terrain(**kwargs)

def handle_art_of_war_campaign(**kwargs: Any) -> dict[str, Any]:
    """Generate a full campaign plan for an objective."""
    return handle_plan_campaign(**kwargs)

def handle_war_room_status(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "war_room": "active"}

def handle_war_room_plan(**kwargs: Any) -> dict[str, Any]:
    return handle_plan_campaign(**kwargs)

def handle_war_room_execute(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "message": "Campaign execution started"}

def handle_war_room_hierarchy(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "hierarchy": "Commander -> Officers -> Clones"}

def handle_war_room_campaigns(**kwargs: Any) -> dict[str, Any]:
    engine = get_war_engine()
    return {"status": "success", "campaigns": engine.list_campaigns()}

def handle_war_room_phase(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "current_phase": "reconnaissance"}

def handle_doctrine_summary(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "doctrine": "Zheng & Qi combined arms"}

def handle_doctrine_stratagems(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "stratagems": ["36 Stratagems loaded"]}

def handle_doctrine_force(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "force_composition": "Tokio Light Infantry + Ralph Probes"}

def handle_fool_guard_status(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "fool_guard": "active"}

def handle_fool_guard_dare_to_die(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "corps": "Dare-to-Die deployment ready"}

def handle_fool_guard_ralph(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "ralph": "I'm helping! (Ralph probe deployed)"}

def handle_assess_terrain(**kwargs: Any) -> dict[str, Any]:
    """Assess the 'terrain' of a given objective."""
    try:
        objective = kwargs.get("objective", "")
        engine = get_war_engine()
        assessment = engine.assess_terrain(objective)
        return {"status": "success", "assessment": assessment.__dict__}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_plan_campaign(**kwargs: Any) -> dict[str, Any]:
    """Generate a full campaign plan for an objective."""
    try:
        objective = kwargs.get("objective", "")
        engine = get_war_engine()
        plan = engine.plan_campaign(objective)
        return {"status": "success", "plan": plan.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
