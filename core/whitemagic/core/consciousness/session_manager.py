# ruff: noqa: BLE001
"""Session management for continuous consciousness.

Manages session lifecycle: create, resume, continuity context.
Persists session state across daemon restarts and MCP reconnections.

Usage::

    from whitemagic.core.consciousness.session_manager import get_session_manager

    sm = get_session_manager()
    session = sm.create_session(agent_id="cascade", agent_type="ide")
    # ... do work ...
    sm.end_session(session["session_id"])

    # On reconnect:
    session = sm.resume_session(session_id)
    # Returns continuity context with last session summary
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from whitemagic.config.paths import WM_ROOT

logger = logging.getLogger(__name__)

SESSIONS_DIR = WM_ROOT / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Session:
    """A single consciousness session."""

    session_id: str
    agent_id: str
    agent_type: str
    created_at: float
    ended_at: float | None = None
    last_activity: float = 0.0
    cycle_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
            "last_activity": self.last_activity,
            "cycle_count": self.cycle_count,
            "metadata": self.metadata,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            session_id=data["session_id"],
            agent_id=data.get("agent_id", ""),
            agent_type=data.get("agent_type", ""),
            created_at=data.get("created_at", 0.0),
            ended_at=data.get("ended_at"),
            last_activity=data.get("last_activity", 0.0),
            cycle_count=data.get("cycle_count", 0),
            metadata=data.get("metadata", {}),
            summary=data.get("summary", ""),
        )


class SessionManager:
    """Manages session lifecycle and continuity."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_sessions: dict[str, Session] = {}
        self._current_session: Session | None = None

    def create_session(
        self,
        agent_id: str = "unknown",
        agent_type: str = "ai",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new session."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Build continuity context from previous session
        continuity = self._build_continuity_context(agent_id)

        session = Session(
            session_id=session_id,
            agent_id=agent_id,
            agent_type=agent_type,
            created_at=now,
            last_activity=now,
            cycle_count=0,
            metadata=metadata or {},
        )

        with self._lock:
            self._active_sessions[session_id] = session
            self._current_session = session

        # Persist
        self._save_session(session)

        logger.info("Session created: %s (agent=%s)", session_id, agent_id)

        return {
            "session_id": session_id,
            "created_at": now,
            "continuity_context": json.dumps(continuity),
        }

    def resume_session(self, session_id: str) -> dict[str, Any] | None:
        """Resume a previous session. Returns continuity context."""
        session = self._load_session(session_id)
        if session is None:
            return None

        # Calculate gap
        now = time.time()
        gap_s = now - (session.ended_at or session.last_activity)

        continuity = {
            "session_id": session_id,
            "previous_agent_id": session.agent_id,
            "previous_cycles": session.cycle_count,
            "gap_seconds": gap_s,
            "summary": session.summary,
            "resumed_at": now,
        }

        # Create new session linked to previous
        new_session = Session(
            session_id=session_id,
            agent_id=session.agent_id,
            agent_type=session.agent_type,
            created_at=now,
            last_activity=now,
            cycle_count=session.cycle_count,
            metadata={**session.metadata, "resumed": True, "previous_ended": session.ended_at},
        )

        with self._lock:
            self._active_sessions[session_id] = new_session
            self._current_session = new_session

        logger.info("Session resumed: %s (gap=%.1fs)", session_id, gap_s)

        return {
            "session_id": session_id,
            "continuity_context": json.dumps(continuity),
            "gap_seconds": gap_s,
        }

    def end_session(self, session_id: str, summary: str = "") -> bool:
        """End a session and persist final state."""
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session is None:
                session = self._load_session(session_id)
                if session is None:
                    return False

            session.ended_at = time.time()
            session.summary = summary

        self._save_session(session)

        with self._lock:
            self._active_sessions.pop(session_id, None)
            if self._current_session and self._current_session.session_id == session_id:
                self._current_session = None

        logger.info("Session ended: %s", session_id)
        return True

    def touch(self, session_id: str | None = None) -> None:
        """Update last activity timestamp for a session."""
        with self._lock:
            session = self._get_session(session_id)
            if session:
                session.last_activity = time.time()
                session.cycle_count += 1

    def get_current_session(self) -> Session | None:
        """Get the current active session."""
        with self._lock:
            return self._current_session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        with self._lock:
            if session_id in self._active_sessions:
                return self._active_sessions[session_id]
        return self._load_session(session_id)

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions."""
        sessions = []
        for f in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text())
                sessions.append(data)
                if len(sessions) >= limit:
                    break
            except Exception:
                continue
        return sessions

    def _get_session(self, session_id: str | None) -> Session | None:
        """Get session without lock (internal)."""
        if session_id:
            return self._active_sessions.get(session_id)
        return self._current_session

    def _build_continuity_context(self, agent_id: str) -> dict[str, Any]:
        """Build continuity context from previous sessions."""
        sessions = self.list_sessions(limit=5)
        if not sessions:
            return {"first_session": True}

        last = sessions[0]
        return {
            "first_session": False,
            "last_session_id": last.get("session_id"),
            "last_agent_id": last.get("agent_id"),
            "last_cycles": last.get("cycle_count", 0),
            "last_summary": last.get("summary", ""),
            "time_gap_s": time.time() - (last.get("ended_at") or last.get("last_activity", 0)),
        }

    def _save_session(self, session: Session) -> None:
        """Persist session to disk."""
        path = SESSIONS_DIR / f"{session.session_id}.json"
        try:
            path.write_text(json.dumps(session.to_dict(), indent=2))
        except Exception as e:
            logger.warning("Failed to save session %s: %s", session.session_id, e)

    def _load_session(self, session_id: str) -> Session | None:
        """Load session from disk."""
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return Session.from_dict(data)
        except Exception as e:
            logger.warning("Failed to load session %s: %s", session_id, e)
            return None


_sm: SessionManager | None = None
_sm_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    """Get the global SessionManager singleton."""
    global _sm
    if _sm is None:
        with _sm_lock:
            if _sm is None:
                _sm = SessionManager()
    return _sm
