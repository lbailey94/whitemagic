"""Integration Helpers — Shim Module (Removed during consolidation).

This module was removed in Milestone 4.3 Singleton Reduction.
Integration helpers are now part of the unified resonance API.
"""

import warnings

from whitemagic.core.resonance import get_bus

warnings.warn(
    "whitemagic.core.resonance.integration_helpers was removed during consolidation. "
    "Use whitemagic.core.resonance.get_bus() and the unified API instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Stubs for backward compatibility
class GanYingMixin:
    """Deprecated: Use whitemagic.core.resonance.get_bus() directly."""
    def __init__(self):
        warnings.warn(
            "GanYingMixin is deprecated. Use whitemagic.core.resonance.get_bus() directly.",
            DeprecationWarning,
            stacklevel=2,
        )

def init_listeners():
    """Deprecated: Use whitemagic.core.resonance.get_bus().listen() directly."""
    warnings.warn(
        "init_listeners() is deprecated. Use whitemagic.core.resonance.get_bus().listen() directly.",
        DeprecationWarning,
        stacklevel=2,
    )

def listen_for(event_type, callback):
    """Deprecated: Use whitemagic.core.resonance.get_bus().listen() directly."""
    warnings.warn(
        "listen_for() is deprecated. Use whitemagic.core.resonance.get_bus().listen() directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_bus().listen(event_type, callback)

__all__ = ["GanYingMixin", "init_listeners", "listen_for"]
