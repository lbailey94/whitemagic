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
import secrets
import sqlite3
import sys
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure whitemagic is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from uvicorn import Config, Server

from whitemagic.config.paths import DB_PATH, ensure_paths
from whitemagic.tools.prat_mappings import GANA_TO_TOOLS, TOOL_TO_GANA
from whitemagic.tools.unified_api import call_tool

# Resonance models
from whitemagic.core.resonance.resonance_models import (
    MemoryDecayModel,
    PatternResonanceDetector,
    GardenResonanceMatrix,
)
from whitemagic.core.resonance.memory_stats import MemoryStatsAnalyzer
from whitemagic.core.resonance.self_model_forecast import SelfModelForecaster

# API response cache for hot paths
sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_cache import get_api_cache

_api_cache = get_api_cache()

try:
    import whitemagic_rs

    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    whitemagic_rs = None

try:
    from whitemagic.core.acceleration.simd_cosine import (
        cosine_similarity as zig_cosine,
        batch_cosine as zig_batch_cosine,
        simd_status as zig_status,
    )

    HAS_ZIG = True
except ImportError:
    HAS_ZIG = False
    zig_cosine = None
    zig_batch_cosine = None
    zig_status = None

try:
    from whitemagic.core.acceleration.haskell_bridge import (
        hs_spatial_status as hs_status,
        hs_create_hexagram,
    )

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

# CORS — restrict to known origins (production + dev)
ALLOWED_ORIGINS = [
    "https://whitemagic.dev",
    "https://app.whitemagic.dev",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-User-Id"],
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


# ── Security: Token Bucket, Nonce Cache, WebSocket Validation ────────────


class TokenBucket:
    """In-memory token bucket for WebSocket rate limiting."""

    def __init__(self, rate: float = 0.5, capacity: int = 10):
        self.rate = rate  # tokens per second (0.5 = 30/min)
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class NonceCache:
    """LRU cache for seen nonces to prevent replay attacks."""

    def __init__(self, max_size: int = 10000, ttl: float = 300):
        self.max_size = max_size
        self.ttl = ttl  # 5 minutes
        self.seen: deque[tuple[str, float]] = deque(maxlen=max_size)
        self._set: set[str] = set()

    def check_and_add(self, nonce: str) -> bool:
        """Return True if nonce is NEW (not replayed). False if replayed."""
        if nonce in self._set:
            return False
        now = time.time()
        # Evict expired nonces
        while self.seen and now - self.seen[0][1] > self.ttl:
            _, old_nonce = self.seen.popleft()
            self._set.discard(old_nonce)
        self.seen.append((nonce, now))
        self._set.add(nonce)
        return True


class SyncSession:
    """Per-session state for authenticated WebSocket connections."""

    def __init__(self, user_id: str, ws: WebSocket, session_key: bytes):
        self.user_id = user_id
        self.ws = ws
        self.session_key = session_key  # 32-byte HKDF-derived key
        self.rate_limiter = TokenBucket()
        self.connected_at = time.time()
        # Presence state
        self.presence_status: str = "active"
        self.presence_since: float = time.time()
        self.current_view: str | None = None
        self.editing_node: str | None = None
        self.cursor_band: tuple[int, int, int] | None = (
            None  # Quantized to galactic band
        )
        self.incognito: bool = False


class SyncMessage(BaseModel):
    """Validated WebSocket message schema."""

    type: str
    userId: str = Field(..., min_length=3, max_length=64)
    timestamp: float = Field(..., gt=0)
    nonce: str = Field(..., min_length=16, max_length=64)
    vectorClock: dict[str, int] = Field(default_factory=dict, max_items=100)
    payload: dict | None = None


# ── WebSocket Sync Manager ───────────────────────────────────────────────


class SyncManager:
    """Manages WebSocket connections for real-time sync."""

    def __init__(self):
        self.sessions: dict[str, list[SyncSession]] = {}  # user_id -> [sessions]
        self.vector_clocks: dict[
            str, dict[str, int]
        ] = {}  # user_id -> {user_id: clock}
        self.pending_ops: dict[str, list[dict]] = {}  # user_id -> [ops]
        self.nonce_cache = NonceCache()
        self.server_private_key = X25519PrivateKey.generate()
        self.server_public_key = self.server_private_key.public_key()

    def add_session(
        self, user_id: str, ws: WebSocket, session_key: bytes
    ) -> SyncSession:
        session = SyncSession(user_id, ws, session_key)
        self.sessions.setdefault(user_id, []).append(session)
        self.vector_clocks.setdefault(user_id, {})
        logger.info(
            "Sync client authenticated: %s (total sessions: %d)",
            user_id,
            len(self.sessions[user_id]),
        )
        return session

    def remove_session(self, user_id: str, ws: WebSocket):
        if user_id in self.sessions:
            self.sessions[user_id] = [s for s in self.sessions[user_id] if s.ws != ws]
            if not self.sessions[user_id]:
                del self.sessions[user_id]
            logger.info("Sync client disconnected: %s", user_id)

    def get_rate_limiter(self, user_id: str) -> TokenBucket | None:
        """Get the rate limiter for the user's first active session."""
        if user_id in self.sessions and self.sessions[user_id]:
            return self.sessions[user_id][0].rate_limiter
        return None

    def get_presence_list(self, exclude_user: str | None = None) -> list[dict]:
        """Get presence info for all visible users."""
        result = []
        for uid, sessions in self.sessions.items():
            if uid == exclude_user:
                continue
            # Use first session for presence (users may have multiple tabs)
            session = sessions[0]
            if session.incognito:
                continue
            # Coarse status: active if heartbeat < 30s, idle if < 5min, else away
            elapsed = time.time() - session.presence_since
            if session.presence_status == "active" and elapsed < 30:
                status = "active"
            elif elapsed < 300:
                status = "idle"
            else:
                status = "away"
            entry: dict[str, Any] = {
                "user_id": uid,
                "status": status,
                "status_since": session.presence_since,
            }
            if session.current_view:
                entry["current_view"] = session.current_view
            if session.cursor_band:
                entry["cursor_band"] = list(session.cursor_band)
            result.append(entry)
        return result

    async def broadcast_presence(self, exclude_user: str | None = None):
        """Broadcast presence list to all connected users."""
        presence_list = self.get_presence_list(exclude_user)
        await self.broadcast(
            {
                "type": "presence_update",
                "users": presence_list,
                "timestamp": datetime.now().isoformat(),
            },
            exclude_user=exclude_user,
        )

    async def broadcast(self, message: dict, exclude_user: str | None = None):
        """Broadcast message to all connected users."""
        dead = []
        for uid, sessions in self.sessions.items():
            if uid == exclude_user:
                continue
            for session in sessions:
                try:
                    await session.ws.send_json(message)
                except Exception:
                    dead.append((uid, session.ws))
        for uid, ws in dead:
            self.remove_session(uid, ws)

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user."""
        if user_id not in self.sessions:
            return
        dead = []
        for session in self.sessions[user_id]:
            try:
                await session.ws.send_json(message)
            except Exception:
                dead.append((user_id, session.ws))
        for uid, ws in dead:
            self.remove_session(uid, ws)

    def merge_vector_clock(
        self, user_id: str, remote_clock: dict[str, int]
    ) -> dict[str, int]:
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


# ── Crypto Helpers ───────────────────────────────────────────────────────

import base64


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(s: str) -> bytes:
    return base64.b64decode(s)


def _derive_session_key(shared_secret: bytes) -> bytes:
    """Derive 32-byte session key from X25519 shared secret via HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"whitemagic-sync-v1",
    )
    return hkdf.derive(shared_secret)


# ── E2EE: AES-GCM Encryption Helpers ─────────────────────────────────────

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def e2ee_encrypt(
    plaintext: bytes, key: bytes, associated_data: bytes | None = None
) -> dict:
    """Encrypt plaintext with AES-256-GCM.

    Args:
        plaintext: Data to encrypt
        key: 32-byte AES key
        associated_data: Optional AAD (authenticated but not encrypted)

    Returns:
        dict with nonce (base64) and ciphertext (base64)
    """
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    ct = aesgcm.encrypt(nonce, plaintext, associated_data)
    return {
        "nonce": _b64encode(nonce),
        "ciphertext": _b64encode(ct),
    }


def e2ee_decrypt(
    nonce_b64: str,
    ciphertext_b64: str,
    key: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """Decrypt AES-256-GCM ciphertext.

    Raises cryptography.exceptions.InvalidTag if authentication fails.
    """
    aesgcm = AESGCM(key)
    nonce = _b64decode(nonce_b64)
    ciphertext = _b64decode(ciphertext_b64)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


def e2ee_encrypt_json(obj: dict, key: bytes) -> dict:
    """Encrypt a JSON-serializable object."""
    plaintext = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return e2ee_encrypt(plaintext, key)


def e2ee_decrypt_json(nonce_b64: str, ciphertext_b64: str, key: bytes) -> dict:
    """Decrypt and parse a JSON object."""
    plaintext = e2ee_decrypt(nonce_b64, ciphertext_b64, key)
    return json.loads(plaintext.decode("utf-8"))


# ── Audit Logger ─────────────────────────────────────────────────────────


class AuditLogger:
    """Append-only security audit log."""

    def __init__(self, log_path: Path | None = None):
        from whitemagic.config.paths import get_state_root

        state_root = get_state_root()
        state_root.mkdir(exist_ok=True, parents=True)
        self.log_path = log_path or state_root / "security_audit.jsonl"

    def log(
        self,
        event_type: str,
        user_id: str | None = None,
        details: dict | None = None,
        severity: str = "info",
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "severity": severity,
            "details": details or {},
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent audit entries."""
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries[-limit:]


audit_logger = AuditLogger()


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
        return {
            "status": "ok",
            "message": "Cache refreshed",
            "api_cache_cleared": cleared,
        }
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
def list_memories(
    q: str = "", limit: int = 50, offset: int = 0, include_coords: bool = False
):
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
            rows = conn.execute(
                base_query, (pattern, pattern, limit, offset)
            ).fetchall()
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
                    (row["id"],),
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

        if q:
            total = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE title LIKE ? OR content LIKE ?",
                (pattern, pattern),
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
                gardens.append(
                    {
                        "name": garden_name,
                        "active": True,
                        "health": round(
                            float(row["avg_importance"] or 0.5) * 0.5 + 0.5, 2
                        ),
                        "resonance": round(1.0 - float(row["avg_distance"] or 0.5), 2),
                        "memory_count": row["memory_count"],
                    }
                )

        existing_names = {g["name"] for g in gardens}
        for name, defaults in all_gardens.items():
            if name not in existing_names:
                gardens.append(
                    {
                        "name": name,
                        "active": defaults["active"],
                        "health": defaults["health"],
                        "resonance": defaults["resonance"],
                        "memory_count": 0,
                    }
                )

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
            "core_garden": "#fbbf24",  # Gold — core memories
            "joy_garden": "#22c55e",  # Green — joyful memories
            "creative_garden": "#a855f7",  # Purple — creative
            "system_garden": "#3b82f6",  # Blue — system
            "truth_garden": "#ef4444",  # Red — truth
            "courage_garden": "#f97316",  # Orange — courage
            "wonder_garden": "#eab308",  # Yellow — wonder
            "wisdom_garden": "#8b5cf6",  # Violet — wisdom
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
                    d = (
                        (ni["x"] - nj["x"]) ** 2
                        + (ni["y"] - nj["y"]) ** 2
                        + (ni["z"] - nj["z"]) ** 2
                    ) ** 0.5
                    neighbors.append((j, d))
                neighbors.sort(key=lambda x: x[1])
                for j, d in neighbors[:5]:
                    strength = max(0, 1.0 - d / 2.0)
                    if strength > 0.3:
                        edges.append(
                            {
                                "source": ni["id"],
                                "target": nodes[j]["id"],
                                "strength": round(strength, 3),
                            }
                        )

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
        with_coords = conn.execute(
            "SELECT COUNT(*) FROM holographic_coords"
        ).fetchone()[0]

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
            zones.append(
                {
                    "name": row["zone"],
                    "count": row["count"],
                    "avg_importance": round(float(row["avg_importance"] or 0), 3),
                }
            )

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
    """WebSocket endpoint with X25519 key-exchange auth, nonce replay protection, and rate limiting.

    Message flow:
    1. Client connects, sends handshake with user_id + X25519 public key + nonce
    2. Server verifies nonce, derives shared secret, returns server public key + nonce
    3. Both sides derive session key via HKDF
    4. Client sends ops (memory_created, memory_updated, etc.) with nonce per message
    5. Server validates nonce, rate-limits, broadcasts, stores in DB
    """
    await ws.accept()
    user_id = None

    try:
        # ── Phase 1: X25519 Handshake ─────────────────────────────────
        handshake = await ws.receive_json()

        user_id = handshake.get("userId")
        client_public_b64 = handshake.get("x25519_public_key")
        client_nonce = handshake.get("nonce")
        timestamp = handshake.get("timestamp")

        if not all([user_id, client_public_b64, client_nonce, timestamp]):
            audit_logger.log(
                "auth_failed", details={"reason": "missing_fields"}, severity="warning"
            )
            await ws.send_json({"type": "error", "error": "Missing handshake fields"})
            await ws.close(code=4001, reason="Incomplete handshake")
            return

        try:
            ts = float(timestamp)
        except (ValueError, TypeError):
            await ws.send_json({"type": "error", "error": "Invalid timestamp"})
            await ws.close(code=4002, reason="Bad timestamp")
            return

        if abs(time.time() - ts) > 300:
            audit_logger.log(
                "auth_failed",
                user_id=user_id,
                details={"reason": "timestamp_expired"},
                severity="warning",
            )
            await ws.send_json({"type": "error", "error": "Timestamp expired"})
            await ws.close(code=4002, reason="Timestamp expired")
            return

        if not sync_manager.nonce_cache.check_and_add(client_nonce):
            audit_logger.log("nonce_replay", user_id=user_id, severity="critical")
            await ws.send_json({"type": "error", "error": "Nonce replayed"})
            await ws.close(code=4003, reason="Replay detected")
            return

        # Derive shared secret via X25519
        try:
            client_public = X25519PublicKey.from_public_bytes(
                _b64decode(client_public_b64)
            )
        except Exception:
            audit_logger.log(
                "auth_failed",
                user_id=user_id,
                details={"reason": "invalid_public_key"},
                severity="warning",
            )
            await ws.send_json({"type": "error", "error": "Invalid public key"})
            await ws.close(code=4004, reason="Bad key")
            return

        shared_secret = sync_manager.server_private_key.exchange(client_public)
        session_key = _derive_session_key(shared_secret)

        # Send server public key + server nonce
        server_public_b64 = _b64encode(
            sync_manager.server_public_key.public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
        )
        server_nonce = secrets.token_hex(16)

        await ws.send_json(
            {
                "type": "auth_ack",
                "server_public_key": server_public_b64,
                "nonce": server_nonce,
                "timestamp": time.time(),
            }
        )

        # Register session
        sync_manager.add_session(user_id, ws, session_key)
        audit_logger.log("auth_success", user_id=user_id, details={"method": "x25519"})

        # Send initial presence list to new user
        await ws.send_json(
            {
                "type": "presence_list",
                "users": sync_manager.get_presence_list(exclude_user=user_id),
                "timestamp": datetime.now().isoformat(),
            }
        )
        # Notify others about new user
        await sync_manager.broadcast_presence(exclude_user=user_id)

        # ── Phase 2: Message Loop ─────────────────────────────────────
        while True:
            data = await ws.receive_json()

            try:
                msg = SyncMessage.model_validate(data)
            except ValidationError as e:
                await ws.send_json({"type": "error", "error": str(e)})
                continue

            if not sync_manager.nonce_cache.check_and_add(msg.nonce):
                audit_logger.log(
                    "nonce_replay", user_id=msg.userId, severity="critical"
                )
                await ws.send_json({"type": "error", "error": "Nonce replayed"})
                await ws.close(code=4003, reason="Replay detected")
                return

            # Rate limit
            limiter = sync_manager.get_rate_limiter(msg.userId)
            if limiter and not limiter.consume():
                audit_logger.log("rate_limited", user_id=msg.userId, severity="warning")
                await ws.send_json({"type": "error", "error": "Rate limited"})
                continue

            user_id = msg.userId

            if msg.type == "heartbeat":
                sync_manager.merge_vector_clock(user_id, msg.vectorClock)
                # Refresh presence status on heartbeat
                if user_id in sync_manager.sessions and sync_manager.sessions[user_id]:
                    session = sync_manager.sessions[user_id][0]
                    session.presence_since = time.time()
                await ws.send_json(
                    {
                        "type": "heartbeat",
                        "userId": "server",
                        "timestamp": datetime.now().isoformat(),
                        "vectorClock": sync_manager.vector_clocks.get(user_id, {}),
                    }
                )
                continue

            if msg.type == "presence_update":
                if user_id in sync_manager.sessions and sync_manager.sessions[user_id]:
                    session = sync_manager.sessions[user_id][0]
                    payload = msg.payload or {}
                    if "status" in payload:
                        session.presence_status = payload["status"]
                        session.presence_since = time.time()
                    if "current_view" in payload:
                        session.current_view = payload["current_view"]
                    if "editing_node" in payload:
                        session.editing_node = payload["editing_node"]
                    if "cursor_band" in payload:
                        band = payload["cursor_band"]
                        if isinstance(band, list) and len(band) == 3:
                            session.cursor_band = (
                                int(band[0]),
                                int(band[1]),
                                int(band[2]),
                            )
                    if "incognito" in payload:
                        session.incognito = payload["incognito"]
                # Broadcast updated presence to everyone
                await sync_manager.broadcast_presence(exclude_user=user_id)
                # Send back full presence list to sender
                await ws.send_json(
                    {
                        "type": "presence_list",
                        "users": sync_manager.get_presence_list(exclude_user=user_id),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                continue

            if msg.type in (
                "memory_created",
                "memory_updated",
                "memory_deleted",
                "association_created",
                "association_deleted",
            ):
                remote_clock = msg.vectorClock or {}
                clock = sync_manager.merge_vector_clock(user_id, remote_clock)

                payload = msg.payload or {}
                try:
                    if msg.type == "memory_created":
                        _store_synced_memory(payload, user_id)
                    elif msg.type == "memory_updated":
                        _update_synced_memory(payload, user_id)
                    elif msg.type == "memory_deleted":
                        _delete_synced_memory(payload, user_id)
                except Exception as e:
                    logger.warning("Sync DB operation failed: %s", e)

                clock = sync_manager.increment_clock(user_id)

                await sync_manager.broadcast(
                    {
                        "type": msg.type,
                        "userId": user_id,
                        "timestamp": datetime.now().isoformat(),
                        "vectorClock": clock,
                        "payload": payload,
                    },
                    exclude_user=user_id,
                )

                await ws.send_json(
                    {
                        "type": "sync_response",
                        "userId": "server",
                        "timestamp": datetime.now().isoformat(),
                        "vectorClock": clock,
                        "payload": {"status": "synced", "op": msg.type},
                    }
                )

                _emit_event(
                    event_type="sync_operation",
                    source="websocket",
                    data={"user_id": user_id, "op": msg.type},
                )

    except WebSocketDisconnect:
        if user_id:
            sync_manager.remove_session(user_id, ws)
    except Exception as e:
        logger.error("WebSocket sync error: %s", e)
        if user_id:
            sync_manager.remove_session(user_id, ws)


def _store_synced_memory(payload: dict, user_id: str):
    """Store a synced memory in the database."""
    conn = get_db_conn()
    try:
        mem_id = payload.get("id", f"sync_{user_id}_{int(time.time())}")
        content = payload.get("content", "")
        garden = payload.get("garden", "unknown")
        mem_type = payload.get("type", "memory")
        embedding = (
            json.dumps(payload["embedding"]) if payload.get("embedding") else None
        )

        conn.execute(
            """
            INSERT OR REPLACE INTO memories (id, title, content, memory_type, importance, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                mem_id,
                content[:100],
                content,
                mem_type,
                0.5,
                json.dumps(
                    {
                        "synced_from": user_id,
                        "garden": garden,
                    }
                ),
            ),
        )

        if embedding:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding)
                VALUES (?, ?)
            """,
                (mem_id, embedding),
            )

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
            conn.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", params
            )
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
        "connected_users": len(sync_manager.sessions),
        "total_sessions": sum(
            len(sessions) for sessions in sync_manager.sessions.values()
        ),
        "users": list(sync_manager.sessions.keys()),
        "vector_clocks": sync_manager.vector_clocks,
        "nonce_cache_size": len(sync_manager.nonce_cache._set),
    }


@app.get("/audit/log")
def audit_log(limit: int = 50):
    """Recent security audit log entries."""
    return {"entries": audit_logger.get_recent(limit)}


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
        rows = conn.execute(
            """
            SELECT id, importance, galactic_distance, access_count, recall_count,
                   json_extract(metadata, '$.resonance') as resonance
            FROM memories
            ORDER BY importance DESC
            LIMIT ?
        """,
            (limit,),
        ).fetchall()

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
        rows = conn.execute(
            """
            SELECT id, importance,
                   json_extract(metadata, '$.resonance') as resonance
            FROM memories
            WHERE json_extract(metadata, '$.resonance') IS NOT NULL
            ORDER BY importance DESC
            LIMIT ?
        """,
            (limit,),
        ).fetchall()

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
        patterns = detector.find_resonant_patterns(
            memories, min_cluster_size=min_cluster_size
        )
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
            row = conn.execute(
                """
                SELECT importance, galactic_distance, access_count, recall_count, created_at
                FROM memories WHERE id = ?
            """,
                (memory_id,),
            ).fetchone()
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
def resonance_constellations(
    overlap_threshold: float = 0.3, limit: int = 500, use_rust: bool = True
):
    """Constellation analysis in 5D holographic space (Rust-accelerated)."""
    try:
        conn = get_db_conn()
        rows = conn.execute(
            """
            SELECT m.id, m.importance,
                   hc.x, hc.y, hc.z, hc.w, hc.v
            FROM memories m
            JOIN holographic_coords hc ON m.id = hc.memory_id
            ORDER BY m.importance DESC
            LIMIT ?
        """,
            (limit,),
        ).fetchall()

        # Build coordinate arrays
        ids = []
        coords = []
        importances = []
        for row in rows:
            ids.append(str(row["id"]))
            coords.append(
                (
                    float(row["x"]),
                    float(row["y"]),
                    float(row["z"]),
                    float(row["w"]),
                    float(row["v"]),
                )
            )
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
                            constellations.append(
                                {
                                    "constellation_id": int(cluster_id),
                                    "member_ids": [ids[i] for i in members],
                                    "center": tuple(round(c, 4) for c in center),
                                    "radius": round(radius, 4),
                                    "size": len(members),
                                }
                            )

                    return {
                        "total_constellations": len(constellations),
                        "backend": "rust",
                        "constellations": constellations[:50],
                    }
            except Exception as e:
                logger.warning(
                    "Rust constellation failed, falling back to Python: %s", e
                )

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
                dist = math.sqrt(
                    sum((a - b) ** 2 for a, b in zip(center_list, other_coord))
                )
                if dist < cluster_radius:
                    members.append(other_id)
                    used.add(j)
                    center_list = [
                        (c * (len(members) - 1) + other_coord[k]) / len(members)
                        for k, c in enumerate(center_list)
                    ]

            if len(members) >= 2:
                radius = (
                    max(
                        math.sqrt(sum((a - b) ** 2 for a, b in zip(center_list, c)))
                        for mid in members
                        for c in coords
                        if ids[ids.index(mid)] == mid
                    )
                    if members
                    else 0
                )

                constellations.append(
                    {
                        "constellation_id": len(constellations),
                        "member_ids": members,
                        "center": tuple(round(c, 4) for c in center_list),
                        "radius": round(radius, 4),
                        "size": len(members),
                    }
                )

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

        # In production, this would use the embedding model
        results = []
        for row in rows:
            content = str(row["content"] or "")[:500]
            # Simple keyword overlap score
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words) / max(1, len(query_words))

            results.append(
                {
                    "id": str(row["id"]),
                    "title": str(row["title"] or "")[:100],
                    "importance": float(row["importance"] or 0.5),
                    "similarity": round(overlap, 4),
                }
            )

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
    parser.add_argument(
        "--reload", action="store_true", help="Auto-reload on code changes"
    )
    args = parser.parse_args()

    logger.info("WhiteMagic REST API starting on http://%s:%s", args.host, args.port)
    logger.info(
        f"Endpoints: /tool, /gana/{{gana}}, /tools, /ganas, /health, /query, /galaxy"
    )
    logger.info(f"Dashboard: /memories, /gardens, /dream/*, /events/stream")
    logger.info(
        f"Resonance: /resonance/analysis, /patterns, /decay, /harmony, /constellations, /stats, /forecast"
    )
    logger.info(f"WebSocket: /sync (real-time bidirectional sync)")
    logger.info(f"Tools available: {len(TOOL_TO_GANA)} across {len(GANA_TO_TOOLS)}")

    config = Config(
        app, host=args.host, port=args.port, log_level="info", lifespan=lifespan
    )
    server = Server(config)
    server.run()


if __name__ == "__main__":
    main()
