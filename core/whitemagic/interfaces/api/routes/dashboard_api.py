# ruff: noqa: BLE001
"""Dashboard API - Live data endpoint for the WhiteMagic Dashboard.

Provides:
- System status
- Memory matrix data
- Timeline events
- File tracking stats
- Agentic module status
"""

import time
from datetime import datetime
from typing import Any, cast

from whitemagic.core.ganas.registry import get_all_ganas

try:
    from fastapi import APIRouter, HTTPException
except ImportError as e:
    # pragma: no cover - optional dependency
    raise ImportError(
        "FastAPI is required for whitemagic.interfaces.api.routes.dashboard_api",
    ) from e

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# In-memory mock stats for now - to be replaced by Gan Ying subscription
_GANA_STATS: dict[str, int] = {}



@router.get("/status")
async def get_system_status() -> dict[str, Any]:
    """Get full system status for dashboard."""
    try:
        from whitemagic.integration import get_hub

        hub = get_hub()
        if not hub.activated:
            hub.activate_all()

        return cast("dict[str, Any]", hub.get_status())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data")
async def get_dashboard_data() -> dict[str, Any]:
    """Get complete dashboard visualization data."""
    try:
        from whitemagic.integration import get_hub

        hub = get_hub()
        return cast("dict[str, Any]", hub.get_dashboard_data())
    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory-matrix")
async def get_memory_matrix() -> dict[str, Any]:
    """Get memory matrix stats and recent files."""
    try:
        from whitemagic.core.memory_matrix import (  # type: ignore[import-not-found]
            get_matrix,
            get_seen_registry,
            get_timeline,
        )

        matrix = get_matrix()
        registry = get_seen_registry()
        timeline = get_timeline()

        return {
            "stats": matrix.stats(),
            "recent_files": [
                {
                    "path": e.path.split("/whitemagic/")[-1] if "/whitemagic/" in e.path else e.path,
                    "type": e.file_type,
                    "times_seen": e.times_seen,
                    "last_seen": e.last_seen,
                }
                for e in registry.get_recent(20)
            ],
            "timeline_summary": timeline.stats(),
            "today": matrix.get_today_summary(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agentic")
async def get_agentic_status() -> dict[str, Any]:
    """Get status of all 13 agentic modules."""
    try:
        from whitemagic.core.intelligence.agentic import full_brain_activation

        return {
            "modules": full_brain_activation(),
            "total": 13,
            "description": "Brain upgrade suite - cognitive enhancements",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session")
async def get_session_info() -> dict[str, Any]:
    """Get current session information."""
    try:
        from whitemagic.session import (
            get_session_manifest,  # type: ignore[import-not-found]
        )

        manifest = get_session_manifest()
        if manifest:
            return cast("dict[str, Any]", manifest.to_dict())
        return {"error": "No active session"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate")
async def activate_all_systems() -> dict[str, Any]:
    """Activate the full integration system."""
    try:
        from whitemagic.integration import activate_all

        return cast("dict[str, Any]", activate_all())
    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualization")
async def get_visualization_data() -> dict[str, Any]:
    """Get data formatted for 2D grid visualization."""
    try:
        from whitemagic.core.memory_matrix import get_matrix

        matrix = get_matrix()
        return cast("dict[str, Any]", matrix.export_for_visualization())
    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ganas/activity")
async def get_gana_activity() -> dict[str, list[dict[str, Any]]]:
    """Get activity stats for all 28 Ganas from live PRAT resonance and vitality data."""
    try:
        from whitemagic.tools.gana_vitality import get_vitality_monitor
        from whitemagic.tools.prat_resonance import get_resonance_state

        ganas = get_all_ganas()
        resonance = get_resonance_state()
        vitality = get_vitality_monitor()

        gana_counts = resonance.get_gana_counts()
        reps = vitality.get_all_reputations()

        activity_list = []
        for gana in ganas:
            mansion = gana.mansion
            rep = reps.get(gana.name, {})
            current_invocations = gana_counts.get(gana.name, 0)

            last_call_age = rep.get("last_call_age_secs")
            last_active = None
            if last_call_age is not None:
                last_active = datetime.fromtimestamp(time.time() - last_call_age).isoformat()

            activity_list.append({
                "mansion": f"{mansion.chinese} ({mansion.pinyin})",
                "quadrant": mansion.quadrant.lower(),
                "invocations": current_invocations,
                "avgExecutionMs": round(rep.get("avg_latency_ms", 0), 2),
                "lastActive": last_active or datetime.now().isoformat(),
                "vitality": rep.get("vitality", "unknown"),
                "successRate": round(rep.get("success_rate", 1.0), 3),
            })

        return {"ganas": activity_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
