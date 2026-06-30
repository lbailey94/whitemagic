# ruff: noqa: BLE001
"""
Garden Synthesis — Cross-garden integration and harmony.

Synthesizes insights across all gardens (joy, truth, love, beauty, etc.)
into a unified wisdom stream.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GardenSynthesis:
    """Synthesizes across all gardens for unified wisdom."""

    def __init__(self) -> None:
        self.gardens: dict[str, Any] = {}
        self.syntheses: list[dict[str, Any]] = []

    def register_garden(self, name: str, garden: Any) -> None:
        """Register a garden for synthesis."""
        self.gardens[name] = garden

    def synthesize(self) -> dict[str, Any]:
        """Run cross-garden synthesis."""
        start = time.monotonic()
        garden_states: dict[str, Any] = {}

        for name, garden in self.gardens.items():
            try:
                if hasattr(garden, "summary"):
                    garden_states[name] = garden.summary()
                elif hasattr(garden, "status"):
                    garden_states[name] = garden.status()
                else:
                    garden_states[name] = {"state": "unknown"}
            except Exception as e:
                garden_states[name] = {"error": str(e)}

        # Find dominant themes
        active_gardens = [
            name
            for name, state in garden_states.items()
            if isinstance(state, dict) and "error" not in state
        ]

        synthesis = {
            "timestamp": time.time(),
            "gardens_synthesized": len(active_gardens),
            "garden_states": garden_states,
            "dominant_theme": active_gardens[0] if active_gardens else "none",
            "harmony_level": len(active_gardens) / max(len(self.gardens), 1),
            "duration_s": time.monotonic() - start,
        }
        self.syntheses.append(synthesis)
        return synthesis

    def history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.syntheses[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "registered_gardens": len(self.gardens),
            "total_syntheses": len(self.syntheses),
            "garden_names": list(self.gardens.keys()),
        }


_synthesis: GardenSynthesis | None = None


def get_synthesis() -> GardenSynthesis:
    global _synthesis
    if _synthesis is None:
        _synthesis = GardenSynthesis()
    return _synthesis
