"""whitemagic.compat.resonance — Legacy resonance adapters.

Provides backward-compatible imports for deprecated resonance modules:
- gan_ying → whitemagic.core.resonance.get_bus()
- gan_ying_enhanced → whitemagic.core.resonance.get_bus()
- harmony_vector → whitemagic.harmony.vector.get_harmony_vector()
- adapters → (removed, no replacement needed)
- temporal_scheduler → whitemagic.core.resonance.get_bus()
- integration_helpers → whitemagic.core.resonance.get_bus()
- redis_bridge → whitemagic.mesh
"""
from __future__ import annotations

from typing import Any

from whitemagic.compat import _deprecated


def get_gan_ying_bus() -> Any:
    """Deprecated: Get the GanYing bus.

    Migration: Use ``from whitemagic.core.resonance import get_bus`` directly.

    .. deprecated:: 24.3.0
        Use ``whitemagic.core.resonance.get_bus()`` instead.
    """
    _deprecated(
        "whitemagic.compat.resonance.get_gan_ying_bus",
        "whitemagic.core.resonance.get_bus()",
    )
    from whitemagic.core.resonance import get_bus

    return get_bus()


def get_harmony_vector() -> Any:
    """Deprecated: Get the harmony vector.

    Migration: Use ``from whitemagic.harmony.vector import get_harmony_vector``.

    .. deprecated:: 24.3.0
        Use ``whitemagic.harmony.vector.get_harmony_vector()`` instead.
    """
    _deprecated(
        "whitemagic.compat.resonance.get_harmony_vector",
        "whitemagic.harmony.vector.get_harmony_vector()",
    )
    from whitemagic.harmony.vector import get_harmony_vector

    return get_harmony_vector()


__all__ = ["get_gan_ying_bus", "get_harmony_vector"]
