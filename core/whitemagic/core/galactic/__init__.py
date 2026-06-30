"""
Galactic Substrate — v23.0 rehydration layer.

Connects the current `whitemagic.core` to the live substrate state DB at
``~/.whitemagic/memory/whitemagic.db``. The substrate is the persistent
memory + embeddings + associations + dharma + constellation + akashic
storage; this module is the read/write API the rest of the core uses.

v23.0 history (per WHITEMAGIC_CHRONOLOGY_2026-06-20.md):
    - Live Era (2025-11-11 to 2025-12-27): Whitemagic-Core on Inspiron 3582
      ran a self-recursive substrate writing 33,297 events to disk.
    - Polyglot Era (v15.8.0, 2026-02-13): 111,665 memories, 2,247,642
      associations, 30 constellations, 182 communities. Galaxy rehydrated.
    - Current (v22.5.0 → v23.0): The live DB at ~/.whitemagic/memory/
      has 12,238 memories + 21,087 associations + 12,638 embeddings
      (per Phase 5 audit). The current core never imported it.

This module is the bridge: it gives the v22.x catalog access to the
substrate that already exists on disk.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

# Centralized path config — never use Path.home() / .expanduser() here.
# Per core/AGENTS.md §10 rule 6.
from whitemagic.config.paths import MEMORY_DIR

logger = logging.getLogger(__name__)


# ─── Defaults ──────────────────────────────────────────────────────

# Default substrate DB path comes from the centralized paths module,
# which respects WM_STATE_ROOT, falls back to ~/.whitemagic, and is
# the single source of truth for all runtime state.
DEFAULT_DB_PATH = MEMORY_DIR / "whitemagic.db"

# Kept for backward-compat re-exports; new code should use DEFAULT_DB_PATH.
DEFAULT_STATE_ROOT = MEMORY_DIR.parent

# Galactic zones (matches v17 whitemagic.core.memory.galactic_map).
GALACTIC_ZONES = {
    (0.00, 0.15): "CORE",
    (0.15, 0.40): "INNER_RIM",
    (0.40, 0.65): "MID_BAND",
    (0.65, 0.85): "OUTER_RIM",
    (0.85, 1.01): "FAR_EDGE",
}


# ─── Connection management ─────────────────────────────────────────


_thread_local = threading.local()


def classify_zone(distance: float) -> str:
    """Map a galactic distance to its named zone.

    Distances are in [0.0, 1.0]: 0.0 is the galactic core (hot, vital,
    frequently accessed), 1.0 is the far edge (deep archive, low recall
    but never deleted). Matches v17 whitemagic.core.memory.galactic_map.
    """
    if distance < 0.15:
        return "CORE"
    if distance < 0.40:
        return "INNER_RIM"
    if distance < 0.65:
        return "MID_BAND"
    if distance < 0.85:
        return "OUTER_RIM"
    return "FAR_EDGE"


def _resolve_db_path() -> Path:
    """Resolve the substrate DB path, falling back to a search.

    Priority:
    1. WM_MEMORY_DB env var (explicit override)
    2. DEFAULT_DB_PATH (from whitemagic.config.paths — respects WM_STATE_ROOT)
    3. The centralized path — works in most setups
    """
    p = Path(os.environ.get("WM_MEMORY_DB", str(DEFAULT_DB_PATH)))
    if p.exists():
        return p
    # Fall back to MEMORY_DIR (the centralized path). This avoids Path.home()
    # usage in this module — paths.py is the single source of truth.
    return MEMORY_DIR / "whitemagic.db"


def get_db_path() -> Path:
    """Public: report the resolved substrate DB path."""
    return _resolve_db_path()


@contextmanager
def connect(read_only: bool = True) -> Iterator[sqlite3.Connection]:
    """Open a connection to the substrate DB.

    Uses a thread-local connection so the same thread reuses the same
    handle (the live DB has 12K+ rows and a per-query open is wasteful).
    """
    path = _resolve_db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Substrate DB not found at {path}. "
            "Set WM_STATE_ROOT or WM_MEMORY_DB, or run the rehydration script."
        )
    uri = f"file:{path}?mode=ro" if read_only else f"file:{path}"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ─── Data shapes ──────────────────────────────────────────────────


@dataclass
class Memory:
    """A single substrate memory."""

    id: str
    title: str | None
    content: str | None
    memory_type: str
    importance: float
    emotional_valence: float
    neuro_score: float
    novelty_score: float
    galactic_distance: float
    galactic_zone: str
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Memory":
        distance = float(row["galactic_distance"] or 0.0)
        zone = "FAR_EDGE"
        for (lo, hi), name in GALACTIC_ZONES.items():
            if lo <= distance < hi:
                zone = name
                break
        tags_raw = row["tags"] or ""
        tags = [t for t in tags_raw.split(",") if t] if isinstance(tags_raw, str) else []
        meta: dict[str, Any] = {}
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except (ValueError, TypeError):
                meta = {"_raw": row["metadata"]}
        return cls(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            memory_type=row["memory_type"] or "SHORT_TERM",
            importance=float(row["importance"] or 0.5),
            emotional_valence=float(row["emotional_valence"] or 0.0),
            neuro_score=float(row["neuro_score"] or 0.0),
            novelty_score=float(row["novelty_score"] or 0.5),
            galactic_distance=distance,
            galactic_zone=zone,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tags=tags,
            metadata=meta,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
            "neuro_score": self.neuro_score,
            "novelty_score": self.novelty_score,
            "galactic_distance": self.galactic_distance,
            "galactic_zone": self.galactic_zone,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class GalaxyStats:
    """Substrate-wide statistics from a single full sweep."""

    total_memories: int
    total_associations: int
    total_embeddings: int
    by_zone: dict[str, int]
    by_type: dict[str, int]
    avg_importance: float
    avg_neuro_score: float
    oldest_memory: str | None
    newest_memory: str | None
    sweep_duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_memories": self.total_memories,
            "total_associations": self.total_associations,
            "total_embeddings": self.total_embeddings,
            "by_zone": self.by_zone,
            "by_type": self.by_type,
            "avg_importance": round(self.avg_importance, 3),
            "avg_neuro_score": round(self.avg_neuro_score, 3),
            "oldest_memory": self.oldest_memory,
            "newest_memory": self.newest_memory,
            "sweep_duration_ms": round(self.sweep_duration_ms, 2),
        }


# ─── Public API: substrate queries ─────────────────────────────────


def galaxy_stats() -> GalaxyStats:
    """Single-pass statistics about the entire substrate.

    Returns counts, zone distribution, type distribution, averages,
    and oldest/newest memory timestamps. Used by /api/galactic/stats
    and the librarian's `galactic.stats` bridge function.
    """
    t0 = time.perf_counter()
    with connect() as conn:
        cur = conn.cursor()
        total_memories = cur.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        total_associations = cur.execute(
            "SELECT COUNT(*) FROM associations"
        ).fetchone()[0]
        # memory_embeddings may be missing in older substrates.
        try:
            total_embeddings = cur.execute(
                "SELECT COUNT(*) FROM memory_embeddings"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            total_embeddings = 0

        # Zone distribution via single GROUP BY.
        by_zone: dict[str, int] = {name: 0 for name in GALACTIC_ZONES.values()}
        for row in cur.execute(
            "SELECT galactic_distance FROM memories WHERE galactic_distance IS NOT NULL"
        ):
            d = float(row[0] or 0.0)
            for (lo, hi), name in GALACTIC_ZONES.items():
                if lo <= d < hi:
                    by_zone[name] += 1
                    break

        by_type: dict[str, int] = {}
        for row in cur.execute(
            "SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type"
        ):
            by_type[row[0] or "UNKNOWN"] = row[1]

        avg_row = cur.execute(
            "SELECT AVG(importance), AVG(neuro_score) FROM memories"
        ).fetchone()
        avg_importance = float(avg_row[0] or 0.0)
        avg_neuro_score = float(avg_row[1] or 0.0)

        oldest = cur.execute(
            "SELECT created_at FROM memories WHERE created_at IS NOT NULL "
            "ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        newest = cur.execute(
            "SELECT created_at FROM memories WHERE created_at IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    return GalaxyStats(
        total_memories=total_memories,
        total_associations=total_associations,
        total_embeddings=total_embeddings,
        by_zone=by_zone,
        by_type=by_type,
        avg_importance=avg_importance,
        avg_neuro_score=avg_neuro_score,
        oldest_memory=oldest[0] if oldest else None,
        newest_memory=newest[0] if newest else None,
        sweep_duration_ms=(time.perf_counter() - t0) * 1000,
    )


def memory_recent(limit: int = 10, memory_type: str | None = None) -> list[Memory]:
    """Most recently updated memories, optionally filtered by type."""
    if limit <= 0:
        return []
    limit = min(int(limit), 200)
    query = "SELECT * FROM memories"
    params: tuple[Any, ...] = ()
    if memory_type:
        query += " WHERE memory_type = ?"
        params = (memory_type,)
    query += " ORDER BY COALESCE(updated_at, created_at) DESC LIMIT ?"
    params = params + (limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Memory.from_row(r) for r in rows]


def memory_search(
    query: str, limit: int = 10, memory_type: str | None = None,
    galaxy: str | None = None,
) -> list[Memory]:
    """FTS5 search across memory content. Falls back to LIKE if FTS unavailable."""
    if not query or limit <= 0:
        return []
    limit = min(int(limit), 100)
    with connect() as conn:
        # Prefer FTS5 if present (it usually is in the live substrate).
        try:
            # Build FTS5 query: phrase match first, keyword fallback
            fts_query = query.strip()
            # Sanitize FTS5-unsafe characters
            for ch in r'[]{}()^~*:,;\/':
                fts_query = fts_query.replace(ch, ' ')
            fts_query = fts_query.strip()
            if not fts_query:
                fts_query = query.strip()

            # For multi-word queries, try phrase match first
            if " " in fts_query and not (fts_query.startswith('"') and fts_query.endswith('"')):
                phrase_q = f'"{fts_query}"'
                # Test if phrase match returns results
                test_rows = conn.execute(
                    "SELECT COUNT(*) FROM memories_fts WHERE memories_fts MATCH ?",
                    (phrase_q,),
                ).fetchone()
                if test_rows[0] > 0:
                    fts_query = phrase_q
                else:
                    # Fall back to individual keywords (implicit AND in FTS5)
                    fts5_reserved = {"OR", "AND", "NOT", "NEAR"}
                    keywords = [k for k in fts_query.split() if k and k.upper() not in fts5_reserved]
                    fts_query = " ".join(keywords) if keywords else fts_query

            sql = (
                "SELECT m.* FROM memories_fts fts "
                "JOIN memories m ON m.id = fts.id "
                "WHERE memories_fts MATCH ?"
            )
            params: tuple[Any, ...] = (fts_query,)
            if memory_type:
                sql += " AND m.memory_type = ?"
                params = params + (memory_type,)
            if galaxy:
                sql += " AND m.galaxy = ?"
                params = params + (galaxy,)
            sql += " ORDER BY rank LIMIT ?"
            params = params + (limit,)
            rows = conn.execute(sql, params).fetchall()
            if rows:
                return [Memory.from_row(r) for r in rows]
        except sqlite3.OperationalError:
            pass
        # Fallback: LIKE-based substring search.
        like = f"%{query}%"
        sql = (
            "SELECT * FROM memories WHERE (title LIKE ? OR content LIKE ?)"
        )
        params = (like, like)
        if memory_type:
            sql += " AND memory_type = ?"
            params = params + (memory_type,)
        if galaxy:
            sql += " AND galaxy = ?"
            params = params + (galaxy,)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params = params + (limit,)
        rows = conn.execute(sql, params).fetchall()
    return [Memory.from_row(r) for r in rows]


def memory_by_id(memory_id: str) -> Memory | None:
    """Look up a single memory by its substrate id."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
    return Memory.from_row(row) if row else None


def associations_for(
    memory_id: str, direction: str = "outgoing", limit: int = 25
) -> list[dict[str, Any]]:
    """Return associations touching a memory (with the other endpoint)."""
    if not memory_id or limit <= 0:
        return []
    limit = min(int(limit), 200)
    with connect() as conn:
        if direction == "outgoing":
            rows = conn.execute(
                "SELECT target_id, strength, relation_type, traversal_count "
                "FROM associations WHERE source_id = ? "
                "ORDER BY strength DESC LIMIT ?",
                (memory_id, limit),
            ).fetchall()
        elif direction == "incoming":
            rows = conn.execute(
                "SELECT source_id, strength, relation_type, traversal_count "
                "FROM associations WHERE target_id = ? "
                "ORDER BY strength DESC LIMIT ?",
                (memory_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT source_id, target_id, strength, relation_type, "
                "traversal_count FROM associations "
                "WHERE source_id = ? OR target_id = ? "
                "ORDER BY strength DESC LIMIT ?",
                (memory_id, memory_id, limit),
            ).fetchall()
    out = []
    for r in rows:
        if direction == "both":
            other = r["target_id"] if r["source_id"] == memory_id else r["source_id"]
        elif direction == "outgoing":
            other = r["target_id"]
        else:
            other = r["source_id"]
        out.append(
            {
                "memory_id": memory_id,
                "other_id": other,
                "strength": float(r["strength"] or 0.0),
                "relation_type": r["relation_type"],
                "traversal_count": r["traversal_count"] or 0,
            }
        )
    return out


def event_search(
    query: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Search the dharma_audit table (the substrate's ethics event log).

    The Whitemagic-Core era had a separate events.jsonl (33K events);
    that data is migrated via the rehydration script into dharma_audit
    rows with `metadata_json` containing the original event payload.
    """
    if limit <= 0:
        return []
    limit = min(int(limit), 200)
    clauses: list[str] = []
    params: list[Any] = []
    if event_type:
        clauses.append("boundary_type = ?")
        params.append(event_type)
    if since:
        clauses.append("timestamp >= ?")
        params.append(since)
    if query:
        clauses.append("(action LIKE ? OR context LIKE ? OR concerns LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT id, timestamp, action, boundary_type, ethical_score, concerns FROM dharma_audit{where} ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "action": r["action"],
            "boundary_type": r["boundary_type"],
            "ethical_score": float(r["ethical_score"] or 0.0),
            "concerns": r["concerns"],
        }
        for r in rows
    ]


def constellation_count() -> int:
    """Number of HDBSCAN-detected constellations in the substrate."""
    with connect() as conn:
        try:
            row = conn.execute("SELECT COUNT(*) FROM constellation_membership").fetchone()
        except sqlite3.OperationalError:
            return 0
    return row[0] if row else 0


def substrate_health() -> dict[str, Any]:
    """Top-level health check for the substrate.

    Returns a dict with: db_path, db_exists, db_size_bytes, total_memories,
    total_associations, total_embeddings, total_dharma_audits, substrate_version.
    """
    path = _resolve_db_path()
    out: dict[str, Any] = {
        "db_path": str(path),
        "db_exists": path.exists(),
        "db_size_bytes": path.stat().st_size if path.exists() else 0,
        "total_memories": 0,
        "total_associations": 0,
        "total_embeddings": 0,
        "total_dharma_audits": 0,
        "total_constellations": 0,
        "total_akashic_seeds": 0,
    }
    if not path.exists():
        out["status"] = "missing"
        return out
    try:
        with connect() as conn:
            out["total_memories"] = conn.execute(
                "SELECT COUNT(*) FROM memories"
            ).fetchone()[0]
            out["total_associations"] = conn.execute(
                "SELECT COUNT(*) FROM associations"
            ).fetchone()[0]
            try:
                out["total_embeddings"] = conn.execute(
                    "SELECT COUNT(*) FROM memory_embeddings"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                out["total_embeddings"] = 0
            try:
                out["total_dharma_audits"] = conn.execute(
                    "SELECT COUNT(*) FROM dharma_audit"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                out["total_dharma_audits"] = 0
            try:
                out["total_constellations"] = conn.execute(
                    "SELECT COUNT(DISTINCT constellation_id) FROM constellation_membership"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                out["total_constellations"] = 0
            try:
                out["total_akashic_seeds"] = conn.execute(
                    "SELECT COUNT(*) FROM akashic_seeds"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                out["total_akashic_seeds"] = 0
        out["status"] = "alive"
    except sqlite3.DatabaseError as e:
        out["status"] = "error"
        out["error"] = str(e)
    return out


__all__ = [
    "GALACTIC_ZONES",
    "DEFAULT_STATE_ROOT",
    "DEFAULT_DB_PATH",
    "Memory",
    "GalaxyStats",
    "classify_zone",
    "connect",
    "get_db_path",
    "galaxy_stats",
    "memory_recent",
    "memory_search",
    "memory_by_id",
    "associations_for",
    "event_search",
    "constellation_count",
    "substrate_health",
]
