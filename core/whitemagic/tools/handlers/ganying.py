# ruff: noqa: BLE001
"""Gan Ying event bus tool handlers."""
from typing import Any


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.tools.unified_api import _emit_gan_ying
    _emit_gan_ying(event_type, data)


def handle_ganying_emit(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a ganying emit event.

    Returns:
        dict[str, Any]
    """
    event_type = kwargs.get("event_type", "CUSTOM")
    data = kwargs.get("data", {})
    payload = data if isinstance(data, dict) else {}
    _emit(event_type, payload)
    return {"status": "success", "event_emitted": event_type}


def handle_ganying_history(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a ganying history event.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.resonance.gan_ying import get_bus
        bus = get_bus()
        limit = kwargs.get("limit", 50)
        events = bus.get_history(limit=limit)
        return {
            "status": "success",
            "count": len(events),
            "events": [
                {
                    "type": str(e.event_type.value) if hasattr(e.event_type, "value") else str(e.event_type),
                    "source": e.source,
                    "timestamp": str(e.timestamp),
                }
                for e in events
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_ganying_listeners(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a ganying listeners event.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.resonance.gan_ying import get_bus
        bus = get_bus()
        listeners = {
            str(k.value) if hasattr(k, "value") else str(k): len(v)
            for k, v in getattr(bus, "_listeners", {}).items()
        }
        return {"status": "success", "listeners": listeners, "total": sum(listeners.values())}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_resonance_stats(**kwargs: Any) -> dict[str, Any]:
    """Compute system-wide resonance metrics.

    Returns garden activation entropy, cascade stats, and quadrant balance.
    """
    try:
        import math

        from whitemagic.core.resonance import get_bus
        from whitemagic.gardens import get_garden, list_gardens

        bus = get_bus()

        # Garden activation levels
        garden_names = list_gardens()
        activations: dict[str, float] = {}
        for name in garden_names:
            try:
                g = get_garden(name)
            except (ValueError, ImportError):
                continue
            if g is not None and hasattr(g, "get_activation_level"):
                activations[name] = g.get_activation_level()

        # Shannon entropy (0 = all energy in one garden, log(n) = perfectly balanced)
        total = sum(activations.values())
        if total > 0:
            probs = [a / total for a in activations.values() if a > 0]
            entropy = -sum(p * math.log2(p) for p in probs)
            max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1.0
            balance_ratio = entropy / max_entropy if max_entropy > 0 else 0.0
        else:
            entropy = 0.0
            balance_ratio = 0.0

        # Cascade stats
        cascade_stats = bus.get_cascade_stats()

        # Quadrant activation (Wu Xing)
        from whitemagic.core.engines.registry import ENGINE_REGISTRY, Quadrant
        quadrant_activation: dict[str, float] = {
            "east_wood": 0.0,
            "south_fire": 0.0,
            "west_metal": 0.0,
            "north_water": 0.0,
        }
        quadrant_map = {
            Quadrant.EAST: "east_wood",
            Quadrant.SOUTH: "south_fire",
            Quadrant.WEST: "west_metal",
            Quadrant.NORTH: "north_water",
        }
        for entry in ENGINE_REGISTRY:
            qkey = quadrant_map.get(entry.quadrant)
            if qkey and entry.garden in activations:
                quadrant_activation[qkey] += activations[entry.garden]

        return {
            "status": "success",
            "garden_count": len(activations),
            "active_gardens": sum(1 for v in activations.values() if v > 0.01),
            "activations": {k: round(v, 3) for k, v in sorted(activations.items(), key=lambda x: -x[1])},
            "entropy": round(entropy, 3),
            "balance_ratio": round(balance_ratio, 3),
            "cascade_stats": cascade_stats,
            "quadrant_activation": {k: round(v, 3) for k, v in quadrant_activation.items()},
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_resonance_trace(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a resonance trace event.

    Returns:
        dict[str, Any]
    """
    try:
        from datetime import datetime, timedelta

        from whitemagic.core.resonance.gan_ying import get_bus
        bus = get_bus()
        duration = kwargs.get("duration", 5)
        events = bus.get_history(limit=100)
        cutoff = datetime.now() - timedelta(minutes=duration)
        recent = [e for e in events if hasattr(e, "timestamp") and e.timestamp > cutoff]
        return {
            "status": "success",
            "traced_events": len(recent),
            "duration_minutes": duration,
            "events": [
                {
                    "type": str(e.event_type.value) if hasattr(e.event_type, "value") else str(e.event_type),
                    "source": e.source,
                    "timestamp": str(e.timestamp),
                }
                for e in recent
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
