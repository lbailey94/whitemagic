# ruff: noqa: BLE001
"""
Terminal Multiplexer — Multiple named scratchpads.

Inspired by tmux/screen but for thought streams:
- Multiple parallel scratchpads
- Switch between different problem contexts
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TerminalMultiplexer:
    """Manages multiple named scratchpad channels."""

    def __init__(self) -> None:
        self._channels: dict[str, list[str]] = {}
        self._active: str = "default"
        self._channels["default"] = []

    def create_channel(self, name: str) -> bool:
        """Create a new channel."""
        if name in self._channels:
            return False
        self._channels[name] = []
        return True

    def switch(self, name: str) -> bool:
        """Switch to a channel."""
        if name not in self._channels:
            return False
        self._active = name
        return True

    def write(self, content: str) -> None:
        """Write to the active channel."""
        self._channels.setdefault(self._active, []).append(content)

    def read(self, channel: str | None = None) -> list[str]:
        """Read from a channel (active if not specified)."""
        ch = channel or self._active
        return self._channels.get(ch, [])

    def list_channels(self) -> list[str]:
        """List all channels."""
        return list(self._channels.keys())

    @property
    def active_channel(self) -> str:
        return self._active

    def close_channel(self, name: str) -> bool:
        """Close a channel."""
        if name == "default" or name not in self._channels:
            return False
        del self._channels[name]
        if self._active == name:
            self._active = "default"
        return True

    def summary(self) -> dict[str, Any]:
        return {
            "channels": len(self._channels),
            "active": self._active,
            "channel_names": list(self._channels.keys()),
        }
