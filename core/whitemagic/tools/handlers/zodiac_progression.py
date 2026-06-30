"""MCP handler for Unified Zodiacal Progression status (Bridge 1 — Telemetric Qi)."""

from typing import Any


def handle_zodiac_status(**kwargs: Any) -> dict[str, Any]:
    """Return the current phase of the UnifiedProgressionDaemon."""
    from whitemagic.core.governance.unified_progression import get_progression_daemon

    daemon = get_progression_daemon()
    return {
        "status": "success",
        "running": daemon.running,
        "zodiac_phase": daemon.state.current_phase.value,
        "wu_xing": daemon.state.wu_xing.value,
        "yin_yang": daemon.state.yin_yang.value,
        "cycle_count": daemon.state.cycle_count,
        "total_activations": daemon.state.total_activations,
        "tick_duration_seconds": daemon.tick_duration,
    }


def handle_zodiac_activate(**kwargs: Any) -> dict[str, Any]:
    """Activate a specific zodiac core with context.

    Args:
        core: Zodiac sign name (e.g., "aries", "leo", "pisces")
        context: Optional dict with operation, intention, urgency
    """
    core_name = kwargs.get("core", "").lower()
    if not core_name:
        return {"status": "error", "error": "core parameter required (e.g., 'aries')"}

    context = kwargs.get("context", {})
    if not isinstance(context, dict):
        return {"status": "error", "error": "context must be a dict"}
    context.setdefault("operation", "activate")
    context.setdefault("intention", "alignment")
    context.setdefault("urgency", "normal")

    try:
        from whitemagic.zodiac.zodiac_cores import get_zodiac_cores

        cores = get_zodiac_cores()
        response = cores.activate_core(core_name, context)
        if response is None:
            return {"status": "error", "error": f"Unknown zodiac core: {core_name}"}
        return {
            "status": "success",
            "core": response.core_name,
            "wisdom": response.wisdom,
            "resonance": response.resonance,
            "transformation": response.transformation_applied,
            "processing_result": response.processing_result,
            "timestamp": response.timestamp.isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_zodiac_council(**kwargs: Any) -> dict[str, Any]:
    """Convene the full zodiac council for a decision.

    Args:
        decision: The decision to get perspectives on
    """
    decision = kwargs.get("decision", "")
    if not decision:
        return {"status": "error", "error": "decision parameter required"}

    try:
        from whitemagic.gardens.connection.zodiac_cores import ZodiacCouncil

        council = ZodiacCouncil()
        result = council.convene(decision)
        return {
            "status": "success",
            "decision": result["decision"],
            "council_size": result["council_size"],
            "perspectives": result["perspectives"],
            "timestamp": result["timestamp"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_zodiac_stats(**kwargs: Any) -> dict[str, Any]:
    """Get activation statistics for all zodiac cores."""
    try:
        from whitemagic.zodiac.zodiac_cores import get_zodiac_cores

        cores = get_zodiac_cores()
        return {"status": "success", "stats": cores.get_core_statistics()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
