"""
Session Manager - Work Session State Management

Manages work sessions with full lifecycle support including creation,
checkpointing, resuming, and metrics tracking.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class SessionStatus(Enum):
    """Session lifecycle status."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Session:
    """Represents a work session."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    status: SessionStatus = SessionStatus.ACTIVE

    # Goals and context
    goals: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    context_tier: int = 1

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    # Progress tracking
    metrics: Dict[str, Any] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)

    # Settings
    auto_checkpoint: bool = True
    checkpoint_interval: int = 1800  # 30 minutes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {**asdict(self), "status": self.status.value}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        data = data.copy()
        if "status" in data:
            data["status"] = SessionStatus(data["status"])
        return cls(**data)


class SessionManager:
    """
    Manages work sessions with full lifecycle support.

    Handles session creation, updates, checkpointing, and resuming.
    Stores session data in JSON files for persistence.
    """

    def __init__(self, base_dir: Path = None):
        """
        Initialize session manager.

        Args:
            base_dir: Base directory for session storage
        """
        self.base_dir = base_dir or Path.home() / ".whitemagic" / "sessions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Active sessions cache
        self._active_sessions: Dict[str, Session] = {}

    def _session_path(self, session_id: str) -> Path:
        """Get path to session file."""
        return self.base_dir / f"{session_id}.json"

    async def create_session(
        self,
        name: str,
        goals: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        context_tier: int = 1,
        auto_checkpoint: bool = True,
    ) -> Session:
        """
        Create new work session.

        Args:
            name: Session name
            goals: Session goals/objectives
            tags: Session tags
            context_tier: Initial context loading tier
            auto_checkpoint: Enable automatic checkpointing

        Returns:
            Created Session object
        """
        session = Session(
            name=name,
            goals=goals or [],
            tags=tags or [],
            context_tier=context_tier,
            auto_checkpoint=auto_checkpoint,
        )

        # Save to disk
        await self._save_session(session)

        # Cache
        self._active_sessions[session.id] = session

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session object or None
        """
        # Check cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Load from disk
        session_path = self._session_path(session_id)
        if not session_path.exists():
            return None

        try:
            data = json.loads(session_path.read_text())
            session = Session.from_dict(data)
            self._active_sessions[session_id] = session
            return session
        except Exception:
            return None

    async def update_session(self, session_id: str, **updates) -> Optional[Session]:
        """
        Update session fields.

        Args:
            session_id: Session ID
            **updates: Fields to update

        Returns:
            Updated session or None
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.updated_at = datetime.utcnow().isoformat()

        # Save
        await self._save_session(session)

        return session

    async def list_sessions(
        self, status: Optional[SessionStatus] = None, limit: int = 20
    ) -> List[Session]:
        """
        List sessions with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum sessions to return

        Returns:
            List of sessions
        """
        sessions = []

        # Load all session files
        for session_file in self.base_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                session = Session.from_dict(data)

                if status and session.status != status:
                    continue

                sessions.append(session)
            except Exception:
                continue

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        return sessions[:limit]

    async def end_session(self, session_id: str, create_summary: bool = True) -> Optional[Session]:
        """
        End a session.

        Args:
            session_id: Session ID
            create_summary: Create summary memory

        Returns:
            Completed session or None
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow().isoformat()
        session.updated_at = session.completed_at

        # Save
        await self._save_session(session)

        # Remove from cache
        self._active_sessions.pop(session_id, None)

        return session

    async def _save_session(self, session: Session) -> None:
        """Save session to disk."""
        session_path = self._session_path(session.id)
        session_path.write_text(json.dumps(session.to_dict(), indent=2))
