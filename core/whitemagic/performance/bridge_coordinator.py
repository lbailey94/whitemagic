# ruff: noqa: BLE001
"""Bridge Coordinator — Coordinate Rust/Haskell bridges."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BridgeCoordinator:
    """Coordinate between Python, Rust, and Haskell implementations."""

    def __init__(self) -> None:
        self.bridges: dict[str, dict[str, Any]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.bridges = {
            "rust_embeddings": {"available": False, "module": None},
            "rust_simd": {"available": False, "module": None},
            "haskell_types": {"available": False, "module": None},
        }
        self._check_availability()

    def _check_availability(self) -> None:
        """Check which bridges are available."""
        for name in self.bridges:
            module_name = f"whitemagic_{name.split('_')[0]}"
            try:
                import importlib

                mod = importlib.import_module(module_name)
                self.bridges[name]["available"] = True
                self.bridges[name]["module"] = mod
            except ImportError:
                logger.debug("Optional dependency unavailable: ImportError")

    def get_bridge(self, name: str) -> Any | None:
        """Get a bridge module by name."""
        bridge = self.bridges.get(name)
        return bridge["module"] if bridge and bridge["available"] else None

    def status(self) -> dict[str, bool]:
        """Get availability status of all bridges."""
        return {name: info["available"] for name, info in self.bridges.items()}

    def summary(self) -> dict[str, Any]:
        return {
            "total_bridges": len(self.bridges),
            "available": sum(1 for b in self.bridges.values() if b["available"]),
            "bridges": self.status(),
        }


_coordinator: BridgeCoordinator | None = None


def get_bridge_coordinator() -> BridgeCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = BridgeCoordinator()
    return _coordinator
