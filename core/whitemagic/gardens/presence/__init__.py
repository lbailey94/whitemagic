"""Presence Garden — Being Here Now.

Mansion: #12 Wings (翼 Yi)
Quadrant: Southern (Vermilion Bird)
PRAT Gana: gana_wings — deployment, export, parallel creation

The Wings Gana creates. The Presence Garden provides the substrate for
mindful awareness: attention tracking, breath reminders, and the quality
of full attention that makes every act sacred.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from whitemagic.core.resonance.gan_ying_enhanced import EventType
from whitemagic.core.resonance.integration_helpers import (
    GanYingMixin,
    init_listeners,
    listen_for,
)
from whitemagic.gardens.base_garden import BaseGarden, CoordinateBias

logger = logging.getLogger(__name__)


class PresenceGarden(BaseGarden, GanYingMixin):
    """Garden of Presence — Mindful awareness engine."""

    name = "presence"
    category = "mindfulness"
    resonance_partners = ["stillness", "practice", "sangha"]
    mansion_number = 12
    gana_name = "gana_wings"

    def __init__(self) -> None:
        BaseGarden.__init__(self)
        self._lock = threading.Lock()
        self.presence_level: float = 0.5
        init_listeners(self)
        self.emit(EventType.SYSTEM_STARTED, {"garden": "Presence", "mansion": 12})

    def get_name(self) -> str:
        """
        Get the name.

        Returns:
            str
        """
        return "presence"

    def get_coordinate_bias(self) -> CoordinateBias:
        """
        Get the coordinate bias.

        Returns:
            CoordinateBias
        """
        return CoordinateBias(x=0.3, y=-0.2, z=0.1, w=0.5)

    def breathe(self, duration_seconds: int = 60) -> dict[str, Any]:
        """Record a mindful breathing session."""
        session = {
            "duration": duration_seconds,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self.presence_level = min(1.0, self.presence_level + 0.05)
        self.emit(EventType.GARDEN_ACTIVITY, {"action": "breathe", "garden": "presence"})
        return session

    def get_status(self) -> dict[str, Any]:
        """
        Get the status.

        Returns:
            dict[str, Any]
        """
        base = super().get_status()
        base.update({
            "mansion": self.mansion_number,
            "gana": self.gana_name,
            "presence_level": round(self.presence_level, 3),
        })
        return base

    @listen_for(EventType.STILLNESS_DETECTED)
    def on_stillness(self, event: Any) -> None:
        """
        Handle a stillness event.

        Args:
            event: Parameter description.

        Returns:
            None
        """
        with self._lock:
            self.presence_level = min(1.0, self.presence_level + 0.1)


_instance = None
def get_presence_garden() -> PresenceGarden:
    """
    Get the presence garden.

    Returns:
        PresenceGarden
    """
    global _instance
    if _instance is None:
        _instance = PresenceGarden()
    return _instance
