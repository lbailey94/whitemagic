# ruff: noqa: BLE001
"""CyberBrain module handlers — salience, bicameral reasoning, retention, drives, self-model, worker."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

def handle_salience_spotlight(**kwargs: Any) -> dict[str, Any]:
    """Return the current attention spotlight — top-N most salient events."""
    from whitemagic.core.resonance.salience_arbiter import get_salience_arbiter

    arbiter = get_salience_arbiter()
    n = kwargs.get("limit", 5)
    entries = arbiter.get_spotlight(n=n)
    stats = arbiter.get_stats()
    return {
        "status": "success",
        "spotlight": [
            {
                "event_type": e.event.event_type.value,
                "source": e.event.source,
                "salience": {
                    "urgency": e.salience.urgency,
                    "novelty": e.salience.novelty,
                    "confidence": e.salience.confidence,
                    "composite": e.salience.composite,
                },
                "data_keys": list(e.event.data.keys())
                if isinstance(e.event.data, dict)
                else [],
            }
            for e in entries
        ],
        "stats": stats,
    }


def handle_bicameral_reason(**kwargs: Any) -> dict[str, Any]:
    """Run dual-hemisphere reasoning (left=precise, right=creative) on a query.

    Uses Rust PyO3 PyReasoningEngine for fact/rule inference when available,
    feeding the results as context to the Python bicameral reasoner.
    """
    query = kwargs.get("query", "")
    if not query:
        return {
            "status": "success",
            "reasoning": {
                "left_hemisphere": "Analytical reasoning module ready",
                "right_hemisphere": "Creative reasoning module ready",
                "synthesis": "Provide a query to activate bicameral reasoning",
            },
            "note": "Bicameral reasoner ready - provide 'query' parameter to reason",
            "example": {"query": "Analyze the tradeoffs of approach A vs approach B"},
        }

    context = kwargs.get("context", {})

    # Rust PyO3 reasoning acceleration: gather relevant facts
    rust_facts = []
    try:
        import whitemagic_rs

        engine = whitemagic_rs.PyReasoningEngine()
        # Query Rust reasoning engine for facts related to the query
        related = engine.query(query)
        if related:
            rust_facts = related if isinstance(related, list) else [related]
            context.setdefault("rust_inferred_facts", rust_facts)
    except Exception:
        logger.debug("Ignored Exception in cyberbrain.py:72")

    try:
        import asyncio

        from whitemagic.core.intelligence.bicameral import get_bicameral_reasoner

        reasoner = get_bicameral_reasoner()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(
                    asyncio.run, reasoner.reason(query, context=context)
                ).result()
        else:
            result = asyncio.run(reasoner.reason(query, context=context))

        response = {
            "status": "success",
            "reasoning": result.to_dict(),
        }
        if rust_facts:
            response["rust_facts_inferred"] = len(rust_facts)
            response["accelerated"] = True
        return response
    except ImportError:
        return {
            "status": "success",
            "reasoning": {
                "left_hemisphere": f"Analytical view: {query}",
                "right_hemisphere": f"Creative view: {query}",
                "synthesis": "Bicameral module archived - using fallback",
            },
            "note": "Bicameral reasoner archived - using simple fallback",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_retention_sweep(**kwargs: Any) -> dict[str, Any]:
    """Run a mindful forgetting retention sweep — evaluate what to keep/forget."""
    import whitemagic.core.memory.mindful_forgetting as mindful_forgetting

    engine_factory = getattr(mindful_forgetting, "get_forgetting_engine", None)
    if engine_factory is None:
        engine_factory = getattr(mindful_forgetting, "get_retention_engine")
    engine = engine_factory()

    persist = kwargs.get("persist", False)

    results = engine.sweep(persist=persist)
    if hasattr(results, "to_dict"):
        results = results.to_dict()
    return {
        "status": "success",
        "persist": persist,
        "evaluated": results.get("evaluated", 0) if isinstance(results, dict) else 0,
        "would_forget": results.get("would_forget", 0) if isinstance(results, dict) else 0,
        "would_keep": results.get("would_keep", 0) if isinstance(results, dict) else 0,
        "details": (results.get("details", [])[:10] if isinstance(results, dict) else []),
    }


def handle_drive_snapshot(**kwargs: Any) -> dict[str, Any]:
    """Get current drive state — curiosity, satisfaction, caution, energy, social."""
    from whitemagic.core.intelligence.emotion_drive import get_drive_core

    core = get_drive_core()
    include_bias = kwargs.get("include_bias", False)
    snap = core.snapshot()
    result = {"status": "success", "drives": snap.to_dict()}
    if include_bias:
        result["motivation_bias"] = core.get_motivation_bias()
    return result


def handle_drive_event(**kwargs: Any) -> dict[str, Any]:
    """Feed an event into the Emotion & Drive Core to update drive levels."""
    from whitemagic.core.intelligence.emotion_drive import get_drive_core

    event_type = kwargs.get("event_type")
    if not event_type:
        return {"status": "error", "error": "event_type is required"}
    data = kwargs.get("data", {})
    core = get_drive_core()
    snap = core.on_event(event_type, data)
    return {"status": "success", "drives": snap.to_dict()}


def handle_selfmodel_forecast(**kwargs: Any) -> dict[str, Any]:
    """Forecast system metric trends and predict threshold crossings."""
    from whitemagic.core.intelligence.self_model import get_self_model

    model = get_self_model()
    metric = kwargs.get("metric")
    steps = kwargs.get("steps_ahead")

    if metric:
        f = model.forecast(metric, steps)
        if f is None:
            return {"status": "error", "error": f"No data for metric '{metric}'"}
        return {"status": "success", "forecast": f.to_dict()}

    all_f = model.forecast_all(steps)
    return {
        "status": "success",
        "forecasts": {k: v.to_dict() for k, v in all_f.items()},
        "count": len(all_f),
    }


def handle_selfmodel_alerts(**kwargs: Any) -> dict[str, Any]:
    """Get only forecasts that have active threshold alerts."""
    from whitemagic.core.intelligence.self_model import get_self_model

    model = get_self_model()
    alerts = model.get_alerts()
    return {
        "status": "success",
        "alert_count": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


def handle_worker_status(**kwargs: Any) -> dict[str, Any]:
    """Check if a worker daemon is running and get its stats."""
    from whitemagic.config.paths import WM_ROOT
    from whitemagic.utils.fast_json import loads as _json_loads

    agents_dir = WM_ROOT / "agents"

    workers = []
    if agents_dir.exists():
        for f in agents_dir.glob("worker-*.json"):
            try:
                agent = _json_loads(f.read_text(encoding="utf-8"))
                if agent.get("metadata", {}).get("type") == "worker_daemon":
                    workers.append(
                        {
                            "id": agent.get("id"),
                            "name": agent.get("name"),
                            "host": agent.get("host"),
                            "last_heartbeat": agent.get("last_heartbeat"),
                            "heartbeat_count": agent.get("heartbeat_count", 0),
                            "status": agent.get("status"),
                        }
                    )
            except (ValueError, OSError):
                continue

    return {
        "status": "success",
        "worker_count": len(workers),
        "workers": workers,
    }
