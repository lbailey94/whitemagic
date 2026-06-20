# ruff: noqa: BLE001
"""Bridge module: galactic substrate operations (v23.0).

Connects the mcp_api_bridge to the live substrate at
``~/.whitemagic/memory/whitemagic.db``. The substrate is real and
active: 12K+ memories, 21K associations, 12K+ embeddings, 35K+ dharma
audits (as of v23.0.0-alpha.1 rehydration of Whitemagic-Core data).

These functions are the substrate's "API" for the bridge catalog —
they let the librarian, the site, and A2A peers query the actual
memory + audit log + resonance state.

The pattern matches existing bridge modules (archaeology.py, dharma.py,
etc.) — lazy import with graceful degradation if the substrate is
unreachable (returns ``{"status": "unavailable", ...}`` so the
librarian can recover instead of crashing).
"""
from __future__ import annotations

from typing import Any


def _get_galactic():
    """Lazy import of the galactic substrate module."""
    try:
        from whitemagic.core.galactic import (
            GalaxyStats,
            associations_for,
            classify_zone,
            constellation_count,
            event_search,
            galaxy_stats,
            memory_by_id,
            memory_recent,
            memory_search,
            substrate_health,
        )
        return {
            "GalaxyStats": GalaxyStats,
            "associations_for": associations_for,
            "classify_zone": classify_zone,
            "constellation_count": constellation_count,
            "event_search": event_search,
            "galaxy_stats": galaxy_stats,
            "memory_by_id": memory_by_id,
            "memory_recent": memory_recent,
            "memory_search": memory_search,
            "substrate_health": substrate_health,
        }
    except ImportError:
        return None


def _unavailable(name: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "error": f"whitemagic.core.galactic not importable — {name} cannot run",
    }


# ─── Public bridge functions ──────────────────────────────────────


def galactic_galaxy_stats(**kwargs: Any) -> dict[str, Any]:
    """Substrate-wide statistics: total memories, associations, embeddings.

    Returns counts, zone distribution (CORE / INNER_RIM / MID_BAND /
    OUTER_RIM / FAR_EDGE), type distribution, averages, oldest/newest
    memory timestamps, and sweep duration.

    Use to answer questions like "how much data does the substrate have?"
    or "is the substrate alive?". Used by the A2A agent card and the
    librarian's status endpoint.
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_galaxy_stats")
    try:
        stats = api["galaxy_stats"]()
        return {
            "status": "ok",
            "function": "galactic_galaxy_stats",
            "result": stats.to_dict(),
        }
    except FileNotFoundError as e:
        return {"status": "unavailable", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_memory_recent(limit: int = 10, memory_type: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Most recently updated memories, optionally filtered by type.

    Args:
        limit: max number of memories to return (default 10, max 200)
        memory_type: filter to "SHORT_TERM" / "LONG_TERM" / "WORKING" (optional)

    Returns a list of memory dicts (id, title, content, type, etc.).
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_memory_recent")
    try:
        mems = api["memory_recent"](limit=int(limit), memory_type=memory_type)
        return {
            "status": "ok",
            "function": "galactic_memory_recent",
            "result": {
                "count": len(mems),
                "memories": [m.to_dict() for m in mems],
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_memory_search(query: str, limit: int = 10, memory_type: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """FTS5 search across memory content, with LIKE fallback.

    Returns a list of matching memories ranked by relevance.
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_memory_search")
    try:
        results = api["memory_search"](query=query, limit=int(limit), memory_type=memory_type)
        return {
            "status": "ok",
            "function": "galactic_memory_search",
            "result": {
                "query": query,
                "count": len(results),
                "memories": [m.to_dict() for m in results],
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_memory_by_id(memory_id: str, **kwargs: Any) -> dict[str, Any]:
    """Look up a single memory by its substrate id (16-char hex)."""
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_memory_by_id")
    try:
        mem = api["memory_by_id"](memory_id)
        if mem is None:
            return {
                "status": "not_found",
                "function": "galactic_memory_by_id",
                "memory_id": memory_id,
            }
        return {
            "status": "ok",
            "function": "galactic_memory_by_id",
            "result": mem.to_dict(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_associations(memory_id: str, direction: str = "outgoing", limit: int = 25, **kwargs: Any) -> dict[str, Any]:
    """Return associations touching a memory (with the other endpoint).

    Args:
        memory_id: 16-char hex memory id
        direction: "outgoing" / "incoming" / "both" (default "outgoing")
        limit: max associations to return (default 25, max 200)
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_associations")
    try:
        assocs = api["associations_for"](
            memory_id, direction=direction, limit=int(limit)
        )
        return {
            "status": "ok",
            "function": "galactic_associations",
            "result": {
                "memory_id": memory_id,
                "direction": direction,
                "count": len(assocs),
                "associations": assocs,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_event_search(
    query: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    limit: int = 25,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the dharma_audit table (substrate ethics + event log).

    After v23.0.0-alpha.1 rehydration, the dharma_audit table holds:
        - 35,053 rows migrated from Whitemagic-Core (2025-11 to 2025-12)
            - events.jsonl (narrator events: voice_expressed, memory_created, etc.)
            - resonance_history.jsonl (resonance field activations)
            - depth_gauge.jsonl (dream layer compression events)
            - health_checks.jsonl (coherence 0.6 -> 0.8 self-monitoring)
            - audit/*.jsonl (CLI command history)
        - rows from live dharma boundary checks (current era)

    Args:
        query: text to search in action/context/concerns
        event_type: filter by boundary_type (e.g., "voice_expressed",
                    "memory_created", "cli_command", "release", "destructive")
        since: ISO timestamp; only events at or after this time
        limit: max events to return (default 25, max 200)
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_event_search")
    try:
        results = api["event_search"](
            query=query, event_type=event_type, since=since, limit=int(limit)
        )
        return {
            "status": "ok",
            "function": "galactic_event_search",
            "result": {
                "query": query,
                "event_type": event_type,
                "since": since,
                "count": len(results),
                "events": results,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_substrate_health(**kwargs: Any) -> dict[str, Any]:
    """Health check: is the substrate alive? What does it contain?

    Returns db path, size, total memories/associations/embeddings/
    dharma_audits/constellations/akashic_seeds, and a status string
    ("alive" / "missing" / "error"). Used by /api/librarian/status and
    the A2A agent card posture.
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_substrate_health")
    try:
        return api["substrate_health"]()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def galactic_constellation_count(**kwargs: Any) -> dict[str, Any]:
    """Number of HDBSCAN-detected constellations in the substrate.

    The v17 era had 30 constellations; the current substrate is
    pre-HDBSCAN, so this typically returns 0. The function is wired
    for the day we re-run constellation detection.
    """
    api = _get_galactic()
    if api is None:
        return _unavailable("galactic_constellation_count")
    try:
        n = api["constellation_count"]()
        return {
            "status": "ok",
            "function": "galactic_constellation_count",
            "result": {"constellations": n},
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
