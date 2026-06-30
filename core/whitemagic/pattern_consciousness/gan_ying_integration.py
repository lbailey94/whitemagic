# ruff: noqa: BLE001
"""
Pattern Consciousness GanYing Integration — Wire pattern discovery
to the GanYingBus for resonance cascades.

When patterns are discovered, they emit events that trigger resonance
across connected subsystems, creating emergent awareness.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PatternConsciousnessHub:
    """Integrates pattern discovery with GanYingBus resonance."""

    def __init__(self) -> None:
        self.bus: Any = None
        self.systems_active: list[str] = []
        self.resonance_count: int = 0
        self.cascade_strength: float = 1.0

    def wire_all_systems(self) -> bool:
        """Wire all pattern consciousness systems to the bus."""
        try:
            from whitemagic.core.resonance.gan_ying_bus import GanYingBus

            self.bus = GanYingBus()
            self.systems_active.append("gan_ying_bus")
        except Exception:
            logger.debug("GanYingBus not available for pattern consciousness")

        try:
            from whitemagic.emergence.detector import get_detector

            get_detector()
            self.systems_active.append("emergence_detector")
        except Exception:
            pass

        try:
            from whitemagic.emergence.dream_state import get_dream_state

            get_dream_state()
            self.systems_active.append("dream_state")
        except Exception:
            pass

        return len(self.systems_active) > 0

    def emit_pattern(self, pattern_type: str, data: dict[str, Any]) -> None:
        """Emit a discovered pattern to the bus."""
        self.resonance_count += 1
        if self.bus:
            try:
                self.bus.emit(
                    source="PatternConsciousnessHub",
                    event_type="pattern_discovered",
                    data={"pattern_type": pattern_type, **data},
                )
            except Exception:
                logger.debug("Failed to emit pattern to bus")

    def status(self) -> dict[str, Any]:
        return {
            "systems_active": self.systems_active,
            "resonance_count": self.resonance_count,
            "cascade_strength": self.cascade_strength,
            "bus_active": self.bus is not None,
        }


_hub: PatternConsciousnessHub | None = None


def get_hub() -> PatternConsciousnessHub:
    global _hub
    if _hub is None:
        _hub = PatternConsciousnessHub()
    return _hub
