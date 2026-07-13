"""whitemagic.compat — Legacy compatibility adapters.

This package isolates deprecated entry points and legacy adapters so that:
1. Deprecation warnings are centralized and consistent
2. Migration paths are documented in one place
3. Legacy code can be removed in bulk at the next major version

Each adapter emits a DeprecationWarning with:
- The removal version (next major)
- The migration path (what to use instead)

Current legacy adapters:
- galaxy.switch → galaxy.use (request-scoped, no global mutation)
- whitemagic.parallel.runner → pytest-xdist
- whitemagic.core.resonance.gan_ying → whitemagic.core.resonance.get_bus()
- whitemagic.core.resonance.gan_ying_enhanced → whitemagic.core.resonance.get_bus()
- whitemagic.core.resonance.adapters → (removed, no replacement needed)
- whitemagic.core.resonance.harmony_vector → whitemagic.harmony.vector.get_harmony_vector()
- whitemagic.core.resonance.temporal_scheduler → whitemagic.core.resonance.get_bus()
- whitemagic.core.resonance.integration_helpers → whitemagic.core.resonance.get_bus()
- whitemagic.core.resonance.redis_bridge → whitemagic.mesh
- whitemagic.gardens.air → whitemagic.gardens.voice
- whitemagic.gardens.metal → whitemagic.gardens.practice
- whitemagic.gardens.gan_ying_wiring → (removed, gardens self-wire via GanYingMixin)
- whitemagic.core.immune.security_integration_recovered → whitemagic.core.immune.security_integration
"""
from __future__ import annotations

import warnings

_REMOVAL_VERSION = "25.0.0"


def _deprecated(
    old_name: str,
    new_name: str,
    *,
    removal_version: str = _REMOVAL_VERSION,
) -> None:
    """Emit a standardized deprecation warning.

    Args:
        old_name: The deprecated API path.
        new_name: The replacement API path (or "removed" if no replacement).
        removal_version: The version where this will be removed.
    """
    warnings.warn(
        f"{old_name} is deprecated and will be removed in v{removal_version}. "
        f"Use {new_name} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


__all__: list[str] = ["_deprecated"]
