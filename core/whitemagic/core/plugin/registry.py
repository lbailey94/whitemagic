"""Plugin registry — tracks installed and active plugins.

Phase 8 WI 6 of the Codebase Hardening Strategy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from whitemagic.core.plugin.base import Plugin, PluginManifest

logger = logging.getLogger(__name__)


class PluginState(StrEnum):
    """Lifecycle state of a plugin."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class PluginInfo:
    """Information about a registered plugin."""

    name: str
    version: str
    author: str = "Unknown"
    description: str = ""
    license: str = "MIT"
    state: PluginState = PluginState.DISCOVERED
    extension_points: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    instance: Plugin | None = None

    @classmethod
    def from_manifest(cls, manifest: PluginManifest, state: PluginState = PluginState.DISCOVERED) -> PluginInfo:
        return cls(
            name=manifest.name,
            version=manifest.version,
            author=manifest.author,
            description=manifest.description,
            license=manifest.license,
            state=state,
            extension_points=list(manifest.extension_points),
            requires=list(manifest.requires),
            config=dict(manifest.config),
        )


class PluginRegistry:
    """Registry of all known plugins and their states.

    Tracks the full lifecycle: discovered → loaded → active → inactive.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}

    def register(self, info: PluginInfo) -> None:
        """Register a plugin info entry."""
        self._plugins[info.name] = info
        logger.debug("Registered plugin: %s v%s", info.name, info.version)

    def unregister(self, name: str) -> bool:
        """Remove a plugin from the registry. Returns True if it existed."""
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def get(self, name: str) -> PluginInfo | None:
        """Get plugin info by name."""
        return self._plugins.get(name)

    def all(self) -> list[PluginInfo]:
        """Return all registered plugins."""
        return list(self._plugins.values())

    def active(self) -> list[PluginInfo]:
        """Return only active plugins."""
        return [p for p in self._plugins.values() if p.state == PluginState.ACTIVE]

    def by_state(self, state: PluginState) -> list[PluginInfo]:
        """Return plugins in a given state."""
        return [p for p in self._plugins.values() if p.state == state]

    def set_state(self, name: str, state: PluginState, error: str = "") -> bool:
        """Update a plugin's state. Returns True if the plugin exists."""
        info = self._plugins.get(name)
        if info is None:
            return False
        info.state = state
        if error:
            info.error = error
        return True

    def set_instance(self, name: str, plugin: Plugin) -> bool:
        """Attach a plugin instance to its registry entry."""
        info = self._plugins.get(name)
        if info is None:
            return False
        info.instance = plugin
        return True

    def clear(self) -> None:
        """Remove all plugins (for testing)."""
        self._plugins.clear()


# Singleton
_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Get the global PluginRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None
