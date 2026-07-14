"""Plugin loader — loads plugins from Python modules.

Phase 8 WI 6 of the Codebase Hardening Strategy.

Discovers plugins by importing modules and looking for a `create_plugin()`
factory function or a `PLUGIN` module-level attribute.

Usage::

    from whitemagic.core.plugin.loader import PluginLoader

    loader = PluginLoader()
    plugin = loader.load("my_plugin_module")
    if plugin:
        plugin.activate()
"""
from __future__ import annotations

import importlib
import logging

from whitemagic.core.plugin.base import Plugin, PluginManifest
from whitemagic.core.plugin.registry import PluginInfo, PluginState, get_registry

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads plugins from Python modules.

    A plugin module must expose either:
    - A `create_plugin() -> Plugin` factory function
    - A `PLUGIN: Plugin` module-level attribute
    - A `get_manifest() -> PluginManifest` function (for metadata-only registration)
    """

    def load(self, module_path: str) -> Plugin | None:
        """Load a plugin from a Python module path.

        Args:
            module_path: Dotted module path (e.g. "my_package.my_plugin").

        Returns:
            The loaded Plugin instance, or None on failure.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.warning("Failed to import plugin module '%s': %s", module_path, e)
            return None

        # Try create_plugin() factory
        factory = getattr(module, "create_plugin", None)
        if callable(factory):
            try:
                plugin = factory()
                if isinstance(plugin, Plugin):
                    self._register_plugin(plugin, module_path)
                    return plugin
            except Exception as e:
                logger.warning("create_plugin() failed for '%s': %s", module_path, e)
                self._register_error(module_path, str(e))
                return None

        # Try PLUGIN attribute
        plugin_attr = getattr(module, "PLUGIN", None)
        if isinstance(plugin_attr, Plugin):
            self._register_plugin(plugin_attr, module_path)
            return plugin_attr

        logger.debug("Module '%s' has no plugin entry point", module_path)
        return None

    def load_manifest(self, module_path: str) -> PluginManifest | None:
        """Load only the manifest from a plugin module (no instantiation)."""
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            return None

        getter = getattr(module, "get_manifest", None)
        if callable(getter):
            try:
                return getter()
            except Exception as e:
                logger.warning("get_manifest() failed for '%s': %s", module_path, e)

        return None

    def activate(self, plugin: Plugin) -> bool:
        """Activate a loaded plugin. Returns True on success."""
        try:
            plugin.activate()
            registry = get_registry()
            registry.set_state(plugin.manifest.name, PluginState.ACTIVE)
            registry.set_instance(plugin.manifest.name, plugin)
            logger.info("Activated plugin: %s", plugin.manifest.name)
            return True
        except Exception as e:
            logger.warning("Failed to activate plugin '%s': %s", plugin.manifest.name, e)
            get_registry().set_state(plugin.manifest.name, PluginState.ERROR, str(e))
            return False

    def deactivate(self, plugin: Plugin) -> bool:
        """Deactivate a plugin. Returns True on success."""
        try:
            plugin.deactivate()
            get_registry().set_state(plugin.manifest.name, PluginState.INACTIVE)
            logger.info("Deactivated plugin: %s", plugin.manifest.name)
            return True
        except Exception as e:
            logger.warning("Failed to deactivate plugin '%s': %s", plugin.manifest.name, e)
            return False

    def _register_plugin(self, plugin: Plugin, module_path: str) -> None:
        """Register a loaded plugin in the global registry."""
        info = PluginInfo.from_manifest(plugin.manifest, PluginState.LOADED)
        info.instance = plugin
        get_registry().register(info)

    def _register_error(self, module_path: str, error: str) -> None:
        """Register a failed plugin load."""
        info = PluginInfo(
            name=module_path,
            version="unknown",
            state=PluginState.ERROR,
            error=error,
        )
        get_registry().register(info)
