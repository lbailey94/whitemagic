# ruff: noqa: BLE001
"""Paradox Holder — Hold paradoxes without resolving them."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ParadoxHolder:
    """Holds paradoxes without forcing resolution."""

    def __init__(self) -> None:
        self._paradoxes: list[dict[str, Any]] = []

    def hold(self, thesis: str, antithesis: str) -> dict[str, Any]:
        """Hold a paradox."""
        entry = {
            "thesis": thesis,
            "antithesis": antithesis,
            "resolved": False,
            "resolution": None,
        }
        self._paradoxes.append(entry)
        return entry

    def resolve(self, idx: int, synthesis: str) -> bool:
        """Resolve a paradox with a synthesis."""
        if 0 <= idx < len(self._paradoxes):
            self._paradoxes[idx]["resolved"] = True
            self._paradoxes[idx]["resolution"] = synthesis
            return True
        return False

    def active_paradoxes(self) -> list[dict[str, Any]]:
        """Get unresolved paradoxes."""
        return [p for p in self._paradoxes if not p["resolved"]]

    def summary(self) -> dict[str, Any]:
        return {
            "total_paradoxes": len(self._paradoxes),
            "active": len(self.active_paradoxes()),
            "resolved": sum(1 for p in self._paradoxes if p["resolved"]),
        }
