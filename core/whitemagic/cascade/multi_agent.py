# ruff: noqa: F403
"""Cascade Multi-Agent (Archived)
==============================

This module enabled multi-agent collaboration driven by embedded local models.

The implementation has been archived and is no longer available.
"""

from __future__ import annotations

from typing import Any


def _disabled_error() -> RuntimeError:
    return RuntimeError(
        "Multi-agent local-model support is archived and no longer available."
    )


class LocalModelAgent:  # pragma: no cover - legacy shim
    """LocalModelAgent: local model agent."""

    def __init__(self, *_: Any, **__: Any) -> None:
        raise _disabled_error()


async def create_agent_team(*_: Any, **__: Any) -> Any:
    """
    Create a new agent team.

    Returns:
        Any
    """
    raise _disabled_error()
