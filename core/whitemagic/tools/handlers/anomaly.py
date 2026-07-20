"""MCP handlers for Harmony Vector Anomaly Detection."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

def handle_anomaly(**kwargs: Any) -> dict[str, Any]:
    """Unified anomaly handler — routes by action parameter."""
    action = kwargs.get("action", "check")
    dispatch = {
        "check": handle_anomaly_check,
        "history": handle_anomaly_history,
        "status": handle_anomaly_status,
    }
    handler = dispatch.get(action)
    if not handler:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Valid: {sorted(dispatch.keys())}",
        }
    return handler(**kwargs)


def handle_anomaly_check(**kwargs: Any) -> dict[str, Any]:
    """Check for active anomalies on Harmony Vector dimensions.

    Includes STRATA codebase findings (structural issues, dead code, archive drift)
    and thermal anomalies from laptop-optimizer when available.
    """
    from whitemagic.harmony.anomaly_detector import get_anomaly_detector

    detector = get_anomaly_detector()
    alerts = detector.check()

    # STRATA findings are deferred to the homeostatic loop's codebase health sensor
    # (running full STRATA analysis on every anomaly check is too slow)
    strata_anomalies: list[dict[str, Any]] = []
    try:
        from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop

        loop = get_homeostatic_loop()
        stats = loop.get_stats()
        recent = stats.get("recent_actions", [])
        for action in recent:
            if action.get("dimension") == "codebase_health":
                strata_anomalies.append(
                    {
                        "source": "homeostatic_codebase_sensor",
                        "dimension": "codebase_quality",
                        "severity": "warning"
                        if action.get("level") == "correct"
                        else "info",
                        "message": action.get(
                            "action_taken", "Codebase health issue detected"
                        ),
                    }
                )
                break
    except Exception:  # noqa: BLE001
        logger.debug("Ignored Exception in anomaly.py:61")

    # Enrich with thermal anomalies from laptop-optimizer
    thermal_anomalies: list[dict[str, Any]] = []
    try:
        from whitemagic.harmony.physical_metrics import get_physical_metrics_source

        source = get_physical_metrics_source()
        anomaly = source.check_thermal_anomaly()
        if anomaly:
            thermal_anomalies.append(
                {
                    "source": "laptop-optimizer",
                    "dimension": "thermal",
                    "pattern": anomaly.pattern,
                    "current_temp": anomaly.current_temp,
                    "threshold": anomaly.threshold,
                    "message": anomaly.message,
                }
            )
    except Exception:  # noqa: BLE001
        logger.debug("Ignored Exception in anomaly.py:82")

    all_alerts = alerts + strata_anomalies + thermal_anomalies
    return {
        "status": "success",
        "active_alerts": all_alerts,
        "alert_count": len(all_alerts),
        "harmony_alerts": len(alerts),
        "strata_alerts": len(strata_anomalies),
        "strata_note": "STRATA analysis deferred to homeostatic loop (periodic codebase health sensor)",
        "thermal_alerts": len(thermal_anomalies),
    }


def handle_anomaly_history(**kwargs: Any) -> dict[str, Any]:
    """Get recent anomaly alert history."""
    from whitemagic.harmony.anomaly_detector import get_anomaly_detector

    limit = int(kwargs.get("limit", 20))
    detector = get_anomaly_detector()
    return {
        "status": "success",
        "alerts": detector.recent_alerts(limit=limit),
    }


def handle_anomaly_status(**kwargs: Any) -> dict[str, Any]:
    """Get anomaly detector status and per-dimension statistics."""
    from whitemagic.harmony.anomaly_detector import get_anomaly_detector

    detector = get_anomaly_detector()
    return {"status": "success", **detector.status()}
