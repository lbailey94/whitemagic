"""Galaxy API — Holographic memory visualization endpoints.

Connects to the real GalaxyManager and returns actual memory nodes
with holographic coordinates from the active galaxy.
"""

import os
import time
from typing import Any

from whitemagic.core.memory.constellation_algorithms import detect_kdtree
from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

# Simple TTL cache for constellation detection results
_CONSTELLATION_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CONSTELLATION_CACHE_TTL: float = 60.0  # seconds

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


class _GalaxyAPIError(Exception):
    """Fallback exception when FastAPI is not installed."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


if HTTPException is None:
    HTTPException = _GalaxyAPIError  # type: ignore[misc,assignment]

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


def _build_nodes_from_galaxy(limit: int = 500, galaxy_name: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Query a galaxy for real memory nodes and edges.

    Args:
        limit: Maximum nodes to return.
        galaxy_name: Optional galaxy to query; uses active galaxy if None.
    """
    try:
        _, um = _resolve_galaxy(galaxy_name)
    except HTTPException:
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


def _build_constellations_from_galaxy(
    limit: int = 500,
    galaxy_name: str | None = None,
    min_members: int = 3,
    max_radius: float = 0.5,
) -> list[dict[str, Any]]:
    """Detect constellations in a galaxy using the Rust KD-tree fast path.

    Args:
        limit: Maximum nodes to consider.
        galaxy_name: Optional galaxy to query.
        min_members: Minimum points per constellation.
        max_radius: Spatial radius for cluster membership.
    """
    try:
        _, um = _resolve_galaxy(galaxy_name)
    except HTTPException:
        return []

    # Gather nodes with 5D coordinates
    memories: list[Any] = []
    try:
        for page in um.backend.list_all_paginated(batch_size=500):
            memories.extend(page)
            if len(memories) >= limit:
                break
    except Exception:
        pass

    if not memories:
        return []

    coords_map: dict[str, tuple] = {}
    try:
        coords_map = um.backend.get_all_coords()
    except Exception:
        pass

    # Build coordinate list with IDs
    coords: list[tuple[float, ...]] = []
    mem_ids: list[str] = []
    mem_lookup: dict[str, Any] = {}

    for mem in memories[:limit]:
        coords_tuple = coords_map.get(mem.id)
        if coords_tuple and len(coords_tuple) >= 3:
            x = float(coords_tuple[0])
            y = float(coords_tuple[1])
            z = float(coords_tuple[2])
            w = float(coords_tuple[3]) if len(coords_tuple) > 3 else 0.5
            v = float(coords_tuple[4]) if len(coords_tuple) > 4 else 0.5
            coords.append((x, y, z, w, v))
            mem_ids.append(str(mem.id))
            mem_lookup[str(mem.id)] = mem
        else:
            # Fallback: hash-based deterministic coordinates
            h = hash(mem.id) & 0x7FFFFFFF
            x = ((h % 1000) / 1000) * 2 - 1
            y = (((h // 1000) % 1000) / 1000) * 2 - 1
            z = (((h // 1000000) % 1000) / 1000) * 2 - 1
            coords.append((x, y, z, 0.5, 0.5))
            mem_ids.append(str(mem.id))
            mem_lookup[str(mem.id)] = mem

    if len(coords) < min_members:
        return []

    try:
        groups, stabilities = detect_kdtree(
            coords, ids=mem_ids, min_members=min_members, max_radius=max_radius
        )
    except Exception:
        return []

    constellations: list[dict[str, Any]] = []
    for i, member_indices in enumerate(groups):
        members = [mem_lookup[mem_ids[idx]] for idx in member_indices if mem_ids[idx] in mem_lookup]
        if not members:
            continue

        # Compute centroid from coords
        cx = sum(coords[idx][0] for idx in member_indices) / len(member_indices)
        cy = sum(coords[idx][1] for idx in member_indices) / len(member_indices)
        cz = sum(coords[idx][2] for idx in member_indices) / len(member_indices)
        cw = sum(coords[idx][3] for idx in member_indices) / len(member_indices)
        cv = sum(coords[idx][4] for idx in member_indices) / len(member_indices)

        # Compute radius (max distance from centroid)
        max_dist = 0.0
        for idx in member_indices:
            dx = coords[idx][0] - cx
            dy = coords[idx][1] - cy
            dz = coords[idx][2] - cz
            dw = coords[idx][3] - cw
            dv = coords[idx][4] - cv
            dist = (dx * dx + dy * dy + dz * dz + dw * dw + dv * dv) ** 0.5
            if dist > max_dist:
                max_dist = dist

        # Dominant tags
        tag_counts: dict[str, int] = {}
        for mem in members:
            for tag in getattr(mem, "tags", []) or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        dominant_tags = sorted(tag_counts, key=lambda t: tag_counts[t], reverse=True)[:5]

        # Dominant zone
        zone_counts: dict[str, int] = {}
        for mem in members:
            zone = _memory_type_to_zone(
                mem.memory_type.name if hasattr(mem.memory_type, "name") else str(mem.memory_type)
            )
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
        dominant_zone = max(zone_counts, key=lambda z: zone_counts[z]) if zone_counts else "active"

        constellations.append({
            "id": f"constellation_{i}",
            "name": f"Cluster {i + 1}",
            "size": len(members),
            "member_ids": [str(mem.id) for mem in members[:10]],
            "centroid": {"x": round(cx, 4), "y": round(cy, 4), "z": round(cz, 4), "w": round(cw, 4), "v": round(cv, 4)},
            "radius": round(max_dist, 4),
            "stability": round(stabilities[i] if i < len(stabilities) else 0.5, 3),
            "dominant_tags": dominant_tags,
            "dominant_zone": dominant_zone,
        })

    return constellations


def _require_api_key(x_api_key: str | None) -> str | None:
    """Validate API key if WM_GALAXY_REQUIRE_KEY is set."""
    require = os.environ.get("WM_GALAXY_REQUIRE_KEY", "").lower() in ("1", "true", "yes")
    if not require:
        return None  # open
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    if x_api_key.startswith("wm_") and len(x_api_key) >= 20:
        return x_api_key
    raise HTTPException(status_code=403, detail="Invalid API key")


def _resolve_galaxy(x_galaxy_name: str | None) -> tuple[Any, Any]:
    """Resolve galaxy from header or active default.

    Returns (galaxy_info, unified_memory) or raises HTTPException.
    """
    gm = get_galaxy_manager()
    if x_galaxy_name:
        info = gm.get_galaxy(x_galaxy_name)
        if not info:
            raise HTTPException(status_code=404, detail=f"Galaxy '{x_galaxy_name}' not found")
        try:
            um = gm._get_memory(x_galaxy_name)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Galaxy unavailable: {exc}") from exc
        return info, um
    return gm.get_active(), gm._get_memory(gm.get_active().name)


if router is not None:
    @router.get("/")
    async def list_galaxies(
        request: Request,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> dict[str, Any]:
        """List all available galaxies."""
        _require_api_key(x_api_key)
        gm = get_galaxy_manager()
        return {
            "active": gm._active_galaxy,
            "galaxies": gm.list_galaxies(),
            "total": len(gm._galaxies),
        }

    @router.get("/nodes")
    async def get_galaxy_nodes(
        request: Request,
        limit: int = 500,
        zone: str | None = None,
        include_content: bool = False,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
        x_galaxy_name: str | None = Header(None, alias="X-Galaxy-Name"),
    ) -> dict[str, Any]:
        """Return holographic galaxy nodes for 3D visualization.

        Supports per-user galaxy isolation via X-Galaxy-Name header.
        If omitted, returns the globally active galaxy.
        """
        _require_api_key(x_api_key)

        nodes, edges = _build_nodes_from_galaxy(limit=limit, galaxy_name=x_galaxy_name)

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
        x_galaxy_name: str | None = Header(None, alias="X-Galaxy-Name"),
    ) -> dict[str, Any]:
        """Create a new memory node in the specified galaxy (or active)."""
        _require_api_key(x_api_key)

        try:
            active, um = _resolve_galaxy(x_galaxy_name)
        except HTTPException:
            raise

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

    @router.get("/constellations")
    async def get_galaxy_constellations(
        request: Request,
        limit: int = 500,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
        x_galaxy_name: str | None = Header(None, alias="X-Galaxy-Name"),
    ) -> dict[str, Any]:
        """Return detected constellations from the galaxy (cached, auto-detect)."""
        _require_api_key(x_api_key)

        cache_key = f"{x_galaxy_name or 'active'}:{limit}"
        now = time.time()

        # Check TTL cache
        cached = _CONSTELLATION_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _CONSTELLATION_CACHE_TTL:
            return {
                "constellations": cached[1],
                "total": len(cached[1]),
                "source": "cache",
                "cached_at": cached[0],
            }

        constellations = _build_constellations_from_galaxy(
            limit=limit, galaxy_name=x_galaxy_name
        )

        # Populate cache
        _CONSTELLATION_CACHE[cache_key] = (now, constellations)

        return {
            "constellations": constellations,
            "total": len(constellations),
            "source": "galaxy_manager",
        }

    @router.post("/constellations/detect")
    async def detect_galaxy_constellations(
        request: Request,
        min_members: int = Body(3),
        max_radius: float = Body(0.5),
        limit: int = Body(500),
        x_api_key: str | None = Header(None, alias="X-API-Key"),
        x_galaxy_name: str | None = Header(None, alias="X-Galaxy-Name"),
    ) -> dict[str, Any]:
        """Trigger fresh constellation detection with tunable parameters.

        Invalidates the read cache for this galaxy.
        """
        _require_api_key(x_api_key)

        cache_key = f"{x_galaxy_name or 'active'}:{limit}"
        _CONSTELLATION_CACHE.pop(cache_key, None)

        t0 = time.time()
        constellations = _build_constellations_from_galaxy(
            limit=limit,
            galaxy_name=x_galaxy_name,
            min_members=min_members,
            max_radius=max_radius,
        )
        elapsed = time.time() - t0

        # Populate cache with fresh result
        _CONSTELLATION_CACHE[cache_key] = (time.time(), constellations)

        return {
            "constellations": constellations,
            "total": len(constellations),
            "source": "galaxy_manager",
            "elapsed_ms": round(elapsed * 1000, 2),
            "params": {"min_members": min_members, "max_radius": max_radius, "limit": limit},
        }
