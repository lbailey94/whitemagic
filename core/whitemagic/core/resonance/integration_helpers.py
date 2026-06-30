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


# Backward-compatibility mixin that delegates to the real GanYingBus
class GanYingMixin:
    """Deprecated: Use whitemagic.core.resonance.get_bus() directly.

    Kept functional for gardens/sangha and other downstream code that
    inherits from this mixin and calls self.emit() / self.listen().
    """

    def __init__(self):
        warnings.warn(
            "GanYingMixin is deprecated. Use whitemagic.core.resonance.get_bus() directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._gan_ying_bus = get_bus()

    def emit(self, event_type, data=None, **kwargs):
        """Emit a resonance event via the global bus."""
        from whitemagic.core.resonance import ResonanceEvent

        if data is None:
            data = kwargs.get("data", {})
        source = kwargs.get("source", getattr(self, "__class__", type(self)).__name__)
        self._gan_ying_bus.emit(
            ResonanceEvent(source=source, event_type=event_type, data=data)
        )

    def listen(self, event_type, callback):
        """Register a listener on the global bus."""
        self._gan_ying_bus.listen(event_type, callback)


def init_listeners(instance):
    """Deprecated: Use whitemagic.core.resonance.get_bus().listen() directly.

    Kept functional for gardens that call init_listeners(self) in __init__.
    """
    warnings.warn(
        "init_listeners() is deprecated. Use whitemagic.core.resonance.get_bus().listen() directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Wire the bus onto the instance so self.emit() works
    instance._gan_ying_bus = get_bus()


def listen_for(event_type):
    """Deprecated: Use whitemagic.core.resonance.get_bus().listen() directly.

    Kept functional for decorators on garden methods.
    """
    warnings.warn(
        "listen_for() is deprecated. Use whitemagic.core.resonance.get_bus().listen() directly.",
        DeprecationWarning,
        stacklevel=2,
    )

    def decorator(callback):
        """
        Perform the decorator operation.

        Args:
            callback: Parameter description.
        """
        return get_bus().listen(event_type, callback)

    return decorator


__all__ = ["GanYingMixin", "init_listeners", "listen_for"]
