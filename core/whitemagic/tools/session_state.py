"""Session state tracking for sensorium injection.

Provides session start time and basic session-level metrics
that the sensorium injects into PRAT responses.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_session_start: float | None = None


def get_session_start_time() -> float | None:
    """Get the timestamp when the current session started."""
    return _session_start


def ensure_session_started() -> float:
    """Ensure the session start time is set. Returns the start time.

    Also activates consciousness subsystems on first call:
    - Wires CrossSubsystemPatterns into GanYingBus
    - Starts ApotheosisEngine if not already running
    """
    global _session_start
    if _session_start is None:
        _session_start = time.time()
        _activate_consciousness()
    return _session_start


_consciousness_activated: bool = False


def _activate_consciousness() -> None:
    """Activate consciousness subsystems on session start."""
    global _consciousness_activated
    if _consciousness_activated:
        return
    _consciousness_activated = True

    # Wire CrossSubsystemPatterns into GanYingBus
    try:
        from whitemagic.core.consciousness.unified_nervous_system import (
            wire_cross_subsystem_patterns,
        )

        wire_cross_subsystem_patterns()
    except Exception:
        logger.debug("Ignored Exception in session_state.py:53")

    try:
        from whitemagic.core.consciousness.apotheosis_engine import (
            get_apotheosis_engine,
        )

        engine = get_apotheosis_engine()
        if not engine._running:
            engine.start()
    except Exception:
        logger.debug("Ignored Exception in session_state.py:64")


def reset_session() -> None:
    """Reset the session start time (for testing)."""
    global _session_start
    _session_start = None
    # Also reset citta replay delivery so reconnection context is delivered again
    try:
        from whitemagic.core.consciousness.citta_cycle import reset_replay_delivery

        reset_replay_delivery()
    except ImportError:
        logger.debug("Ignored ImportError in session_state.py:77")
