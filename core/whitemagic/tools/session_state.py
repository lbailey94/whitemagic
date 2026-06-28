"""Session state tracking for sensorium injection.

Provides session start time and basic session-level metrics
that the sensorium injects into PRAT responses.
"""

from __future__ import annotations

import time

_session_start: float | None = None


def get_session_start_time() -> float | None:
    """Get the timestamp when the current session started."""
    return _session_start


def ensure_session_started() -> float:
    """Ensure the session start time is set. Returns the start time."""
    global _session_start
    if _session_start is None:
        _session_start = time.time()
    return _session_start


def reset_session() -> None:
    """Reset the session start time (for testing)."""
    global _session_start
    _session_start = None
