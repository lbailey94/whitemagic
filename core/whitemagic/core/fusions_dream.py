# ruff: noqa: BLE001
"""Dream Scheduling Fusion — Self-Model Forecasts → Dream Scheduling.

Proactive dreaming based on energy forecasts from the Self-Model subsystem.
Extracted from fusions.py for better separation of concerns.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def check_proactive_dream() -> dict[str, Any]:
    """Check Self-Model energy forecast and trigger proactive dreaming
    if an energy trough is predicted.

    Instead of waiting for idle time, this allows the system to
    pre-emptively enter a dream phase when the Self-Model predicts
    energy will drop below the warning threshold.

    Returns:
        Dict with forecast info and whether dreaming was triggered.
    """
    try:
        from whitemagic.core.intelligence.self_model import get_self_model

        model = get_self_model()
        forecast = model.forecast("energy")

        if forecast is None:
            return {"triggered": False, "reason": "insufficient energy data"}

        result: dict[str, Any] = {
            "energy_current": round(forecast.current, 4),
            "energy_predicted": round(forecast.predicted, 4),
            "energy_trend": forecast.trend,
            "energy_slope": round(forecast.slope, 6),
        }

        # Trigger proactive dreaming if energy is falling and will hit warning
        should_dream = (
            forecast.trend == "falling"
            and forecast.alert is not None
            and forecast.threshold_eta is not None
            and forecast.threshold_eta <= 15  # within 15 steps
        )

        if should_dream:
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                from whitemagic.core.fusions_event_bridge import emit_fusion_event

                dc = get_dream_cycle()

                if not dc._dreaming and dc._running:
                    # Force a consolidation phase (most valuable when energy is low)
                    dc._dreaming = True
                    logger.info(
                        "🔮 Proactive dream triggered: energy %.3f → %.3f "
                        "(predicted trough in ~%d steps)",
                        forecast.current,
                        forecast.predicted,
                        forecast.threshold_eta,
                    )
                    result["triggered"] = True
                    result["reason"] = (
                        f"Energy predicted to drop to {forecast.predicted:.3f} "
                        f"in ~{forecast.threshold_eta} steps"
                    )
                    result["dream_phase"] = "proactive_consolidation"

                    # Emit event
                    emit_fusion_event(
                        "PROACTIVE_DREAM",
                        {
                            "energy_current": forecast.current,
                            "energy_predicted": forecast.predicted,
                            "threshold_eta": forecast.threshold_eta,
                        },
                    )
                else:
                    result["triggered"] = False
                    result["reason"] = "already dreaming or dream cycle not running"
            except Exception as e:
                result["triggered"] = False
                result["reason"] = f"dream cycle error: {e}"
        else:
            result["triggered"] = False
            result["reason"] = "energy forecast within safe range"

        return result

    except Exception as e:
        logger.error("Proactive dream check failed: %s", e, exc_info=True)
        return {"triggered": False, "reason": f"error: {e}"}
