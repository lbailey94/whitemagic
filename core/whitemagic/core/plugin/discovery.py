"""Plugin discovery — finds plugins in known directories.

Phase 8 WI 6 of the Codebase Hardening Strategy.

Scans configured directories for Python modules that look like plugins
(containing a create_plugin() function or PLUGIN attribute).

Usage::

    from whitemagic.core.plugin.discovery import PluginDiscovery

    discovery = PluginDiscovery()
    paths = discovery.scan(["/path/to/plugins"])
    for path in paths:
        print(f"Found plugin: {path}")
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from whitemagic.core.plugin.registry import PluginInfo, PluginState, get_registry

logger = logging.getLogger(__name__)

# Default plugin search directories
_DEFAULT_DIRS = [
    "plugins",
    "~/.whitemagic/plugins",
]

# Plugin entry point markers
_PLUGIN_MARKERS = ("create_plugin", "PLUGIN", "get_manifest")


class PluginDiscovery:
    """Discovers plugins by scanning directories for Python modules.

    A module is considered a plugin candidate if it contains any of:
    - `create_plugin` callable
    - `PLUGIN` attribute
    - `get_manifest` callable
    """

    def __init__(self) -> None:
        self._discovered: list[str] = []

    @property
    def discovered_modules(self) -> list[str]:
        return list(self._discovered)

    def scan(self, dirs: list[str] | None = None) -> list[str]:
        """Scan directories for plugin modules.

        Args:
            dirs: List of directories to scan. Defaults to known locations.

        Returns:
            List of module paths that look like plugins.
        """
        search_dirs = dirs or self._default_dirs()
        results: list[str] = []

        for d in search_dirs:
            dir_path = Path(d).expanduser()
            if not dir_path.exists() or not dir_path.is_dir():
                continue

            for py_file in dir_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                if self._looks_like_plugin(py_file):
                    module_path = self._path_to_module(py_file, dir_path)
                    results.append(module_path)
                    self._discovered.append(module_path)
                    logger.debug("Discovered plugin candidate: %s", module_path)

        return results

    def register_discovered(self, module_paths: list[str] | None = None) -> list[PluginInfo]:
        """Register discovered plugins in the registry (metadata only).

        Args:
            module_paths: Specific modules to register. Defaults to all discovered.

        Returns:
            List of PluginInfo entries created.
        """
        paths = module_paths or self._discovered
        infos: list[PluginInfo] = []

        for path in paths:
            info = PluginInfo(
                name=path,
                version="unknown",
                state=PluginState.DISCOVERED,
            )
            get_registry().register(info)
            infos.append(info)

        return infos

    def _default_dirs(self) -> list[str]:
        """Return default plugin search directories."""
        dirs = []
        for d in _DEFAULT_DIRS:
            p = Path(d).expanduser()
            if p.is_absolute():
                dirs.append(str(p))
            else:
                # Relative to state root or CWD
                state_root = os.environ.get("WM_STATE_ROOT", "")
                if state_root:
                    dirs.append(str(Path(state_root) / d))
                dirs.append(str(p))
        return dirs

    def _looks_like_plugin(self, py_file: Path) -> bool:
        """Check if a Python file looks like a plugin module."""
        try:
            content = py_file.read_text(errors="replace")
            return any(marker in content for marker in _PLUGIN_MARKERS)
        except OSError:
            return False

    def _path_to_module(self, py_file: Path, base_dir: Path) -> str:
        """Convert a file path to a dotted module path."""
        rel = py_file.relative_to(base_dir) if py_file.is_relative_to(base_dir) else py_file
        parts = list(rel.with_suffix("").parts)
        return ".".join(parts)

    def clear(self) -> None:
        """Clear discovered modules (for testing)."""
        self._discovered.clear()
