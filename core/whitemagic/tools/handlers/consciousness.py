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
        from whitemagic.core.consciousness.depth_gauge import get_depth_gauge

        gauge = get_depth_gauge()
        reading = gauge.get_current_reading()
        return {
            "status": "success",
            "reading": reading.to_dict() if reading else None,
            "layer": reading.layer.value if reading else "unknown",
        }
    except Exception as e:
        logger.debug("consciousness.depth error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "depth_gauge_unavailable", "message": str(e)}


def handle_consciousness_coherence(**kwargs: Any) -> dict[str, Any]:
    """Get coherence metric across 8 consciousness dimensions."""
    try:
        from whitemagic.core.consciousness.coherence import CoherenceMetric

        metric = CoherenceMetric()
        scores = metric.measure()
        return {
            "status": "success",
            "scores": scores,
            "composite": metric.composite_score(scores) if hasattr(metric, "composite_score") else None,
            "state": metric.classify(scores) if hasattr(metric, "classify") else "unknown",
        }
    except Exception as e:
        logger.debug("consciousness.coherence error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "coherence_unavailable", "message": str(e)}


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
        report = tracker.report() if hasattr(tracker, "report") else tracker.get_summary()
        return {"status": "success", "report": report}
    except Exception as e:
        logger.debug("consciousness.token_report error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "token_report_failed", "message": str(e)}


def handle_consciousness_narrative(**kwargs: Any) -> dict[str, Any]:
    """Get current narrative emotional state."""
    try:
        from whitemagic.core.consciousness.narrative_emotions import (
            NarrativeEmotions,
        )

        narrative = NarrativeEmotions()
        state = narrative.get_current_state() if hasattr(narrative, "get_current_state") else {}
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
        return {"status": "error", "error_code": "unified_field_failed", "message": str(e)}


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
        ("synchronicity_detector", "whitemagic.core.consciousness.synchronicity_detector"),
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
        return {"status": "error", "error_code": "citta_continuity_failed", "message": str(e)}


def handle_citta_stream_summary(**kwargs: Any) -> dict[str, Any]:
    """Get summary of the entire citta stream history."""
    try:
        from whitemagic.core.consciousness.citta_stream import get_stream_summary

        summary = get_stream_summary()
        return {"status": "success", "summary": summary}
    except Exception as e:
        logger.debug("citta.stream_summary error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "citta_summary_failed", "message": str(e)}


def handle_citta_sensorium(**kwargs: Any) -> dict[str, Any]:
    """Get the full sensorium — self-state injected into every PRAT response."""
    try:
        from whitemagic.tools.prat_resonance import _build_sensorium

        sensorium = _build_sensorium()
        return {"status": "success", "sensorium": sensorium}
    except Exception as e:
        logger.debug("citta.sensorium error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "sensorium_failed", "message": str(e)}
