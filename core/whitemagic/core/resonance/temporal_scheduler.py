"""Temporal Scheduler — Shim Module (Removed during consolidation).

This module was removed in Milestone 4.3 Singleton Reduction.
Temporal scheduling is now integrated into the resonance subsystem.
"""

import warnings
from enum import Enum

warnings.warn(
    "whitemagic.core.resonance.temporal_scheduler was removed during consolidation. "
    "Temporal scheduling is now integrated into whitemagic.core.resonance.",
    DeprecationWarning,
    stacklevel=2,
)


class TemporalLane(Enum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


# Event type to lane mapping
_EVENT_LANE_MAP = {
    "BROKER_DISCONNECTED": TemporalLane.FAST,
    "TASK_FAILED": TemporalLane.FAST,
    "AGENT_DEREGISTERED": TemporalLane.FAST,
    "VOTE_CONSENSUS_REACHED": TemporalLane.SLOW,
    "VOTE_SESSION_CLOSED": TemporalLane.SLOW,
    "TASK_CREATED": TemporalLane.MEDIUM,
    "BROKER_MESSAGE_PUBLISHED": TemporalLane.MEDIUM,
}


def classify_event(event_type) -> TemporalLane:
    """Classify an event type into a temporal lane."""
    name = getattr(event_type, "name", str(event_type))
    return _EVENT_LANE_MAP.get(name, TemporalLane.MEDIUM)


# Stub for backward compatibility
def get_temporal_scheduler():
    """Deprecated: Temporal scheduler is now integrated into resonance subsystem."""
    warnings.warn(
        "get_temporal_scheduler() is deprecated. "
        "Use whitemagic.core.resonance.get_bus() and the unified scheduling system.",
        DeprecationWarning,
        stacklevel=2,
    )
    return None


__all__ = ["get_temporal_scheduler", "TemporalLane", "classify_event"]
