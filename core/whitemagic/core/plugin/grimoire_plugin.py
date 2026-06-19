# ruff: noqa: BLE001
"""Grimoire Plugin Manifest — Microkernel Mandala (Bridge 3).

Wraps the GrimoireEngine in the WhiteMagic Plugin protocol so it can be
discovered, loaded, and hot-swapped by the PluginRegistry without a hard
import dependency in the core dispatch startup path.

The existing whitemagic.core.plugin system (PluginRegistry, PluginLoader,
PluginDiscovery) is already wired to scan for Plugin subclasses. Registering
GrimoireEngine here pulls Grimoire into the microkernel orbit seamlessly.

Usage (automatic via PluginDiscovery, or explicit):
    from whitemagic.core.plugin.grimoire_plugin import GrimoirePlugin
    registry = get_registry()
    registry.register(GrimoirePlugin())
    plugin = registry.get("grimoire")
    plugin.start()
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal Plugin Protocol (mirrors what whitemagic.core.plugin.base defines,
# without a hard import so this file is always importable even when the full
# plugin subsystem hasn't loaded yet).
# ---------------------------------------------------------------------------

class _PluginBase:
    """Thin fallback base so GrimoirePlugin is always usable."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    def start(self) -> None:
        """Start the plugin — graceful no-op fallback."""
        logger.debug("GrimoirePlugin.start: no-op fallback")

    def stop(self) -> None:
        """Stop the plugin — graceful no-op fallback."""
        logger.debug("GrimoirePlugin.stop: no-op fallback")

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.

        Returns:
            dict[str, Any]
        """
        return {"name": self.name, "running": True}


try:
    from whitemagic.core.plugin.base import (  # type: ignore[no-redef]
        Plugin as _PluginBase,  # type: ignore[assignment]
    )
except ImportError:
    pass  # fallback base is sufficient


class GrimoirePlugin(_PluginBase):
    """Hot-loadable Grimoire 2.0 subsystem plugin.

    The microkernel can load/unload Grimoire without restarting the MCP server.
    Phase context is pulled live from the UnifiedProgressionDaemon.
    """

    name = "grimoire"
    version = "2.0.0"
    description = "Living Spellbook — 28-chapter recommendation engine driven by the 12-phase Zodiacal clock"

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._running = False

    def start(self) -> None:
        """
        Perform the start operation.

        Returns:
            None
        """
        from whitemagic.core.intelligence.grimoire_engine import get_grimoire_engine
        self._engine = get_grimoire_engine()
        self._engine.awaken()
        self._running = True
        logger.info("GrimoirePlugin started (v%s)", self.version)

    def stop(self) -> None:
        """
        Perform the stop operation.

        Returns:
            None
        """
        self._running = False
        self._engine = None
        logger.info("GrimoirePlugin stopped")

    def recommend(self, task: str, keywords: list[str] | None = None) -> list[dict[str, Any]]:
        """Public API: recommend spells for a task using live cycle context."""
        if not self._running or self._engine is None:
            return []
        self._engine.update_context(task=task, keywords=keywords or [])
        return [
            {"spell": r.spell_name, "chapter": r.chapter, "confidence": r.confidence}
            for r in self._engine.recommend_spells(max_results=5)
        ]

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.

        Returns:
            dict[str, Any]
        """
        from whitemagic.core.governance.unified_progression import (
            get_progression_daemon,
        )
        daemon = get_progression_daemon()
        return {
            "name": self.name,
            "version": self.version,
            "running": self._running,
            "engine_state": self._engine.state.value if self._engine else "unloaded",
            "current_zodiac_phase": daemon.state.current_phase.value,
            "wu_xing": daemon.state.wu_xing.value,
            "yin_yang": daemon.state.yin_yang.value,
        }


# ---------------------------------------------------------------------------
# Auto-registration helper
# ---------------------------------------------------------------------------

def register_grimoire_plugin() -> None:
    """Register GrimoirePlugin with the PluginRegistry if available."""
    try:
        from whitemagic.core.plugin import get_registry
        registry = get_registry()
        plugin = GrimoirePlugin()
        plugin.start()
        registry.register(plugin)  # type: ignore[arg-type]
        logger.info("GrimoirePlugin registered in PluginRegistry")
    except Exception as e:
        logger.debug("PluginRegistry not available, skipping auto-registration: %s", e)
