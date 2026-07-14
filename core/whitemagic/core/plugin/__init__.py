"""WhiteMagic Plugin System — Versioned extension points.

Phase 8 WI 6 of the Codebase Hardening Strategy.

Enables third-party extensions without modifying core. Provides:
- Plugin base class and manifest
- Versioned extension points (tools, handlers, retrieval, governance, accelerators)
- Plugin registry with lifecycle states
- Plugin loader (factory function or module attribute)
- Plugin discovery (directory scanning)
"""

from .base import Plugin, PluginManifest
from .discovery import PluginDiscovery
from .extension_point import (
    EP_GOVERNANCE_POLICIES,
    EP_HANDLERS,
    EP_NATIVE_ACCELERATORS,
    EP_RETRIEVAL_STAGES,
    EP_TOOLS,
    ExtensionPoint,
    clear_extension_points,
    get_extension_point,
    list_extension_points,
)
from .loader import PluginLoader
from .registry import (
    PluginInfo,
    PluginRegistry,
    PluginState,
    get_registry,
    reset_registry,
)

__all__ = [
    "Plugin",
    "PluginManifest",
    "ExtensionPoint",
    "PluginRegistry",
    "PluginInfo",
    "PluginState",
    "PluginLoader",
    "PluginDiscovery",
    "get_registry",
    "reset_registry",
    "get_extension_point",
    "list_extension_points",
    "clear_extension_points",
    "EP_TOOLS",
    "EP_HANDLERS",
    "EP_RETRIEVAL_STAGES",
    "EP_GOVERNANCE_POLICIES",
    "EP_NATIVE_ACCELERATORS",
]
