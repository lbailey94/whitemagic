"""MCP handlers for Harmony Vector Anomaly Detection."""

from typing import Any


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
        return {"status": "error", "message": f"Unknown action '{action}'. Valid: {sorted(dispatch.keys())}"}
    return handler(**kwargs)


def handle_anomaly_check(**kwargs: Any) -> dict[str, Any]:
    """Check for active anomalies on Harmony Vector dimensions.

    Includes STRATA codebase findings (structural_stub, dead_code, archive_drift)
    and thermal anomalies from laptop-optimizer when available.
    """
    from whitemagic.harmony.anomaly_detector import get_anomaly_detector
    detector = get_anomaly_detector()
    alerts = detector.check()

    # Enrich with STRATA codebase findings
    strata_anomalies: list[dict[str, Any]] = []
    try:
        from whitemagic.tools.strata import Strata, FindingSeverity
        from pathlib import Path
        core_path = str(Path(__file__).parent.parent.parent.parent.parent)
        if Path(core_path, "AGENTS.md").exists():
            strata = Strata(core_path)
            findings = strata.analyze(incremental=True)
            for f in findings:
                if f.severity in (FindingSeverity.ERROR, FindingSeverity.WARNING):
                    strata_anomalies.append({
                        "source": "strata",
                        "dimension": "codebase_quality",
                        "severity": f.severity.value,
                        "category": f.category,
                        "file": f.file,
                        "line": f.line,
                        "message": f.message,
                        "suggestion": f.suggestion,
                    })
    except Exception:
        pass

    # Enrich with thermal anomalies from laptop-optimizer
    thermal_anomalies: list[dict[str, Any]] = []
    try:
        from whitemagic.harmony.physical_metrics import get_physical_metrics_source
        source = get_physical_metrics_source()
        anomaly = source.check_thermal_anomaly()
        if anomaly:
            thermal_anomalies.append({
                "source": "laptop-optimizer",
                "dimension": "thermal",
                "pattern": anomaly.pattern,
                "current_temp": anomaly.current_temp,
                "threshold": anomaly.threshold,
                "message": anomaly.message,
            })
    except Exception:
        pass

    all_alerts = alerts + strata_anomalies + thermal_anomalies
    return {
        "status": "success",
        "active_alerts": all_alerts,
        "alert_count": len(all_alerts),
        "harmony_alerts": len(alerts),
        "strata_alerts": len(strata_anomalies),
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
