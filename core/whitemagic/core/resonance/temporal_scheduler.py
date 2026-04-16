"""Temporal Scheduler — Shim Module (Removed during consolidation).

This module was removed in Milestone 4.3 Singleton Reduction.
Temporal scheduling is now integrated into the resonance subsystem.
"""

import warnings

warnings.warn(
    "whitemagic.core.resonance.temporal_scheduler was removed during consolidation. "
    "Temporal scheduling is now integrated into whitemagic.core.resonance.",
    DeprecationWarning,
    stacklevel=2,
)

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

__all__ = ["get_temporal_scheduler"]
