"""whitemagic.compat.galaxy — Legacy galaxy adapter.

Provides backward-compatible access to deprecated galaxy operations:
- switch_galaxy() → use galaxy.use (request-scoped, no global mutation)
"""
from __future__ import annotations

from typing import Any

from whitemagic.compat import _deprecated


def switch_galaxy(name: str, **kwargs: Any) -> dict[str, Any]:
    """Deprecated: Switch the active galaxy (mutates global state).

    Migration: Use the `galaxy.use` tool instead, which provides
    request-scoped access without mutating process-global state.

    .. deprecated:: 24.3.0
        Use ``galaxy.use`` instead. Will be removed in v25.0.0.
    """
    _deprecated(
        "whitemagic.compat.galaxy.switch_galaxy",
        "galaxy.use (request-scoped, no global mutation)",
    )
    from whitemagic.tools.handlers.galaxy import handle_galaxy_switch

    return handle_galaxy_switch(name=name, **kwargs)


__all__ = ["switch_galaxy"]
