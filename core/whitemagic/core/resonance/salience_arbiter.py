"""Salience Arbiter — Shim Module (Removed during consolidation).

This module was removed in Milestone 4.3 Singleton Reduction.
Salience arbitration is now integrated into the resonance subsystem.
"""

import warnings

warnings.warn(
    "whitemagic.core.resonance.salience_arbiter was removed during consolidation. "
    "Salience arbitration is now integrated into whitemagic.core.resonance.",
    DeprecationWarning,
    stacklevel=2,
)

# Stub for backward compatibility
def get_salience_arbiter():
    """Deprecated: Salience arbiter is now integrated into resonance subsystem."""
    warnings.warn(
        "get_salience_arbiter() is deprecated. "
        "Use whitemagic.core.resonance.get_bus() and the unified arbitration system.",
        DeprecationWarning,
        stacklevel=2,
    )
    return None

__all__ = ["get_salience_arbiter"]
