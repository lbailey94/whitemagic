#!/usr/bin/env python3
"""Compatibility shim — re-exports the lean MCP server.

The historical module ``whitemagic.run_mcp`` was replaced by
``whitemagic.run_mcp_lean`` in v22.0.0. This shim preserves backward
compatibility for documented entrypoints, CLI scaffolding, and tests.
New code should import from ``whitemagic.run_mcp_lean`` directly.
"""
from __future__ import annotations

from whitemagic.run_mcp_lean import *  # noqa: F401,F403

# Explicit re-exports of symbols that are actually available
from whitemagic.run_mcp_lean import (  # noqa: F401
    main,
    server,
)

# Backward compat: tests expect `mcp`
mcp = server

# Backward compat: historical entrypoints expected by omega_test and CI
register_tools = lambda: None  # noqa: E731
register_resources = lambda: None  # noqa: E731


class _LifecycleShim:
    """Graceful fallback for historical lifecycle API."""

    @staticmethod
    def startup() -> None:
        """No-op startup for backward compatibility."""
        return None

    @staticmethod
    def shutdown() -> None:
        """No-op shutdown for backward compatibility."""
        return None


lifecycle = _LifecycleShim()


if __name__ == "__main__":
    # `python -m whitemagic.run_mcp` must still launch the server.
    main()
