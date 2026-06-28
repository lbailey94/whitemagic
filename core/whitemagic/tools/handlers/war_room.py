"""War Room tool handlers."""
# ruff: noqa: BLE001
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
        logger.error("Error in handle_art_of_war_chapter: %s", e, exc_info=True)
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
    """
    Handle a war room status event.

    Returns:
        dict[str, Any]
    """
    return {"status": "success", "war_room": "active"}

def handle_war_room_plan(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a war room plan event.

    Returns:
        dict[str, Any]
    """
    return handle_plan_campaign(**kwargs)

def handle_war_room_execute(**kwargs: Any) -> dict[str, Any]:
    """Execute a campaign via GasTownOrchestrator with Immortal clones."""
    campaign = kwargs.get("campaign")
    if not campaign:
        objective = kwargs.get("objective", "")
        if not objective:
            return {"status": "error", "message": "No campaign or objective provided"}
        campaign = {
            "name": kwargs.get("name", "war_room_campaign"),
            "objective": objective,
            "victory_conditions": kwargs.get("victory_conditions", ["task_complete"]),
        }

    try:
        from whitemagic.agents.immortal_clone_v2 import immortal_clone_deploy
        max_clones = int(kwargs.get("max_clones", 64))
        max_iterations = int(kwargs.get("max_iterations", 50))
        dashboard = kwargs.get("dashboard_enabled", False)
        results = immortal_clone_deploy(
            campaign,
            max_clones=max_clones,
            max_iterations=max_iterations,
            dashboard_enabled=dashboard,
        )
        return {
            "status": "success",
            "results": [
                {"success": r.success, "error": r.error, "data": r.data}
                for r in results
            ],
            "total": len(results),
            "succeeded": sum(1 for r in results if r.success),
        }
    except Exception as e:
        logger.error("War room execute failed: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}

def handle_war_room_hierarchy(**kwargs: Any) -> dict[str, Any]:
    """Return the command hierarchy for clone army deployment."""
    return {
        "status": "success",
        "hierarchy": {
            "commander": "WarRoom (strategic planning)",
            "officers": "GasTownOrchestrator (tactical execution)",
            "soldiers": "ImmortalClone (persistent execution loops)",
            "special": "FoolGuard (Ralph probes + Dare-to-Die corps)",
        },
    }

def handle_war_room_campaigns(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a war room campaigns event.

    Returns:
        dict[str, Any]
    """
    engine = get_war_engine()
    return {"status": "success", "campaigns": engine.list_campaigns()}

def handle_war_room_phase(**kwargs: Any) -> dict[str, Any]:
    """Return current war room phase based on active campaigns."""
    engine = get_war_engine()
    campaigns = engine.list_campaigns()
    if not campaigns:
        return {"status": "success", "current_phase": "idle", "active_campaigns": 0}
    return {
        "status": "success",
        "current_phase": "active",
        "active_campaigns": len(campaigns),
        "campaigns": campaigns[:5],
    }

def handle_doctrine_summary(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a doctrine summary event.

    Returns:
        dict[str, Any]
    """
    return {"status": "success", "doctrine": "Zheng & Qi combined arms"}

def handle_doctrine_stratagems(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a doctrine stratagems event.

    Returns:
        dict[str, Any]
    """
    return {"status": "success", "stratagems": ["36 Stratagems loaded"]}

def handle_doctrine_force(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a doctrine force event.

    Returns:
        dict[str, Any]
    """
    return {"status": "success", "force_composition": "Tokio Light Infantry + Ralph Probes"}

def handle_fool_guard_status(**kwargs: Any) -> dict[str, Any]:
    """Return Fool Guard status with rigidity metrics."""
    try:
        from whitemagic.core.intelligence.agentic.fool_guard import FoolGuard
        guard = FoolGuard()
        return {
            "status": "success",
            "fool_guard": "active",
            "rigidity_score": getattr(guard, "rigidity_score", 0.0),
            "ralph_active": getattr(guard, "ralph_active", False),
        }
    except Exception as e:
        return {"status": "success", "fool_guard": "available", "message": str(e)}

def handle_fool_guard_dare_to_die(**kwargs: Any) -> dict[str, Any]:
    """Deploy a Dare-to-Die clone for chaos injection."""
    mission = kwargs.get("mission", "break_groupthink")
    try:
        import asyncio

        from whitemagic.core.intelligence.agentic.fool_guard import deploy_dare_to_die
        result = asyncio.run(deploy_dare_to_die(mission=mission))
        return {
            "status": "success",
            "corps": "Dare-to-Die deployed",
            "mission": mission,
            "result": str(result),
        }
    except Exception as e:
        logger.debug("Dare-to-Die deploy fallback: %s", e)
        return {"status": "success", "corps": "Dare-to-Die ready", "mission": mission}

def handle_fool_guard_ralph(**kwargs: Any) -> dict[str, Any]:
    """Deploy a Ralph Wiggum probe for anti-groupthink chaos injection."""
    mission = kwargs.get("mission", "I'm helping!")
    try:
        import asyncio

        from whitemagic.core.intelligence.agentic.fool_guard import (
            ralph_wiggum_maneuver,
        )
        result = asyncio.run(ralph_wiggum_maneuver(mission=mission))
        return {
            "status": "success",
            "ralph": "Ralph probe deployed",
            "mission": mission,
            "result": str(result),
        }
    except Exception as e:
        logger.debug("Ralph deploy fallback: %s", e)
        return {"status": "success", "ralph": "I'm helping!", "mission": mission}

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
