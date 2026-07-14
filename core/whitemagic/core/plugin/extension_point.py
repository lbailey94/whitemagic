"""Versioned extension points for plugin boundaries.

Phase 8 WI 6 of the Codebase Hardening Strategy.

Defines versioned extension points that plugins can register into:
- tools: Add new MCP tools
- handlers: Add or override tool handlers
- retrieval_stages: Add pipeline stages to memory retrieval
- governance_policies: Add Dharma governance rules
- native_accelerators: Register native bridge accelerators

Each extension point has a semantic version. Plugins declare which
extension points they use and the minimum version they require.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Known extension point categories
EP_TOOLS = "tools"
EP_HANDLERS = "handlers"
EP_RETRIEVAL_STAGES = "retrieval_stages"
EP_GOVERNANCE_POLICIES = "governance_policies"
EP_NATIVE_ACCELERATORS = "native_accelerators"

KNOWN_EXTENSION_POINTS = {
    EP_TOOLS,
    EP_HANDLERS,
    EP_RETRIEVAL_STAGES,
    EP_GOVERNANCE_POLICIES,
    EP_NATIVE_ACCELERATORS,
}


@dataclass
class ExtensionPoint:
    """A versioned extension point that plugins can register into.

    Attributes:
        name: The extension point name (e.g. "tools", "handlers").
        version: Semantic version string (e.g. "1.0.0").
        description: Human-readable description.
        required: If True, the plugin system cannot start without this EP.
    """

    name: str
    version: str = "1.0.0"
    description: str = ""
    required: bool = False
    _registrations: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def register(self, plugin_name: str, callback: Callable[..., Any], **metadata: Any) -> None:
        """Register a callback into this extension point."""
        self._registrations.append({
            "plugin": plugin_name,
            "callback": callback,
            "metadata": metadata,
        })
        logger.debug("Registered %s into extension point '%s'", plugin_name, self.name)

    def unregister(self, plugin_name: str) -> int:
        """Remove all registrations from a given plugin. Returns count removed."""
        before = len(self._registrations)
        self._registrations = [r for r in self._registrations if r["plugin"] != plugin_name]
        removed = before - len(self._registrations)
        if removed:
            logger.debug("Removed %d registrations from '%s' for plugin '%s'", removed, self.name, plugin_name)
        return removed

    def get_registrations(self) -> list[dict[str, Any]]:
        """Return all registrations for this extension point."""
        return list(self._registrations)

    def get_callbacks(self) -> list[Callable[..., Any]]:
        """Return just the callback functions."""
        return [r["callback"] for r in self._registrations]

    def clear(self) -> None:
        """Remove all registrations."""
        self._registrations.clear()


# Global registry of extension points
_extension_points: dict[str, ExtensionPoint] = {}


def get_extension_point(name: str) -> ExtensionPoint:
    """Get or create an extension point by name."""
    if name not in _extension_points:
        _extension_points[name] = ExtensionPoint(name=name)
    return _extension_points[name]


def list_extension_points() -> dict[str, ExtensionPoint]:
    """Return all registered extension points."""
    return dict(_extension_points)


def clear_extension_points() -> None:
    """Clear all extension points (for testing)."""
    for ep in _extension_points.values():
        ep.clear()
    _extension_points.clear()


# Initialize known extension points with default versions
def _init_known_points() -> None:
    defaults = {
        EP_TOOLS: ("1.0.0", "Register new MCP tools"),
        EP_HANDLERS: ("1.0.0", "Register or override tool handlers"),
        EP_RETRIEVAL_STAGES: ("1.0.0", "Add stages to the memory retrieval pipeline"),
        EP_GOVERNANCE_POLICIES: ("1.0.0", "Register Dharma governance policy rules"),
        EP_NATIVE_ACCELERATORS: ("1.0.0", "Register native bridge accelerators"),
    }
    for name, (version, desc) in defaults.items():
        if name not in _extension_points:
            _extension_points[name] = ExtensionPoint(
                name=name, version=version, description=desc,
            )


_init_known_points()
