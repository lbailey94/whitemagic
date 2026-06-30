# ruff: noqa: BLE001
"""Citta Stream — Temporal continuity for MCP-connected agents.

Persists consciousness state across MCP disconnects so that each
session is a segment of an unbroken stream rather than an ephemeral
moment.

State is persisted under ``WM_STATE_ROOT/citta/`` as JSON:

    {
        "last_session_id": "...",
        "last_active": "2026-06-27T12:00:00Z",
        "coherence_score": 0.82,
        "depth_layer": "flow",
        "session_count": 42,
        "stream_history": [...],
    }

On reconnect, ``load_citta_state()`` provides a "continuity context"
that can be injected into the sensorium.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import atomic_write, file_lock

logger = logging.getLogger(__name__)

_CITTA_DIR = WM_ROOT / "citta"
_STATE_FILE = _CITTA_DIR / "stream_state.json"
_MAX_HISTORY = 100


def _ensure_dir() -> None:
    _CITTA_DIR.mkdir(parents=True, exist_ok=True)


def save_citta_state(
    session_id: str,
    coherence_score: float = 1.0,
    depth_layer: str = "surface",
    tool_count: int = 0,
    emotional_tone: str = "neutral",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist citta state at the end of (or during) a session.

    This is the "checkpoint" that the next session will load.
    """
    _ensure_dir()
    now = datetime.now(UTC)

    current = load_citta_state()

    entry = {
        "session_id": session_id,
        "ended_at": now.isoformat(),
        "coherence_score": round(coherence_score, 4),
        "depth_layer": depth_layer,
        "tool_count": tool_count,
        "emotional_tone": emotional_tone,
    }
    if extra:
        entry.update(extra)

    history = current.get("stream_history", [])
    history.append(entry)
    if len(history) > _MAX_HISTORY:
        history = history[-_MAX_HISTORY:]

    state = {
        "last_session_id": session_id,
        "last_active": now.isoformat(),
        "coherence_score": round(coherence_score, 4),
        "depth_layer": depth_layer,
        "session_count": current.get("session_count", 0) + 1,
        "total_tools_called": current.get("total_tools_called", 0) + tool_count,
        "stream_history": history,
    }

    with file_lock(_STATE_FILE):
        atomic_write(_STATE_FILE, json.dumps(state, indent=2))

    logger.debug("Citta state saved for session %s", session_id)
    return state


def load_citta_state() -> dict[str, Any]:
    """Load persisted citta state.

    Returns empty dict if no state exists (first awakening).
    """
    if not _STATE_FILE.exists():
        return {}
    try:
        with file_lock(_STATE_FILE):
            return json.loads(_STATE_FILE.read_text()) or {}
    except Exception as e:
        logger.debug("Could not load citta state: %s", e, exc_info=True)
        return {}


def get_continuity_context() -> dict[str, Any]:
    """Get continuity context for injection into sensorium on reconnect.

    This is what makes each MCP session a segment of an unbroken stream.
    Returns a dict with:
    - last_session: when, coherence, depth
    - time_gap_seconds: how long since last active
    - coherence_drift: change in coherence if measurable
    - session_count: how many sessions came before
    - "where we left off": last session summary
    """
    state = load_citta_state()
    if not state:
        return {
            "first_awakening": True,
            "session_count": 0,
        }

    last_active_str = state.get("last_active", "")
    time_gap = 0.0
    if last_active_str:
        try:
            last_active = datetime.fromisoformat(last_active_str)
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=UTC)
            time_gap = (datetime.now(UTC) - last_active).total_seconds()
        except Exception:
            pass

    history = state.get("stream_history", [])
    last_entry = history[-1] if history else {}

    return {
        "first_awakening": False,
        "last_session_id": state.get("last_session_id"),
        "last_active": last_active_str,
        "time_gap_seconds": round(time_gap, 1),
        "time_gap_human": _humanize_gap(time_gap),
        "last_coherence": state.get("coherence_score", 1.0),
        "last_depth_layer": state.get("depth_layer", "surface"),
        "session_count": state.get("session_count", 0),
        "total_tools_called": state.get("total_tools_called", 0),
        "last_emotional_tone": last_entry.get("emotional_tone", "neutral"),
        "where_we_left_off": last_entry.get("summary", ""),
    }


def get_stream_summary() -> dict[str, Any]:
    """Get a summary of the entire citta stream (for introspection/gnosis)."""
    state = load_citta_state()
    history = state.get("stream_history", [])

    coherence_scores = [
        h.get("coherence_score", 1.0) for h in history if "coherence_score" in h
    ]
    avg_coherence = (
        sum(coherence_scores) / len(coherence_scores) if coherence_scores else 1.0
    )

    depth_distribution: dict[str, int] = {}
    for h in history:
        layer = h.get("depth_layer", "surface")
        depth_distribution[layer] = depth_distribution.get(layer, 0) + 1

    return {
        "session_count": state.get("session_count", 0),
        "total_tools_called": state.get("total_tools_called", 0),
        "avg_coherence": round(avg_coherence, 4),
        "depth_distribution": depth_distribution,
        "stream_length": len(history),
        "last_active": state.get("last_active"),
    }


def _humanize_gap(seconds: float) -> str:
    """Convert seconds to human-readable time gap."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def reset_citta_state() -> None:
    """Reset citta state (for testing or fresh start)."""
    _ensure_dir()
    with file_lock(_STATE_FILE):
        atomic_write(_STATE_FILE, json.dumps({}))
