"""Humor Garden — The Medicine of Laughter.

Mansion: #9 Willow (柳 Liu)
Quadrant: Southern (Vermilion Bird)
PRAT Gana: gana_willow — resilience, play, adaptive recovery

The Willow Gana bends without breaking. The Humor Garden provides the
substrate for joy, wit, and the perspective shift that turns obstacles
into punchlines.
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


class HumorGarden(BaseGarden, GanYingMixin):
    """Garden of Humor — Laughter and perspective engine."""

    name = "humor"
    category = "resilience"
    resonance_partners = ["joy", "play", "courage"]
    mansion_number = 9
    gana_name = "gana_willow"

    def __init__(self) -> None:
        BaseGarden.__init__(self)
        self._lock = threading.Lock()
        self.joy_index: float = 0.5
        init_listeners(self)
        self.emit(EventType.SYSTEM_STARTED, {"garden": "Humor", "mansion": 9})

    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "humor"

    def get_coordinate_bias(self) -> CoordinateBias:
        """
        Get the coordinate bias.
        
        Returns:
            CoordinateBias
        """
        return CoordinateBias(x=0.8, y=0.4, z=0.2, w=0.1)

    def laugh(self, context: str = "general") -> dict[str, Any]:
        """Record a moment of laughter or perspective shift."""
        moment = {
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self.joy_index = min(1.0, self.joy_index + 0.05)
        self.emit(EventType.GARDEN_ACTIVITY, {"action": "laugh", "garden": "humor"})
        return moment

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
            "joy_index": round(self.joy_index, 3),
        })
        return base

    @listen_for(EventType.JOY_EXPERIENCED)
    def on_joy(self, event: Any) -> None:
        """
        Handle a joy event.
        
        Args:
            event: Parameter description.
        
        Returns:
            None
        """
        with self._lock:
            self.joy_index = min(1.0, self.joy_index + 0.1)


_instance = None
def get_humor_garden() -> HumorGarden:
    """
    Get the humor garden.
    
    Returns:
        HumorGarden
    """
    global _instance
    if _instance is None:
        _instance = HumorGarden()
    return _instance
