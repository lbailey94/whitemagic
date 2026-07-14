# ruff: noqa: BLE001
"""Gana Bridge — PRAT meta-tool invocation bridge.

This module provides `gana_invoke()`, the bridge function called by
the dispatch pipeline when a tool name starts with `gana_`.

It delegates to `prat_router.route_prat_call()` which handles:
- Resonance context building
- Wu Xing quadrant boost
- Garden integration
- Tool validation (ensures sub-tool belongs to Gana)
- Zig dispatch pre-check
- Result normalization with _resonance metadata
"""

from typing import Any


def gana_invoke(
    tool_name: str, args: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Invoke a Gana meta-tool through the PRAT router.

    Args:
        tool_name: The Gana name, e.g. "gana_ghost"
        args: Arguments dict, typically contains `tool` and `args` keys
        **kwargs: Additional kwargs passed through

    Returns:
        A normalized result dict with _resonance metadata.
    """
    from whitemagic.tools.prat_router import route_prat_call

    _args = args or {}

    # The PRAT router expects the sub-tool name in `tool=` and its args in `args=`
    sub_tool = _args.pop("tool", None)
    sub_args = _args.pop("args", {}) or {}

    # Merge any remaining top-level args into sub_args for convenience
    if _args:
        sub_args.update(_args)

    return route_prat_call(
        gana_name=tool_name,
        tool=sub_tool,
        args=sub_args,
        **kwargs,
    )
