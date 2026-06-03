"""Galaxy API — Holographic memory visualization endpoints.

Phase 4 stub: returns demo galaxy data with optional API-key gating.
"""

import os
from typing import Any

try:
    from fastapi import APIRouter, Header, HTTPException, Request
    router = APIRouter(prefix="/galaxy", tags=["galaxy"])
except ImportError:  # pragma: no cover - optional dependency
    APIRouter = None  # type: ignore[misc,assignment]
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

        nodes = _DEMO_NODES
        if zone:
            nodes = [n for n in nodes if n["zone"] == zone]
        if limit:
            nodes = nodes[:limit]

        return {
            "nodes": nodes,
            "edges": _DEMO_EDGES,
            "total": len(_DEMO_NODES),
            "has_coords": len([n for n in _DEMO_NODES if "x" in n]),
        }
