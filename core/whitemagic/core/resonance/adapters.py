"""Adapters — Shim Module (Removed during consolidation).

This module was removed in Milestone 4.3 Singleton Reduction.
Adapters are no longer needed in the unified resonance subsystem.
"""

import warnings

warnings.warn(
    "whitemagic.core.resonance.adapters was removed during consolidation. "
    "Adapters are no longer needed in the unified resonance subsystem.",
    DeprecationWarning,
    stacklevel=2,
)

# Stub for backward compatibility
def setup_all_adapters():
    """Deprecated: Adapters are no longer needed in the unified resonance subsystem."""
    warnings.warn(
        "setup_all_adapters() is deprecated. No adapters are needed in the unified system.",
        DeprecationWarning,
        stacklevel=2,
    )
    pass

__all__ = ["setup_all_adapters"]
