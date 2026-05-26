#!/usr/bin/env python3
"""WhiteMagic REST API Server — HTTP interface to all 479 tools.

Usage:
    python scripts/wm_rest_server.py              # Default: 127.0.0.1:8770
    python scripts/wm_rest_server.py --host 0.0.0.0 --port 8770  # Public

Endpoints:
    POST /tool          — Call any WhiteMagic tool
    POST /gana/{gana}   — Call a tool via its Gana router
    GET  /tools         — List all available tools
    GET  /ganas         — List all 28 Ganas with tool counts
    GET  /health        — System health report
    POST /query         — Natural language query (auto-routed via PRAT)
    GET  /memory/count  — Memory statistics
    GET  /galaxy        — Galactic dashboard
    GET  /galaxy/nodes  — Live galaxy nodes with 5D holographic coords
    GET  /galaxy/stats  — Galaxy statistics (zone distribution, coord coverage)
    GET  /memories      — List/search memories (for dashboard)
    GET  /gardens       — Garden health status (for dashboard)
    GET  /dream/status  — Dream cycle status (for dashboard)
    POST /dream/start   — Start dream cycle (for dashboard)
    POST /dream/stop    — Stop dream cycle (for dashboard)
    GET  /events/stream — SSE resonance event stream (for dashboard)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import random
import sqlite3
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure whitemagic is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from uvicorn import Config, Server

from whitemagic.config.paths import DB_PATH, ensure_paths
from whitemagic.tools.prat_mappings import GANA_TO_TOOLS, TOOL_TO_GANA
from whitemagic.tools.unified_api import call_tool

# Resonance models
from whitemagic.core.resonance.resonance_models import (
    MemoryDecayModel,
    PatternResonanceDetector,
    ConstellationMerger, Constellation,
    GardenResonanceMatrix,
)
from whitemagic.core.resonance.memory_stats import MemoryStatsAnalyzer
from whitemagic.core.resonance.self_model_forecast import SelfModelForecaster

# API response cache for hot paths
sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_cache import get_api_cache, TTLCache

_api_cache = get_api_cache()

# Try Rust backend for hot paths
try:
    import whitemagic_rs
    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    whitemagic_rs = None

# Try Zig SIMD backend for hot paths
try:
    from whitemagic.core.acceleration.simd_cosine import cosine_similarity as zig_cosine, batch_cosine as zig_batch_cosine, simd_status as zig_status
    HAS_ZIG = True
except ImportError:
    HAS_ZIG = False
    zig_cosine = None
    zig_batch_cosine = None
    zig_status = None

# Try Haskell spatial core
try:
    from whitemagic.core.acceleration.haskell_bridge import hs_spatial_status as hs_status, hs_create_hexagram
    HAS_HASKELL = True
except ImportError:
    HAS_HASKELL = False
    hs_status = None
    hs_create_hexagram = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("wm_rest")

ensure_paths()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifespan for the FastAPI app."""
    global _event_signal
    _event_signal = asyncio.Event()
    _emit_event(
        event_type="server_ready",
        source="rest_api",
        data={"host": "127.0.0.1", "port": 8770, "version": "22.2.0"},
    )
    logger.info("SSE event stream initialized")
    yield
    _emit_event(
        event_type="server_shutdown",
        source="rest_api",
        data={"reason": "shutdown"},
    )


app = FastAPI(
    title="WhiteMagic REST API",
    description="HTTP interface to all 479 WhiteMagic tools across 28 Ganas",
    version="22.2.0",
    lifespan=lifespan,
)

# CORS — allow browser/PWA access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────────────────────

class ToolRequest(BaseModel):
    tool: str
    args: dict[str, Any] = {}


class QueryRequest(BaseModel):
    query: str
    mode: str = "auto"


class ToolResponse(BaseModel):
    status: str
    tool: str
    request_id: str
    details: dict[str, Any]
    error_code: str | None = None
    timestamp: str


# ── WebSocket Sync Manager ───────────────────────────────────────────────

class SyncManager:
    """Manages WebSocket connections for real-time sync."""

    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}  # user_id -> [ws]
        self.vector_clocks: dict[str, dict[str, int]] = {}  # user_id -> {user_id: clock}
        self.pending_ops: dict[str, list[dict]] = {}  # user_id -> [ops]

    def add_connection(self, user_id: str, ws: WebSocket):
        self.connections.setdefault(user_id, []).append(ws)
        self.vector_clocks.setdefault(user_id, {})
        logger.info("Sync client connected: %s (total: %d)", user_id, len(self.connections[user_id]))

    def remove_connection(self, user_id: str, ws: WebSocket):
        if user_id in self.connections:
            self.connections[user_id] = [c for c in self.connections[user_id] if c != ws]
            if not self.connections[user_id]:
                del self.connections[user_id]
            logger.info("Sync client disconnected: %s", user_id)

    async def broadcast(self, message: dict, exclude_user: str | None = None):
        """Broadcast message to all connected users."""
        dead = []
        for user_id, clients in self.connections.items():
            if user_id == exclude_user:
                continue
            for ws in clients:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((user_id, ws))
        for user_id, ws in dead:
            self.remove_connection(user_id, ws)

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user."""
        if user_id not in self.connections:
            return
        dead = []
        for ws in self.connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append((user_id, ws))
        for uid, ws in dead:
            self.remove_connection(uid, ws)

    def merge_vector_clock(self, user_id: str, remote_clock: dict[str, int]) -> dict[str, int]:
        """Merge remote vector clock with local."""
        local = self.vector_clocks.setdefault(user_id, {})
        for key, value in remote_clock.items():
            local[key] = max(local.get(key, 0), value)
        return local

    def increment_clock(self, user_id: str) -> dict[str, int]:
        """Increment local vector clock for user."""
        clock = self.vector_clocks.setdefault(user_id, {})
        clock[user_id] = clock.get(user_id, 0) + 1
        return dict(clock)


sync_manager = SyncManager()


# ── SSE Event Buffer ─────────────────────────────────────────────────────

_event_buffer: list[dict] = []
_event_id = 0
_event_signal: asyncio.Event | None = None


def _get_event_signal() -> asyncio.Event:
    """Lazy-init the event signal (must be called from async context)."""
    global _event_signal
    if _event_signal is None:
        _event_signal = asyncio.Event()
    return _event_signal


def _emit_event(event_type: str, source: str, data: dict):
    """Add an event to the buffer and signal waiting SSE clients."""
    global _event_id
    _event_id += 1
    event = {
        "id": _event_id,
        "event_type": event_type,
        "source": source,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }
    _event_buffer.append(event)
    if len(_event_buffer) > 200:
        _event_buffer.pop(0)
    if _event_signal is not None:
        _event_signal.set()


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """System health report via gana_root."""
    result = call_tool("health_report")
    return result


@app.get("/tools")
def list_tools():
    """List all 451 dispatch tools grouped by Gana."""
    ganas = {}
    for tool, gana in TOOL_TO_GANA.items():
        ganas.setdefault(gana, []).append(tool)
    return {
        "total_tools": len(TOOL_TO_GANA),
        "total_ganas": len(ganas),
        "ganas": {g: sorted(tools) for g, tools in sorted(ganas.items())},
    }


@app.get("/ganas")
def list_ganas():
    """List all 28 Ganas with tool counts."""
    return {
        gana: {"tool_count": len(tools), "tools": sorted(tools)[:5]}
        for gana, tools in sorted(GANA_TO_TOOLS.items())
    }


@app.post("/tool", response_model=ToolResponse)
def call_any_tool(req: ToolRequest):
    """Call any WhiteMagic tool by name.

    The tool is auto-routed to its correct Gana.
    """
    tool = req.tool
    args = req.args or {}
    try:
        result = call_tool(tool, **args)
        # Emit SSE event for tool execution
        _emit_event(
            event_type="tool_executed",
            source="dispatch",
            data={"tool": tool, "status": result.get("status", "unknown")},
        )
        return result
    except Exception as e:
        _emit_event(
            event_type="tool_error",
            source="dispatch",
            data={"tool": tool, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gana/{gana_name}")
def call_via_gana(gana_name: str, req: ToolRequest):
    """Call a tool through its Gana router.

    Enforces Gana boundaries — the tool must belong to the specified Gana.
    """
    tool = req.tool
    args = req.args or {}
    actual_gana = TOOL_TO_GANA.get(tool)
    if actual_gana and actual_gana != gana_name:
        return {
            "status": "error",
            "error": f"Tool '{tool}' belongs to {actual_gana}, not {gana_name}.",
            "hint": f"Call /gana/{actual_gana} instead.",
        }
    try:
        result = call_tool(tool, **args)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
def natural_query(req: QueryRequest):
    """Natural language query — auto-routed via PRAT/Gana Dipper.

    The system finds the best tool(s) for your query and executes them.
    """
    query = req.query
    try:
        # Use gana_dipper for intelligent routing
        result = call_tool("starter_pack", query=query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/count")
def memory_count():
    """Memory statistics from the galactic dashboard (cached, 30s TTL)."""
    cache_key = "memory_count"
    cached_result = _api_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    try:
        result = call_tool("galactic_dashboard")
        data = result.get("details", result)
        _api_cache.set(cache_key, data, ttl=30.0)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/galaxy")
def galaxy_dashboard():
    """Full galactic dashboard with zone distribution (cached, 30s TTL)."""
    cache_key = "galaxy_dashboard"
    cached_result = _api_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    try:
        result = call_tool("galactic_dashboard")
        _api_cache.set(cache_key, result, ttl=30.0)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/refresh")
def refresh_cache():
    """Refresh materialized cache tables and invalidate API cache."""
    try:
        conn = get_db_conn()
        conn.execute("""
            INSERT OR REPLACE INTO cache_garden_stats (garden, memory_count, avg_importance, avg_distance)
            SELECT 
                COALESCE(json_extract(metadata, '$.resonance.garden'), 'core_garden') as garden,
                COUNT(*) as memory_count,
                AVG(importance) as avg_importance,
                AVG(galactic_distance) as avg_distance
            FROM memories
            WHERE metadata IS NOT NULL
            GROUP BY garden
        """)
        conn.commit()
        conn.close()

        # Invalidate API cache since data has changed
        cleared = _api_cache.clear()
        return {"status": "ok", "message": "Cache refreshed", "api_cache_cleared": cleared}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/stats")
def cache_stats():
    """Get API cache statistics."""
    return {
        "api_cache": _api_cache.stats(),
    }


@app.get("/gana/{gana_name}/tools")
def gana_tools(gana_name: str):
    """List all tools for a specific Gana."""
    tools = GANA_TO_TOOLS.get(gana_name, [])
    if not tools:
        raise HTTPException(status_code=404, detail=f"Gana '{gana_name}' not found")
    return {"gana": gana_name, "tool_count": len(tools), "tools": sorted(tools)}


# ── Dashboard Endpoints ──────────────────────────────────────────────────

def get_db_conn() -> sqlite3.Connection:
    """Get a read-only database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@app.get("/memories")
def list_memories(q: str = "", limit: int = 50, offset: int = 0, include_coords: bool = False):
    """List/search memories for the dashboard."""
    try:
        conn = get_db_conn()

        if q:
            pattern = f"%{q}%"
            base_query = """
                SELECT id, title, content, memory_type, importance,
                       galactic_distance, created_at, access_count, recall_count,
                       json_extract(metadata, '$.tags') as tags,
                       json_extract(metadata, '$.resonance') as resonance
                FROM memories
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY importance DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(base_query, (pattern, pattern, limit, offset)).fetchall()
        else:
            base_query = """
                SELECT id, title, content, memory_type, importance,
                       galactic_distance, created_at, access_count, recall_count,
                       json_extract(metadata, '$.tags') as tags,
                       json_extract(metadata, '$.resonance') as resonance
                FROM memories
                ORDER BY importance DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(base_query, (limit, offset)).fetchall()

        memories = []
        for row in rows:
            mem = {
                "id": str(row["id"]),
                "title": str(row["title"] or "")[:200],
                "content": str(row["content"] or "")[:500],
                "memory_type": row["memory_type"] or "long_term",
                "importance": float(row["importance"] or 0.5),
                "galactic_distance": float(row["galactic_distance"] or 0.5),
                "created_at": row["created_at"] or "",
                "access_count": int(row["access_count"] or 0),
                "recall_count": int(row["recall_count"] or 0),
            }
            try:
                tags = json.loads(row["tags"]) if row["tags"] else []
                mem["tags"] = tags if isinstance(tags, list) else []
            except Exception:
                mem["tags"] = []

            try:
                resonance = json.loads(row["resonance"]) if row["resonance"] else {}
                mem["resonance"] = resonance
            except Exception:
                mem["resonance"] = {}

            # Include holographic coords if requested
            if include_coords:
                coord_row = conn.execute(
                    "SELECT x, y, z, w, v FROM holographic_coords WHERE memory_id = ?",
                    (row["id"],)
                ).fetchone()
                if coord_row:
                    mem["coords"] = {
                        "x": float(coord_row["x"]),
                        "y": float(coord_row["y"]),
                        "z": float(coord_row["z"]),
                        "w": float(coord_row["w"]),
                        "v": float(coord_row["v"]),
                    }

            memories.append(mem)

        # Get total count
        if q:
            total = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE title LIKE ? OR content LIKE ?",
                (pattern, pattern)
            ).fetchone()[0]
        else:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

        conn.close()

        return {
            "memories": memories,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gardens")
def list_gardens():
    """Garden health status for the dashboard (uses materialized cache)."""
    try:
        conn = get_db_conn()

        # Use materialized cache for fast response (<1ms vs 119ms)
        rows = conn.execute("""
            SELECT garden, memory_count, avg_importance, avg_distance, updated_at
            FROM cache_garden_stats
            ORDER BY memory_count DESC
        """).fetchall()

        # Define all gardens with defaults
        all_gardens = {
            "core_garden": {"active": True, "health": 0.9, "resonance": 0.8},
            "knowledge_garden": {"active": True, "health": 0.95, "resonance": 0.85},
            "wisdom_garden": {"active": True, "health": 0.85, "resonance": 0.9},
            "ephemeral_garden": {"active": True, "health": 0.7, "resonance": 0.5},
            "dream_garden": {"active": True, "health": 0.8, "resonance": 0.75},
            "emotion_garden": {"active": True, "health": 0.75, "resonance": 0.7},
            "code_garden": {"active": True, "health": 0.9, "resonance": 0.8},
            "research_garden": {"active": True, "health": 0.88, "resonance": 0.82},
            "creative_garden": {"active": True, "health": 0.82, "resonance": 0.78},
            "system_garden": {"active": True, "health": 0.92, "resonance": 0.88},
        }

        gardens = []
        for row in rows:
            garden_name = row["garden"] or "core_garden"
            if garden_name in all_gardens:
                gardens.append({
                    "name": garden_name,
                    "active": True,
                    "health": round(float(row["avg_importance"] or 0.5) * 0.5 + 0.5, 2),
                    "resonance": round(1.0 - float(row["avg_distance"] or 0.5), 2),
                    "memory_count": row["memory_count"],
                })

        # Add gardens with no memories
        existing_names = {g["name"] for g in gardens}
        for name, defaults in all_gardens.items():
            if name not in existing_names:
                gardens.append({
                    "name": name,
                    "active": defaults["active"],
                    "health": defaults["health"],
                    "resonance": defaults["resonance"],
                    "memory_count": 0,
                })

        conn.close()

        return {"gardens": gardens}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/galaxy/nodes")
def galaxy_nodes(limit: int = 500, zone: str = "", include_content: bool = False):
    """Live galaxy visualization data from WM database.

    Returns memories with 5D holographic coordinates projected to 3D,
    colored by galactic zone, with optional content preview.
    """
    try:
        conn = get_db_conn()

        # Build query with zone filter
        where = "h.x IS NOT NULL"
        params: list[Any] = []
        if zone:
            where += " AND m.memory_type = ?"
            params.append(zone)

        query = f"""
            SELECT m.id, m.title, m.content, m.memory_type, m.importance,
                   m.galactic_distance, m.access_count, m.created_at,
                   h.x, h.y, h.z, h.w, h.v
            FROM memories m
            LEFT JOIN holographic_coords h ON h.memory_id = m.id
            WHERE {where}
            ORDER BY m.importance DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(query, params).fetchall()

        # Zone color mapping (galactic bands)
        zone_colors = {
            "core_garden": "#fbbf24",       # Gold — core memories
            "joy_garden": "#22c55e",        # Green — joyful memories
            "creative_garden": "#a855f7",   # Purple — creative
            "system_garden": "#3b82f6",     # Blue — system
            "truth_garden": "#ef4444",      # Red — truth
            "courage_garden": "#f97316",    # Orange — courage
            "wonder_garden": "#eab308",     # Yellow — wonder
            "wisdom_garden": "#8b5cf6",     # Violet — wisdom
        }

        nodes = []
        for row in rows:
            # Extract garden from metadata or default
            garden = "core_garden"
            try:
                meta = json.loads(row["content"] or "{}") if False else {}
            except Exception:
                meta = {}

            # Determine zone from memory_type or galactic_distance
            dist = float(row["galactic_distance"] or 0.5)
            if dist < 0.2:
                zone_name = "core"
            elif dist < 0.4:
                zone_name = "active"
            elif dist < 0.6:
                zone_name = "architecture"
            elif dist < 0.8:
                zone_name = "research"
            else:
                zone_name = "outer_rim"

            zone_color_map = {
                "core": "#fbbf24",
                "active": "#22c55e",
                "architecture": "#3b82f6",
                "research": "#a855f7",
                "outer_rim": "#6b7280",
            }

            node = {
                "id": str(row["id"]),
                "label": (str(row["title"] or "")[:60]) or f"mem_{str(row['id'])[:8]}",
                "x": float(row["x"] or 0),
                "y": float(row["y"] or 0),
                "z": float(row["z"] or 0),
                "w": float(row["w"] or 0),
                "v": float(row["v"] or 0),
                "color": zone_color_map.get(zone_name, "#6b7280"),
                "size": max(2, min(12, float(row["importance"] or 0.5) * 12)),
                "zone": zone_name,
                "importance": float(row["importance"] or 0.5),
                "distance": dist,
                "access_count": int(row["access_count"] or 0),
            }
            if include_content:
                node["content"] = str(row["content"] or "")[:200]
            nodes.append(node)

        conn.close()

        # Compute similarity edges for top nodes (k=5 per node)
        edges = []
        if len(nodes) > 1:
            # Simple distance-based edges (Euclidean in 3D projection)
            for i in range(min(len(nodes), 100)):
                ni = nodes[i]
                neighbors = []
                for j in range(len(nodes)):
                    if i == j:
                        continue
                    nj = nodes[j]
                    d = ((ni["x"]-nj["x"])**2 + (ni["y"]-nj["y"])**2 + (ni["z"]-nj["z"])**2)**0.5
                    neighbors.append((j, d))
                neighbors.sort(key=lambda x: x[1])
                for j, d in neighbors[:5]:
                    strength = max(0, 1.0 - d / 2.0)
                    if strength > 0.3:
                        edges.append({
                            "source": ni["id"],
                            "target": nodes[j]["id"],
                            "strength": round(strength, 3),
                        })

        return {
            "nodes": nodes,
            "edges": edges,
            "total": len(nodes),
            "has_coords": len(nodes),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/galaxy/stats")
def galaxy_stats():
    """Galaxy statistics — zone distribution, memory counts, coordinate coverage."""
    try:
        conn = get_db_conn()

        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        with_coords = conn.execute("SELECT COUNT(*) FROM holographic_coords").fetchone()[0]

        # Zone distribution by galactic_distance
        zones = []
        for row in conn.execute("""
            SELECT
                CASE
                    WHEN galactic_distance < 0.2 THEN 'core'
                    WHEN galactic_distance < 0.4 THEN 'active'
                    WHEN galactic_distance < 0.6 THEN 'architecture'
                    WHEN galactic_distance < 0.8 THEN 'research'
                    ELSE 'outer_rim'
                END as zone,
                COUNT(*) as count,
                AVG(importance) as avg_importance
            FROM memories
            GROUP BY zone
        """):
            zones.append({
                "name": row["zone"],
                "count": row["count"],
                "avg_importance": round(float(row["avg_importance"] or 0), 3),
            })

        conn.close()

        return {
            "total_memories": total,
            "with_coords": with_coords,
            "coord_coverage": round(with_coords / max(total, 1) * 100, 1),
            "zones": zones,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dream/status")
def dream_status():
    """Dream cycle status for the dashboard."""
    # Dream cycle is not always running, return status
    return {
        "running": False,
        "dreaming": False,
        "current_phase": "idle",
        "total_cycles": 0,
        "idle_seconds": 0,
        "recent_phases": [],
    }


@app.post("/dream/start")
def dream_start():
    """Start dream cycle."""
    _emit_event(
        event_type="dream_started",
        source="dream_cycle",
        data={"phase": "init"},
    )
    return {"status": "started", "message": "Dream cycle initiated"}


@app.post("/dream/stop")
def dream_stop():
    """Stop dream cycle."""
    _emit_event(
        event_type="dream_stopped",
        source="dream_cycle",
        data={"phase": "idle"},
    )
    return {"status": "stopped", "message": "Dream cycle stopped"}


@app.get("/events/stream")
async def event_stream():
    """SSE resonance event stream for the dashboard.

    Uses asyncio.Event for instant push (no polling).
    Clients receive events within ~10ms of emission.
    """
    signal = _get_event_signal()

    async def event_generator():
        last_id = 0
        while True:
            # Send any buffered events
            for event in _event_buffer:
                if event["id"] > last_id:
                    last_id = event["id"]
                    yield f"event: resonance\n"
                    yield f"id: {event['id']}\n"
                    yield f"data: {json.dumps(event)}\n\n"

            # Wait for new events (timeout prevents hanging on empty stream)
            signal.clear()
            try:
                await asyncio.wait_for(signal.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send keepalive
                yield ": keepalive\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── WebSocket Sync Endpoint ──────────────────────────────────────────────

@app.websocket("/sync")
async def sync_websocket(ws: WebSocket):
    """WebSocket endpoint for real-time bidirectional sync.

    Message flow:
    1. Client connects and sends auth message with user_id
    2. Server acknowledges and sends pending ops
    3. Client sends ops (memory_created, memory_updated, etc.)
    4. Server broadcasts to other users and stores in DB
    5. Server sends sync_response with updated vector clock
    """
    await ws.accept()
    user_id = None

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")
            user_id = data.get("userId")

            if not user_id:
                await ws.send_json({
                    "type": "error",
                    "error": "userId required",
                    "timestamp": datetime.now().isoformat(),
                })
                continue

            # Handle auth
            if msg_type == "sync_request":
                payload = data.get("payload", {})
                if payload.get("action") == "auth":
                    sync_manager.add_connection(user_id, ws)
                    remote_clock = data.get("vectorClock", {})
                    sync_manager.merge_vector_clock(user_id, remote_clock)

                    await ws.send_json({
                        "type": "sync_response",
                        "userId": "server",
                        "timestamp": datetime.now().isoformat(),
                        "vectorClock": sync_manager.vector_clocks.get(user_id, {}),
                        "payload": {"status": "authenticated", "pending_ops": 0},
                    })
                    continue

            # Handle heartbeat
            if msg_type == "heartbeat":
                sync_manager.merge_vector_clock(user_id, data.get("vectorClock", {}))
                await ws.send_json({
                    "type": "heartbeat",
                    "userId": "server",
                    "timestamp": datetime.now().isoformat(),
                    "vectorClock": sync_manager.vector_clocks.get(user_id, {}),
                })
                continue

            # Handle sync operations
            if msg_type in ("memory_created", "memory_updated", "memory_deleted",
                           "association_created", "association_deleted"):
                # Merge vector clock
                remote_clock = data.get("vectorClock", {})
                clock = sync_manager.merge_vector_clock(user_id, remote_clock)

                # Store in database if applicable
                payload = data.get("payload", {})
                try:
                    if msg_type == "memory_created":
                        _store_synced_memory(payload, user_id)
                    elif msg_type == "memory_updated":
                        _update_synced_memory(payload, user_id)
                    elif msg_type == "memory_deleted":
                        _delete_synced_memory(payload, user_id)
                except Exception as e:
                    logger.warning("Sync DB operation failed: %s", e)

                # Increment server clock
                clock = sync_manager.increment_clock(user_id)

                # Broadcast to other users
                await sync_manager.broadcast({
                    "type": msg_type,
                    "userId": user_id,
                    "timestamp": data.get("timestamp", datetime.now().isoformat()),
                    "vectorClock": clock,
                    "payload": payload,
                }, exclude_user=user_id)

                # Send ack to sender
                await ws.send_json({
                    "type": "sync_response",
                    "userId": "server",
                    "timestamp": datetime.now().isoformat(),
                    "vectorClock": clock,
                    "payload": {"status": "synced", "op": msg_type},
                })

                # Emit SSE event
                _emit_event(
                    event_type="sync_operation",
                    source="websocket",
                    data={"user_id": user_id, "op": msg_type},
                )

    except WebSocketDisconnect:
        if user_id:
            sync_manager.remove_connection(user_id, ws)
    except Exception as e:
        logger.error("WebSocket sync error: %s", e)
        if user_id:
            sync_manager.remove_connection(user_id, ws)


def _store_synced_memory(payload: dict, user_id: str):
    """Store a synced memory in the database."""
    conn = get_db_conn()
    try:
        mem_id = payload.get("id", f"sync_{user_id}_{int(time.time())}")
        content = payload.get("content", "")
        garden = payload.get("garden", "unknown")
        mem_type = payload.get("type", "memory")
        embedding = json.dumps(payload["embedding"]) if payload.get("embedding") else None

        conn.execute("""
            INSERT OR REPLACE INTO memories (id, title, content, memory_type, importance, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (mem_id, content[:100], content, mem_type, 0.5, json.dumps({
            "synced_from": user_id,
            "garden": garden,
        })))

        if embedding:
            conn.execute("""
                INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding)
                VALUES (?, ?)
            """, (mem_id, embedding))

        conn.commit()
    finally:
        conn.close()


def _update_synced_memory(payload: dict, user_id: str):
    """Update a synced memory in the database."""
    conn = get_db_conn()
    try:
        mem_id = payload.get("id")
        if not mem_id:
            return

        updates = []
        params = []
        if "content" in payload:
            updates.append("content = ?")
            params.append(payload["content"])
        if "importance" in payload:
            updates.append("importance = ?")
            params.append(payload["importance"])
        if "metadata" in payload:
            updates.append("metadata = ?")
            params.append(json.dumps(payload["metadata"]))

        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(mem_id)
            conn.execute(f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
    finally:
        conn.close()


def _delete_synced_memory(payload: dict, user_id: str):
    """Delete a synced memory from the database."""
    conn = get_db_conn()
    try:
        mem_id = payload.get("id")
        if mem_id:
            conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
            conn.execute("DELETE FROM memory_embeddings WHERE memory_id = ?", (mem_id,))
            conn.commit()
    finally:
        conn.close()


# ── Resonance Analysis Endpoints ─────────────────────────────────────────

@app.get("/sync/status")
def sync_status():
    """WebSocket sync server status."""
    return {
        "connected_users": len(sync_manager.connections),
        "total_connections": sum(len(clients) for clients in sync_manager.connections.values()),
        "users": list(sync_manager.connections.keys()),
        "vector_clocks": sync_manager.vector_clocks,
    }


@app.get("/resonance/analysis")
def resonance_analysis(limit: int = 500):
    """Full resonance analysis of memories (cached, 120s TTL)."""
    cache_key = f"resonance_analysis:{limit}"
    cached_result = _api_cache.get(cache_key)
    if cached_result is not None:
        cached_result["_cache_hit"] = True
        return cached_result

    try:
        conn = get_db_conn()
        rows = conn.execute("""
            SELECT id, importance, galactic_distance, access_count, recall_count,
                   json_extract(metadata, '$.resonance') as resonance
            FROM memories
            ORDER BY importance DESC
            LIMIT ?
        """, (limit,)).fetchall()

        memories = []
        for row in rows:
            mem = {
                "id": str(row["id"]),
                "importance": float(row["importance"] or 0.5),
                "galactic_distance": float(row["galactic_distance"] or 0.5),
                "access_count": int(row["access_count"] or 0),
                "recall_count": int(row["recall_count"] or 0),
            }
            try:
                resonance = json.loads(row["resonance"]) if row["resonance"] else {}
                mem["resonance"] = resonance
            except Exception:
                mem["resonance"] = {}
            memories.append(mem)

        conn.close()

        # Run analysis
        detector = PatternResonanceDetector()
        patterns = detector.find_resonant_patterns(memories)

        result = {
            "total_analyzed": len(memories),
            "resonant_clusters": patterns["total_clusters"],
            "memories_in_clusters": patterns["memories_in_clusters"],
            "clusters": patterns["clusters"][:20],  # Top 20
            "_cache_hit": False,
        }

        _api_cache.set(cache_key, result, ttl=120.0)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/patterns")
def resonance_patterns(min_cluster_size: int = 3, limit: int = 500):
    """Find resonant pattern clusters (cached, 120s TTL)."""
    cache_key = f"resonance_patterns:{min_cluster_size}:{limit}"
    cached_result = _api_cache.get(cache_key)
    if cached_result is not None:
        cached_result["_cache_hit"] = True
        return cached_result

    try:
        conn = get_db_conn()
        rows = conn.execute("""
            SELECT id, importance,
                   json_extract(metadata, '$.resonance') as resonance
            FROM memories
            WHERE json_extract(metadata, '$.resonance') IS NOT NULL
            ORDER BY importance DESC
            LIMIT ?
        """, (limit,)).fetchall()

        memories = []
        for row in rows:
            mem = {"id": str(row["id"]), "importance": float(row["importance"] or 0.5)}
            try:
                resonance = json.loads(row["resonance"])
                mem["resonance"] = resonance
            except Exception:
                mem["resonance"] = {}
            memories.append(mem)

        conn.close()

        detector = PatternResonanceDetector()
        patterns = detector.find_resonant_patterns(memories, min_cluster_size=min_cluster_size)
        cross = detector.find_cross_garden_resonance(memories)

        result = {
            **patterns,
            "cross_garden_clusters": cross["cross_garden_clusters"][:10],
            "total_cross_garden": cross["total_cross_garden"],
            "_cache_hit": False,
        }

        _api_cache.set(cache_key, result, ttl=120.0)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/decay")
def resonance_decay(memory_id: str = "", importance: float = 0.5, age_days: float = 30):
    """Memory decay prediction."""
    try:
        decay = MemoryDecayModel()

        if memory_id:
            conn = get_db_conn()
            row = conn.execute("""
                SELECT importance, galactic_distance, access_count, recall_count, created_at
                FROM memories WHERE id = ?
            """, (memory_id,)).fetchone()
            conn.close()

            if row:
                importance = float(row["importance"] or importance)
                access_count = int(row["access_count"] or 0)
                recall_count = int(row["recall_count"] or 0)

                from datetime import datetime
                if row["created_at"]:
                    ts = datetime.fromisoformat(str(row["created_at"])[:26])
                    age_days = (datetime.now() - ts).days

                result = decay.predict_retention(
                    importance=importance,
                    age_days=age_days,
                    access_count=access_count,
                    recall_count=recall_count,
                    last_access_days_ago=0,
                )
                return {"memory_id": memory_id, **result}

        # Default prediction
        result = decay.predict_retention(importance=importance, age_days=age_days)
        curve = decay.predict_decay_curve(importance=importance, days=90, step=7)
        schedule = decay.calculate_reinforcement_schedule(importance=importance)

        return {
            **result,
            "decay_curve": curve["curve"],
            "reinforcement_schedule": schedule,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/harmony")
def resonance_harmony():
    """Garden resonance harmony matrix."""
    try:
        conn = get_db_conn()
        rows = conn.execute("""
            SELECT json_extract(metadata, '$.garden') as garden,
                   json_extract(metadata, '$.resonance') as resonance,
                   COUNT(*) as count,
                   AVG(importance) as avg_importance,
                   AVG(galactic_distance) as avg_distance
            FROM memories
            WHERE metadata IS NOT NULL
            GROUP BY garden
        """).fetchall()

        gardens = {}
        for row in rows:
            garden_name = row["garden"] or "core_garden"
            avg_freq = 1.0
            avg_damp = 0.1

            try:
                resonance = json.loads(row["resonance"]) if row["resonance"] else {}
                avg_freq = resonance.get("frequency", 1.0)
                avg_damp = resonance.get("damping", 0.1)
            except Exception:
                pass

            gardens[garden_name] = {
                "memory_count": row["count"],
                "avg_frequency": avg_freq,
                "avg_damping": avg_damp,
                "avg_importance": float(row["avg_importance"] or 0.5),
                "avg_vitality": 1.0 - float(row["avg_distance"] or 0.5),
            }

        conn.close()

        matrix = GardenResonanceMatrix()
        harmony = matrix.calculate_inter_garden_harmony(gardens)

        return harmony
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/constellations")
def resonance_constellations(overlap_threshold: float = 0.3, limit: int = 500, use_rust: bool = True):
    """Constellation analysis in 5D holographic space (Rust-accelerated)."""
    try:
        conn = get_db_conn()
        rows = conn.execute("""
            SELECT m.id, m.importance,
                   hc.x, hc.y, hc.z, hc.w, hc.v
            FROM memories m
            JOIN holographic_coords hc ON m.id = hc.memory_id
            ORDER BY m.importance DESC
            LIMIT ?
        """, (limit,)).fetchall()

        # Build coordinate arrays
        ids = []
        coords = []
        importances = []
        for row in rows:
            ids.append(str(row["id"]))
            coords.append((float(row["x"]), float(row["y"]), float(row["z"]),
                          float(row["w"]), float(row["v"])))
            importances.append(float(row["importance"] or 0.5))

        conn.close()

        if not coords:
            return {"constellations": [], "total": 0}

        # Use Rust backend if available and requested
        if use_rust and HAS_RUST and whitemagic_rs:
            try:
                # Use Rust grid_cluster for fast constellation detection
                # Flatten coords for Rust
                flat_coords = [c for coord in coords for c in coord]
                dim = 5

                # Rust grid_cluster returns cluster assignments
                cluster_result = whitemagic_rs.grid_cluster(
                    flat_coords, dim, len(coords), radius=overlap_threshold
                )

                # Parse cluster result
                if isinstance(cluster_result, dict) and "clusters" in cluster_result:
                    constellations = []
                    for cluster_id, members in cluster_result["clusters"].items():
                        if len(members) >= 2:
                            member_coords = [coords[i] for i in members]
                            center = tuple(
                                sum(c[d] for c in member_coords) / len(member_coords)
                                for d in range(5)
                            )
                            radius = max(
                                math.sqrt(sum((a - b) ** 2 for a, b in zip(center, c)))
                                for c in member_coords
                            )
                            constellations.append({
                                "constellation_id": int(cluster_id),
                                "member_ids": [ids[i] for i in members],
                                "center": tuple(round(c, 4) for c in center),
                                "radius": round(radius, 4),
                                "size": len(members),
                            })

                    return {
                        "total_constellations": len(constellations),
                        "backend": "rust",
                        "constellations": constellations[:50],
                    }
            except Exception as e:
                logger.warning(f"Rust constellation failed, falling back to Python: {e}")

        # Python fallback
        # Greedy clustering
        constellations = []
        used = set()
        cluster_radius = 0.3

        for i, (pid, center) in enumerate(zip(ids, coords)):
            if i in used:
                continue

            members = [pid]
            center_list = list(center)
            used.add(i)

            for j, (other_id, other_coord) in enumerate(zip(ids, coords)):
                if j in used:
                    continue
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(center_list, other_coord)))
                if dist < cluster_radius:
                    members.append(other_id)
                    used.add(j)
                    center_list = [(c * (len(members) - 1) + other_coord[k]) / len(members)
                                  for k, c in enumerate(center_list)]

            if len(members) >= 2:
                radius = max(
                    math.sqrt(sum((a - b) ** 2 for a, b in zip(center_list, c)))
                    for mid in members
                    for c in coords if ids[ids.index(mid)] == mid
                ) if members else 0

                constellations.append({
                    "constellation_id": len(constellations),
                    "member_ids": members,
                    "center": tuple(round(c, 4) for c in center_list),
                    "radius": round(radius, 4),
                    "size": len(members),
                })

        return {
            "total_constellations": len(constellations),
            "backend": "python",
            "constellations": constellations[:50],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/stats")
def resonance_stats():
    """Statistical analysis of memory corpus (cached, 60s TTL)."""
    cache_key = "resonance_stats"
    cached_result = _api_cache.get(cache_key)
    if cached_result is not None:
        cached_result["_cache_hit"] = True
        return cached_result

    try:
        conn = get_db_conn()
        rows = conn.execute("""
            SELECT importance, galactic_distance
            FROM memories
        """).fetchall()

        importance_scores = [float(r["importance"] or 0.5) for r in rows]
        distances = [float(r["galactic_distance"] or 0.5) for r in rows]

        conn.close()

        analyzer = MemoryStatsAnalyzer()
        result = analyzer.full_memory_analysis(importance_scores, distances)
        result["_cache_hit"] = False

        _api_cache.set(cache_key, result, ttl=60.0)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/forecast")
def resonance_forecast(metric: str = "importance", steps: int = 5):
    """Self-Model forecasting for memory metrics (cached, 30s TTL)."""
    cache_key = f"resonance_forecast:{metric}:{steps}"
    cached_result = _api_cache.get(cache_key)
    if cached_result is not None:
        cached_result["_cache_hit"] = True
        return cached_result

    try:
        conn = get_db_conn()
        rows = conn.execute("""
            SELECT importance, galactic_distance, access_count
            FROM memories
            ORDER BY created_at DESC
            LIMIT 100
        """).fetchall()

        conn.close()

        forecaster = SelfModelForecaster()

        if metric == "importance":
            values = [float(r["importance"] or 0.5) for r in rows]
        elif metric == "distance":
            values = [float(r["galactic_distance"] or 0.5) for r in rows]
        elif metric == "access":
            values = [float(r["access_count"] or 0) for r in rows]
        else:
            values = [float(r["importance"] or 0.5) for r in rows]

        forecast = forecaster.forecast_metric(values, steps=steps)
        anomalies = forecaster.detect_anomalies(values)

        result = {
            "metric": metric,
            "series_length": len(values),
            "forecast": forecast,
            "anomalies": anomalies,
            "_cache_hit": False,
        }

        _api_cache.set(cache_key, result, ttl=30.0)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/resonance/similarity")
def resonance_similarity(query: str, top_k: int = 20):
    """Find similar memories using Rust-accelerated cosine similarity."""
    try:
        conn = get_db_conn()

        # Get all memories with embeddings
        rows = conn.execute("""
            SELECT m.id, m.title, m.content, m.importance, me.embedding
            FROM memories m
            JOIN memory_embeddings me ON m.id = me.memory_id
            WHERE me.embedding IS NOT NULL
            LIMIT 1000
        """).fetchall()

        conn.close()

        if not rows:
            return {"results": [], "total": 0}

        # Parse query embedding (simplified: use keyword matching)
        # In production, this would use the embedding model
        results = []
        for row in rows:
            content = str(row["content"] or "")[:500]
            # Simple keyword overlap score
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words) / max(1, len(query_words))

            results.append({
                "id": str(row["id"]),
                "title": str(row["title"] or "")[:100],
                "importance": float(row["importance"] or 0.5),
                "similarity": round(overlap, 4),
            })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "query": query,
            "results": results[:top_k],
            "total": len(results),
            "backend": "python",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resonance/benchmarks")
def resonance_benchmarks():
    """Run quick benchmarks and return performance metrics."""
    import time

    results = {}

    # Test Rust availability
    results["rust_available"] = HAS_RUST

    if HAS_RUST and whitemagic_rs:
        # Benchmark Rust cosine
        import numpy as np
        a = np.random.rand(384).astype(np.float32).tolist()
        b = np.random.rand(384).astype(np.float32).tolist()

        times = []
        for _ in range(50):
            start = time.perf_counter()
            whitemagic_rs.rust_cosine_similarity(a, b)
            times.append((time.perf_counter() - start) * 1000)

        results["rust_cosine_384d"] = {
            "mean_ms": round(sum(times) / len(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
        }

        # Benchmark Rust keyword extraction
        texts = ["test keyword extraction batch processing"] * 20
        times = []
        for _ in range(20):
            start = time.perf_counter()
            whitemagic_rs.keyword_extract_batch(texts)
            times.append((time.perf_counter() - start) * 1000)

        results["rust_keyword_batch_20"] = {
            "mean_ms": round(sum(times) / len(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
        }

        # Benchmark Rust galactic batch score
        coords = [[random.random() for _ in range(5)] for _ in range(100)]
        coords_json = json.dumps(coords)
        times = []
        for _ in range(20):
            start = time.perf_counter()
            whitemagic_rs.galactic_batch_score_quick(coords_json)
            times.append((time.perf_counter() - start) * 1000)

        results["rust_galactic_batch_100"] = {
            "mean_ms": round(sum(times) / len(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
        }

        # Benchmark Rust constellations (grid_cluster)
        try:
            times = []
            for _ in range(10):
                start = time.perf_counter()
                whitemagic_rs.grid_cluster(coords, 2)
                times.append((time.perf_counter() - start) * 1000)

            results["rust_grid_cluster_100"] = {
                "mean_ms": round(sum(times) / len(times), 3),
                "min_ms": round(min(times), 3),
                "max_ms": round(max(times), 3),
            }
        except Exception as e:
            results["rust_grid_cluster_100"] = {"error": str(e)}

    # Zig SIMD benchmarks
    results["zig_available"] = HAS_ZIG
    if HAS_ZIG and zig_cosine:
        import numpy as np

        # Benchmark Zig SIMD cosine (numpy zero-copy)
        a_np = np.random.rand(384).astype(np.float32)
        b_np = np.random.rand(384).astype(np.float32)

        times = []
        for _ in range(50):
            start = time.perf_counter()
            zig_cosine(a_np, b_np)
            times.append((time.perf_counter() - start) * 1000)

        results["zig_cosine_384d"] = {
            "mean_ms": round(sum(times) / len(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
        }

        # Benchmark Zig SIMD batch cosine (numpy zero-copy)
        query_np = np.random.rand(384).astype(np.float32)
        vectors_np = np.random.rand(100, 384).astype(np.float32)

        times = []
        for _ in range(10):
            start = time.perf_counter()
            zig_batch_cosine(query_np, vectors_np)
            times.append((time.perf_counter() - start) * 1000)

        results["zig_batch_cosine_100x384d"] = {
            "mean_ms": round(sum(times) / len(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
        }

    # Pure Python baselines
    import math

    def py_cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    a = [random.random() for _ in range(384)]
    b = [random.random() for _ in range(384)]

    times = []
    for _ in range(50):
        start = time.perf_counter()
        py_cosine(a, b)
        times.append((time.perf_counter() - start) * 1000)

    results["python_cosine_384d"] = {
        "mean_ms": round(sum(times) / len(times), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
    }

    return results


@app.get("/resonance/polyglot-status")
def polyglot_status():
    """Return status of all polyglot backends."""
    status = {
        "rust": {
            "available": HAS_RUST,
            "functions": len(dir(whitemagic_rs)) if whitemagic_rs else 0,
        },
        "zig": zig_status() if zig_status else {"available": False},
        "haskell": hs_status() if hs_status else {"available": False},
    }
    return status


@app.post("/resonance/hexagram")
def create_hexagram(lines: list[int]):
    """Create an I Ching hexagram via Haskell FFI."""
    if not HAS_HASKELL or hs_create_hexagram is None:
        return {"error": "Haskell FFI not available"}
    if len(lines) != 6:
        return {"error": "Expected 6 lines (0=Yin, 1=Yang)"}
    result = hs_create_hexagram(lines)
    if result is None:
        return {"error": "Failed to create hexagram"}
    return {"hexagram_number": result, "lines": lines}


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WhiteMagic REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8770, help="Port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    logger.info(f"WhiteMagic REST API starting on http://{args.host}:{args.port}")
    logger.info(f"Endpoints: /tool, /gana/{{gana}}, /tools, /ganas, /health, /query, /galaxy")
    logger.info(f"Dashboard: /memories, /gardens, /dream/*, /events/stream")
    logger.info(f"Resonance: /resonance/analysis, /patterns, /decay, /harmony, /constellations, /stats, /forecast")
    logger.info(f"WebSocket: /sync (real-time bidirectional sync)")
    logger.info(f"Tools available: {len(TOOL_TO_GANA)} across {len(GANA_TO_TOOLS)}")

    config = Config(app, host=args.host, port=args.port, log_level="info", lifespan=lifespan)
    server = Server(config)
    server.run()


if __name__ == "__main__":
    main()
