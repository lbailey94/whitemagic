"""Redis Bridge — Shim Module (Removed during consolidation).

This module was removed in Milestone 4.3 Singleton Reduction.
Redis bridging is now handled by the whitemagic.mesh subsystem.
"""

import warnings

warnings.warn(
    "whitemagic.core.resonance.redis_bridge was removed during consolidation. "
    "Redis bridging is now handled by whitemagic.mesh subsystem.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = []
