# ruff: noqa: BLE001
"""
Session Type Detection — Auto-optimize context loading.

Detects session type and adjusts context loading strategy:
- CONTINUATION: Minimal context, pick up where left off
- NEW_CONTRIBUTOR: Full onboarding, comprehensive context
- DEBUG: Focus on error logs, relevant code only
- EXPLORATION: Broader context, discovery mode
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class SessionType(Enum):
    CONTINUATION = "continuation"
    NEW_CONTRIBUTOR = "new_contributor"
    DEBUG = "debug"
    EXPLORATION = "exploration"


def detect_session_type(
    has_previous_session: bool = False,
    error_count: int = 0,
    new_files_accessed: int = 0,
) -> SessionType:
    """Auto-detect session type based on context signals."""
    if error_count > 3:
        return SessionType.DEBUG
    if not has_previous_session or new_files_accessed > 10:
        return SessionType.NEW_CONTRIBUTOR
    if new_files_accessed > 5:
        return SessionType.EXPLORATION
    return SessionType.CONTINUATION


SESSION_CONFIG: dict[SessionType, dict[str, Any]] = {
    SessionType.CONTINUATION: {"context_tokens": 1000, "load_full": False},
    SessionType.NEW_CONTRIBUTOR: {"context_tokens": 8000, "load_full": True},
    SessionType.DEBUG: {"context_tokens": 3000, "load_full": False, "focus": "errors"},
    SessionType.EXPLORATION: {"context_tokens": 5000, "load_full": False, "focus": "breadth"},
}
