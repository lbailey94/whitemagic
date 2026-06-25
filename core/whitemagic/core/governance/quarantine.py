"""Quarantine Manager — Session isolation for hallucinated or suspicious activity.

When the Voice Audit scanner detects unverified claims (hallucinated tool
invocations), the Quarantine Manager isolates the associated session for
human review.

Usage:
    from whitemagic.core.governance.quarantine import get_quarantine_manager
    qm = get_quarantine_manager()
    qm.quarantine_session("session_abc", reason="Hallucinated delete_memory claim")
    status = qm.status()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QuarantineEntry:
    """QuarantineEntry: quarantine entry.

    Value object: equality and repr are field-based."""
    session_id: str
    reason: str
    quarantined_at: datetime
    source: str = "voice_audit"
    reviewed: bool = False
    review_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "session_id": self.session_id,
            "reason": self.reason,
            "quarantined_at": self.quarantined_at.isoformat(),
            "source": self.source,
            "reviewed": self.reviewed,
            "review_notes": self.review_notes,
        }


class QuarantineManager:
    """Manages a list of quarantined sessions."""

    def __init__(self, auto_expire_hours: int = 168) -> None:
        self._entries: dict[str, QuarantineEntry] = {}
        self._lock = threading.Lock()
        self._auto_expire = timedelta(hours=auto_expire_hours)

    def quarantine_session(
        self,
        session_id: str,
        reason: str,
        source: str = "voice_audit",
    ) -> QuarantineEntry:
        """Quarantine a session. Idempotent if already quarantined."""
        with self._lock:
            if session_id in self._entries:
                entry = self._entries[session_id]
                entry.reason += f" | additional: {reason}"
                logger.info("Updated quarantine for %s: %s", session_id, reason)
                return entry
            entry = QuarantineEntry(
                session_id=session_id,
                reason=reason,
                quarantined_at=datetime.now(UTC),
                source=source,
            )
            self._entries[session_id] = entry
            logger.warning("Session quarantined: %s — %s", session_id, reason)
            return entry

    def release_session(self, session_id: str, review_notes: str = "") -> bool:
        """Release a session from quarantine (mark reviewed)."""
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return False
            entry.reviewed = True
            entry.review_notes = review_notes
            logger.info("Session released from quarantine: %s", session_id)
            return True

    def remove_session(self, session_id: str) -> bool:
        """Permanently remove a quarantine entry."""
        with self._lock:
            if session_id in self._entries:
                del self._entries[session_id]
                return True
            return False

    def list_quarantined(self, include_reviewed: bool = False) -> list[dict[str, Any]]:
        """List quarantined sessions."""
        with self._lock:
            self._prune_expired()
            results = []
            for entry in self._entries.values():
                if not include_reviewed and entry.reviewed:
                    continue
                results.append(entry.to_dict())
            return sorted(results, key=lambda x: x["quarantined_at"], reverse=True)

    def is_quarantined(self, session_id: str) -> bool:
        """
        Check whether the quarantined condition holds.

        Args:
            session_id: Parameter description.

        Returns:
            bool
        """
        with self._lock:
            self._prune_expired()
            entry = self._entries.get(session_id)
            if entry is None:
                return False
            return not entry.reviewed

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.

        Returns:
            dict[str, Any]
        """
        with self._lock:
            self._prune_expired()
            active = [e for e in self._entries.values() if not e.reviewed]
            reviewed = [e for e in self._entries.values() if e.reviewed]
            return {
                "active_quarantines": len(active),
                "reviewed_quarantines": len(reviewed),
                "total_entries": len(self._entries),
                "auto_expire_hours": self._auto_expire.total_seconds() / 3600,
            }

    def _prune_expired(self) -> None:
        cutoff = datetime.now(UTC) - self._auto_expire
        expired = [sid for sid, e in self._entries.items() if e.quarantined_at < cutoff]
        for sid in expired:
            del self._entries[sid]
            logger.info("Quarantine entry expired and removed: %s", sid)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_qm_instance: QuarantineManager | None = None
_qm_lock = threading.Lock()


def get_quarantine_manager() -> QuarantineManager:
    """Get the global QuarantineManager singleton."""
    global _qm_instance
    if _qm_instance is None:
        with _qm_lock:
            if _qm_instance is None:
                _qm_instance = QuarantineManager()
    return _qm_instance
