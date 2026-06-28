"""Top-level session facade (Group B — fresh implementation).

Provides a high-level API for session management, building on
whitemagic.sessions.manager.SessionManager.
"""

from __future__ import annotations

from typing import Any

from whitemagic.session.manager import Session, SessionManager


def get_active_session() -> Session | None:
    """Return the currently active session, or None."""
    return SessionManager().get_active_session()


def list_sessions(limit: int = 10) -> list[Session]:
    """List recent sessions, most recent first."""
    return SessionManager().list_sessions(limit=limit)


def get_session_manifest() -> dict[str, Any] | None:
    """Return the active session as a manifest dict, or None."""
    session = get_active_session()
    if session is None:
        return None
    return session.to_dict()


__all__ = ["get_active_session", "list_sessions", "get_session_manifest", "Session"]
