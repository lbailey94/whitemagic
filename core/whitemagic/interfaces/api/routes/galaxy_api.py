"""Galaxy API — Holographic memory visualization endpoints.

Connects to the real GalaxyManager and returns actual memory nodes
with holographic coordinates from the active galaxy.
"""

import os
from typing import Any

from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

try:
    from fastapi import APIRouter, Body, Header, HTTPException, Request
    router = APIRouter(prefix="/galaxy", tags=["galaxy"])
except ImportError:  # pragma: no cover - optional dependency
    APIRouter = None  # type: ignore[misc,assignment]
    Body = None  # type: ignore[misc,assignment]
    Header = None  # type: ignore[misc,assignment]
    HTTPException = None  # type: ignore[misc,assignment]
    Request = None  # type: ignore[misc,assignment]
    router = None  # type: ignore[assignment]

# Demo galaxy nodes (matches InteractiveGalaxySphere local mode)
_DEMO_NODES: list[dict[str, Any]] = [
    {"id": "1", "label": "Memory Core", "x": 0.2, "y": 0.1, "z": 0.3, "w": 0.5, "v": 0.2, "color": "#fbbf24", "size": 3, "zone": "core", "importance": 0.9, "distance": 0.3, "access_count": 150},
    {"id": "2", "label": "Wisdom Node", "x": -0.3, "y": 0.4, "z": 0.2, "w": 0.3, "v": 0.6, "color": "#22c55e", "size": 2, "zone": "active", "importance": 0.7, "distance": 0.5, "access_count": 80},
    {"id": "3", "label": "Truth Cluster", "x": 0.5, "y": -0.2, "z": -0.4, "w": 0.2, "v": 0.8, "color": "#3b82f6", "size": 2.5, "zone": "architecture", "importance": 0.8, "distance": 0.7, "access_count": 120},
    {"id": "4", "label": "Mystery Ring", "x": -0.6, "y": -0.3, "z": 0.5, "w": 0.7, "v": 0.3, "color": "#a855f7", "size": 1.5, "zone": "research", "importance": 0.5, "distance": 1.0, "access_count": 40},
    {"id": "5", "label": "Outer Echo", "x": 0.8, "y": 0.6, "z": -0.2, "w": 0.1, "v": 0.9, "color": "#6b7280", "size": 1, "zone": "outer_rim", "importance": 0.3, "distance": 1.5, "access_count": 10},
]

_DEMO_EDGES: list[dict[str, Any]] = [
    {"source": "1", "target": "2", "strength": 0.8},
    {"source": "1", "target": "3", "strength": 0.6},
    {"source": "2", "target": "4", "strength": 0.4},
]

_ZONE_COLORS: dict[str, str] = {
    "core": "#fbbf24",
    "active": "#22c55e",
    "architecture": "#3b82f6",
    "research": "#a855f7",
    "outer_rim": "#6b7280",
}


def _memory_type_to_zone(mem_type: str | None) -> str:
    """Map memory type to galaxy zone."""
    if not mem_type:
        return "active"
    mt = mem_type.upper()
    if mt in ("LONG_TERM", "CORE"):
        return "core"
    if mt in ("SHORT_TERM", "EPHEMERAL"):
        return "active"
    if mt in ("ARCHITECTURAL", "SYSTEM"):
        return "architecture"
    if mt in ("RESEARCH", "EXPERIMENTAL"):
        return "research"
    if mt in ("DREAM", "EDGE"):
        return "outer_rim"
    return "active"


def _build_nodes_from_galaxy(limit: int = 500) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Query the active galaxy for real memory nodes and edges."""
    try:
        gm = get_galaxy_manager()
        active = gm.get_active()
        um = gm._get_memory(active.name)
    except Exception:
        return [], []

    memories: list[Any] = []
    try:
        for page in um.backend.list_all_paginated(batch_size=500):
            memories.extend(page)
            if len(memories) >= limit:
                break
    except Exception:
        pass

    if not memories:
        return [], []

    coords_map: dict[str, tuple] = {}
    try:
        coords_map = um.backend.get_all_coords()
    except Exception:
        pass

    nodes: list[dict[str, Any]] = []
    for mem in memories[:limit]:
        zone = _memory_type_to_zone(
            mem.memory_type.name if hasattr(mem.memory_type, "name") else str(mem.memory_type)
        )
        coords = coords_map.get(mem.id)
        if coords:
            x, y, z, w = coords[0], coords[1], coords[2], coords[3]
            v = coords[4] if len(coords) > 4 else 0.5
        else:
            h = hash(mem.id) & 0x7FFFFFFF
            x = ((h % 1000) / 1000) * 2 - 1
            y = (((h // 1000) % 1000) / 1000) * 2 - 1
            z = (((h // 1000000) % 1000) / 1000) * 2 - 1
            w = 0.5
            v = 0.5

        nodes.append({
            "id": mem.id,
            "label": mem.title or mem.id[:8],
            "content": mem.content if len(mem.content) < 500 else mem.content[:500] + "...",
            "x": round(x, 4),
            "y": round(y, 4),
            "z": round(z, 4),
            "w": round(w, 4),
            "v": round(v, 4),
            "color": _ZONE_COLORS.get(zone, "#22c55e"),
            "size": max(0.5, min(3.0, (mem.importance or 0.5) * 3)),
            "zone": zone,
            "importance": round(mem.importance or 0.5, 2),
            "distance": round(mem.galactic_distance or 0.0, 3),
            "access_count": mem.access_count or 0,
        })

    edges: list[dict[str, Any]] = []
    try:
        with um.backend.pool.connection() as conn:
            cursor = conn.execute(
                "SELECT source_id, target_id, strength FROM associations LIMIT ?",
                (limit * 2,),
            )
            for row in cursor:
                edges.append({"source": row[0], "target": row[1], "strength": round(row[2] or 0.5, 2)})
    except Exception:
        pass

    return nodes, edges


def _require_api_key(x_api_key: str | None) -> str | None:
    """Validate API key if WM_GALAXY_REQUIRE_KEY is set."""
    require = os.environ.get("WM_GALAXY_REQUIRE_KEY", "").lower() in ("1", "true", "yes")
    if not require:
        return None  # open
    if not x_api_key:
        raise Exception("401: X-API-Key header required")
    # TODO: hash lookup against DB
    if x_api_key.startswith("wm_") and len(x_api_key) >= 20:
        return x_api_key
    raise Exception("403: Invalid API key")


if router is not None:
    @router.get("/nodes")
    async def get_galaxy_nodes(
        request: Request,
        limit: int = 500,
        zone: str | None = None,
        include_content: bool = False,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> dict[str, Any]:
        """Return holographic galaxy nodes for 3D visualization."""
        _require_api_key(x_api_key)

        nodes, edges = _build_nodes_from_galaxy(limit=limit)

        # Fallback to demo data if galaxy is empty
        if not nodes:
            nodes = _DEMO_NODES
            edges = _DEMO_EDGES

        if zone:
            nodes = [n for n in nodes if n.get("zone") == zone]
        if limit:
            nodes = nodes[:limit]
            edges = edges[:limit]

        # Optionally strip content to keep payload small
        if not include_content:
            for n in nodes:
                n.pop("content", None)

        return {
            "nodes": nodes,
            "edges": edges,
            "total": len(nodes),
            "has_coords": len([n for n in nodes if "x" in n]),
            "source": "galaxy_manager" if nodes is not _DEMO_NODES else "demo",
        }

    @router.post("/nodes")
    async def create_galaxy_node(
        request: Request,
        label: str = Body(...),
        content: str = Body(""),
        zone: str = Body("active"),
        importance: float = Body(0.5),
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> dict[str, Any]:
        """Create a new memory node in the active galaxy."""
        _require_api_key(x_api_key)

        try:
            gm = get_galaxy_manager()
            active = gm.get_active()
            um = gm._get_memory(active.name)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Galaxy unavailable: {exc}") from exc

        try:
            from whitemagic.core.memory.unified_types import MemoryType
            mem_type = MemoryType.SHORT_TERM
            for mt in MemoryType:
                if mt.name.lower() == zone.upper() or mt.name.lower() == zone.lower():
                    mem_type = mt
                    break
        except Exception:
            mem_type = None

        try:
            mem = um.store(
                content=content or label,
                title=label,
                tags={"galaxy_node", f"zone:{zone}"},
                importance=max(0.0, min(1.0, importance)),
                memory_type=mem_type,
                metadata={"created_via": "galaxy_api", "zone": zone},
            )
            um.backend.store_coords(
                mem.id,
                round((hash(mem.id) % 1000) / 500 - 1, 4),
                round(((hash(mem.id) // 7) % 1000) / 500 - 1, 4),
                round(((hash(mem.id) // 13) % 1000) / 500 - 1, 4),
                round(importance, 4),
                round(importance, 4),
            )
            return {
                "id": mem.id,
                "label": label,
                "zone": zone,
                "importance": importance,
                "status": "created",
                "galaxy": active.name,
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to create node: {exc}") from exc
