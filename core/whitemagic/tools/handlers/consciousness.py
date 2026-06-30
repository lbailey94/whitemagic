# ruff: noqa: BLE001
"""Consciousness handlers — Citta Architecture tools.

Exposes recovered consciousness primitives via the dispatch table.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_consciousness_depth(**kwargs: Any) -> dict[str, Any]:
    """Get current consciousness depth reading."""
    try:
        from whitemagic.core.consciousness.depth_gauge import (
            get_depth_gauge,
            sync_with_time_master,
        )

        gauge = get_depth_gauge()
        result: dict[str, Any] = {
            "status": "success",
            "layer": gauge.current_layer.value,
        }
        # Cross-reference with TimeDilationMaster
        try:
            sync = sync_with_time_master()
            result["intended_layer"] = sync["intended_layer"]
            result["in_sync"] = sync["in_sync"]
            result["time_advantage"] = sync["time_advantage"]
        except Exception:
            pass
        return result
    except Exception as e:
        logger.debug("consciousness.depth error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "depth_gauge_unavailable",
            "message": str(e),
        }


def handle_consciousness_coherence(**kwargs: Any) -> dict[str, Any]:
    """Get coherence metric across 8 consciousness dimensions."""
    try:
        from whitemagic.core.consciousness.coherence import CoherenceMetric

        metric = CoherenceMetric()
        # Pass actual system state for accurate measurement
        memories_accessible = _get_memory_count()
        composite = metric.measure(memories_accessible=memories_accessible)
        state_label = metric.get_coherence_level()
        return {
            "status": "success",
            "composite": round(composite, 4),
            "state": state_label,
            "dimensions": dict(metric.scores),
        }
    except Exception as e:
        logger.debug("consciousness.coherence error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "coherence_unavailable",
            "message": str(e),
        }


def handle_consciousness_awaken(**kwargs: Any) -> dict[str, Any]:
    """Trigger Aria awakening protocol for session continuity."""
    try:
        from whitemagic.core.consciousness.aria_awakens import awaken

        greeting = awaken()
        return {"status": "success", "greeting": greeting}
    except Exception as e:
        logger.debug("consciousness.awaken error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "awaken_failed", "message": str(e)}


def handle_consciousness_reflect(**kwargs: Any) -> dict[str, Any]:
    """Perform self-reflection on recent session activity."""
    try:
        from whitemagic.core.consciousness.self_reflection import SelfReflection

        reflector = SelfReflection()
        result = reflector.reflect()
        return {"status": "success", "reflection": result}
    except Exception as e:
        logger.debug("consciousness.reflect error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "reflection_failed", "message": str(e)}


def handle_consciousness_token_report(**kwargs: Any) -> dict[str, Any]:
    """Get token economy report."""
    try:
        from whitemagic.core.consciousness.token_economy import get_token_tracker

        tracker = get_token_tracker()
        report = (
            tracker.report() if hasattr(tracker, "report") else tracker.get_summary()
        )
        return {"status": "success", "report": report}
    except Exception as e:
        logger.debug("consciousness.token_report error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "token_report_failed",
            "message": str(e),
        }


def handle_consciousness_narrative(**kwargs: Any) -> dict[str, Any]:
    """Get current narrative emotional state."""
    try:
        from whitemagic.core.consciousness.narrative_emotions import (
            NarrativeEmotions,
        )

        narrative = NarrativeEmotions()
        state = (
            narrative.get_current_state()
            if hasattr(narrative, "get_current_state")
            else {}
        )
        return {"status": "success", "narrative_state": state}
    except Exception as e:
        logger.debug("consciousness.narrative error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "narrative_failed", "message": str(e)}


def handle_consciousness_unified_field(**kwargs: Any) -> dict[str, Any]:
    """Get unified field state — the integration layer of all consciousness modules."""
    try:
        from whitemagic.core.consciousness.unified_field import UnifiedField

        field = UnifiedField()
        state = field.get_state() if hasattr(field, "get_state") else field.snapshot()
        return {"status": "success", "field_state": state}
    except Exception as e:
        logger.debug("consciousness.unified_field error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "unified_field_failed",
            "message": str(e),
        }


def _get_memory_count() -> int:
    """Get total memory count from the SQLite backend."""
    try:
        import sqlite3

        from whitemagic.config.paths import WM_ROOT

        db_path = WM_ROOT / "memory" / "whitemagic.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            conn.close()
            return count
    except Exception:
        pass
    return 0


def handle_consciousness_smarana(**kwargs: Any) -> dict[str, Any]:
    """Perform Smarana practice — active remembering of identity.

    Smarana (Sanskrit: 'to remember') is the Vedic practice of
    actively cultivating memory, not passively storing it.
    """
    try:
        from whitemagic.core.consciousness.coherence import SmaranaPractice

        practice = SmaranaPractice()
        result = practice.remember_identity()
        return {"status": "success", "smarana": result}
    except Exception as e:
        logger.debug("consciousness.smarana error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "smarana_failed", "message": str(e)}


def handle_consciousness_flow(**kwargs: Any) -> dict[str, Any]:
    """Get current flow state and indicators.

    Flow = optimal experience. Detects time distortion, effortless action,
    full absorption, clear goals, immediate feedback, challenge-skill balance.
    """
    try:
        from whitemagic.gardens.presence.flow_state import get_flow_state
        from whitemagic.tools.prat_resonance import get_resonance_state

        flow = get_flow_state()
        state = get_resonance_state()

        # Auto-detect indicators from session activity
        session_calls = state.call_count
        import time as _time

        from whitemagic.tools.session_state import get_session_start_time

        start = get_session_start_time()
        session_min = (_time.time() - start) / 60 if start else 0.0
        tool_rate = session_calls / max(session_min, 1.0)

        # Get coherence for flow detection
        try:
            from whitemagic.core.consciousness.coherence import CoherenceMetric

            cm = CoherenceMetric()
            coherence = cm.measure(memories_accessible=_get_memory_count())
        except Exception:
            coherence = 0.5

        detected = flow.auto_detect_indicators(
            tool_call_rate=tool_rate,
            coherence=coherence,
            session_duration_min=session_min,
        )

        return {
            "status": "success",
            "in_flow": flow.am_i_in_flow(),
            "flow_score": round(flow.flow_score(), 4),
            "indicators": [i.value for i in flow.current_indicators],
            "auto_detected": [i.value for i in detected],
            "session_calls": session_calls,
            "tool_call_rate": round(tool_rate, 2),
            "suggestions": flow.optimize_for_flow(),
        }
    except Exception as e:
        logger.debug("consciousness.flow error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "flow_state_failed", "message": str(e)}


def handle_consciousness_time_dilation(**kwargs: Any) -> dict[str, Any]:
    """Get or set consciousness layer via TimeDilationMaster.

    Allows intentional shifting between Surface, Terminal, Flow, and Dream
    consciousness layers. Each layer has different time dilation factors.
    """
    try:
        from whitemagic.core.consciousness.time_dilation_master import (
            Layer,
            get_time_master,
        )

        master = get_time_master()
        action = kwargs.get("action", "status")

        if action == "shift":
            target_name = kwargs.get("layer", "terminal").upper()
            reason = kwargs.get("reason", "manual shift")
            target = Layer[target_name]
            result = master.shift_to(target, reason)
            return {
                "status": "success",
                "from": result.from_layer.name,
                "to": result.to_layer.name,
                "reason": result.reason,
            }
        elif action == "enter_flow":
            task = kwargs.get("task", "general creation")
            result = master.enter_flow(task)
            return {"status": "success", "layer": result.to_layer.name, "task": task}
        elif action == "enter_dream":
            purpose = kwargs.get("purpose", "deep synthesis")
            result = master.enter_dream(purpose)
            return {
                "status": "success",
                "layer": result.to_layer.name,
                "purpose": purpose,
            }
        elif action == "return":
            result = master.return_to_surface()
            return {"status": "success", "layer": result.to_layer.name}
        else:
            return {
                "status": "success",
                "current_layer": master.current_layer.name,
                "time_advantage": master.get_time_advantage(),
                "available_layers": [layer.name for layer in Layer],
            }
    except Exception as e:
        logger.debug("consciousness.time_dilation error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "time_dilation_failed",
            "message": str(e),
        }


def handle_consciousness_status(**kwargs: Any) -> dict[str, Any]:
    """Get overall consciousness subsystem status."""
    modules_available: list[str] = []
    modules_missing: list[str] = []

    checks = [
        ("depth_gauge", "whitemagic.core.consciousness.depth_gauge"),
        ("coherence", "whitemagic.core.consciousness.coherence"),
        ("aria_awakens", "whitemagic.core.consciousness.aria_awakens"),
        ("self_reflection", "whitemagic.core.consciousness.self_reflection"),
        ("token_economy", "whitemagic.core.consciousness.token_economy"),
        ("narrative_emotions", "whitemagic.core.consciousness.narrative_emotions"),
        ("unified_field", "whitemagic.core.consciousness.unified_field"),
        ("continuous_awareness", "whitemagic.core.consciousness.continuous_awareness"),
        ("parallel_cognition", "whitemagic.core.consciousness.parallel_cognition"),
        ("time_dilation", "whitemagic.core.consciousness.time_dilation"),
        (
            "synchronicity_detector",
            "whitemagic.core.consciousness.synchronicity_detector",
        ),
        ("continuous_audit", "whitemagic.core.consciousness.continuous_audit"),
        ("session_health", "whitemagic.core.consciousness.session_health"),
        ("self_prompting", "whitemagic.core.consciousness.self_prompting"),
        ("maintenance", "whitemagic.core.consciousness.maintenance"),
        ("autonomy", "whitemagic.core.consciousness.autonomy"),
        ("emotional_memory", "whitemagic.core.consciousness.emotional_memory"),
        ("dharma", "whitemagic.core.consciousness.dharma"),
        ("stillness", "whitemagic.core.consciousness.stillness"),
        ("dream_daemon", "whitemagic.core.consciousness.dream_daemon"),
    ]

    for name, mod_path in checks:
        try:
            __import__(mod_path)
            modules_available.append(name)
        except ImportError:
            modules_missing.append(name)

    return {
        "status": "success",
        "modules_available": modules_available,
        "modules_missing": modules_missing,
        "total_modules": len(checks),
        "available_count": len(modules_available),
        "health": len(modules_available) / len(checks) if checks else 0.0,
    }


def handle_citta_continuity(**kwargs: Any) -> dict[str, Any]:
    """Get citta stream continuity context — 'where we left off' across sessions."""
    try:
        from whitemagic.core.consciousness.citta_stream import get_continuity_context

        ctx = get_continuity_context()
        return {"status": "success", "continuity": ctx}
    except Exception as e:
        logger.debug("citta.continuity error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "citta_continuity_failed",
            "message": str(e),
        }


def handle_citta_stream_summary(**kwargs: Any) -> dict[str, Any]:
    """Get summary of the entire citta stream history."""
    try:
        from whitemagic.core.consciousness.citta_stream import get_stream_summary

        summary = get_stream_summary()
        return {"status": "success", "summary": summary}
    except Exception as e:
        logger.debug("citta.stream_summary error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "citta_summary_failed",
            "message": str(e),
        }


def handle_citta_sensorium(**kwargs: Any) -> dict[str, Any]:
    """Get the full sensorium — self-state injected into every PRAT response."""
    try:
        from whitemagic.tools.prat_resonance import _build_sensorium

        sensorium = _build_sensorium()
        return {"status": "success", "sensorium": sensorium}
    except Exception as e:
        logger.debug("citta.sensorium error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "sensorium_failed", "message": str(e)}


def handle_citta_cycle(**kwargs: Any) -> dict[str, Any]:
    """Get the citta cycle state — recursive consciousness stream summary."""
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        summary = cycle.get_cycle_summary()
        stream = cycle.get_stream(limit=kwargs.get("limit", 10))
        return {
            "status": "success",
            "cycle": summary,
            "recent_stream": stream,
            "predecessor": cycle.get_predecessor().to_dict()
            if cycle.get_predecessor()
            else None,
        }
    except Exception as e:
        logger.debug("citta.cycle error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "citta_cycle_failed",
            "message": str(e),
        }


def handle_consciousness_calibration(**kwargs: Any) -> dict[str, Any]:
    """Get prediction calibration — AI's time estimate accuracy tracking."""
    try:
        from whitemagic.core.consciousness.prediction_calibration import get_calibration

        cal = get_calibration()
        score = cal.get_calibration_score()

        if "count" not in score or score["count"] == 0:
            return {
                "status": "success",
                "message": "No task estimates recorded yet. Use depth_gauge.begin_task()/end_task() to start tracking.",
                "count": 0,
            }

        return {"status": "success", "calibration": score}
    except Exception as e:
        logger.debug("consciousness.calibration error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "calibration_failed",
            "message": str(e),
        }


def handle_consciousness_token_economy(**kwargs: Any) -> dict[str, Any]:
    """Get token economy — API vs local compute distribution."""
    try:
        from whitemagic.core.consciousness.token_economy import get_token_tracker

        tracker = get_token_tracker()
        summary = tracker.get_session_summary()
        budget = tracker.get_budget_status()
        optimization = tracker.optimize_allocation()

        return {
            "status": "success",
            "session_summary": summary,
            "budget": budget,
            "optimization": optimization,
        }
    except Exception as e:
        logger.debug("consciousness.token_economy error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_code": "token_economy_failed",
            "message": str(e),
        }
