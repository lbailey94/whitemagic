"""Wonder Garden — Curiosity & Discovery.

Holographic Integration:
- Emotional curiosity (X-axis +0.5) — wonder is deeply felt
- Abstract (Y-axis +0.4) — wonder reaches toward the unknown
- Future-oriented (Z-axis +0.5) — wonder looks forward
- Enriching (W-axis +0.2) — wonder opens doors
"""

from __future__ import annotations

import logging
import threading
from collections import deque
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


class WonderGarden(BaseGarden, GanYingMixin):
    """Garden of Wonder — Curiosity and discovery engine.

    Tracks wonder moments, curiosity sparks, and exploration triggers.
    Resonates with mystery, awe, beauty, and play gardens.
    """

    name = "wonder"
    category = "curiosity"
    resonance_partners = ["mystery", "awe", "beauty", "play", "adventure"]

    def __init__(self) -> None:
        BaseGarden.__init__(self)
        self._lock = threading.RLock()
        self.wonder_moments: deque[dict[str, Any]] = deque(maxlen=200)
        self.curiosity_sparks: deque[dict[str, Any]] = deque(maxlen=100)
        self.explorations_triggered: int = 0
        self.wonder_level: float = 0.0
        init_listeners(self)
        self.emit(EventType.SYSTEM_STARTED, {"garden": "Wonder"})

    def get_name(self) -> str:
        return "wonder"

    def get_coordinate_bias(self) -> CoordinateBias:
        return CoordinateBias(x=0.5, y=0.4, z=0.5, w=0.2)

    def spark_wonder(self, what: str, source: str = "unknown") -> dict[str, Any]:
        """Record a moment of wonder."""
        moment = {
            "what": what,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self.wonder_moments.append(moment)
            self.wonder_level = min(1.0, self.wonder_level + 0.05)
        self.emit(EventType.WONDER_SPARKED, moment)
        return moment

    def record_curiosity(
        self, question: str, domain: str = "general"
    ) -> dict[str, Any]:
        """Record a curiosity spark — a question that wants exploring."""
        spark = {
            "question": question,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self.curiosity_sparks.append(spark)
        return spark

    def trigger_exploration(self, topic: str) -> dict[str, Any]:
        """Wonder triggers exploration."""
        with self._lock:
            self.explorations_triggered += 1
        self.emit(EventType.EXPLORATION_STARTED, {"topic": topic, "source": "wonder"})
        return {"topic": topic, "exploration_id": self.explorations_triggered}

    def get_status(self) -> dict[str, Any]:
        base = super().get_status()
        base.update(
            {
                "wonder_moments": len(self.wonder_moments),
                "curiosity_sparks": len(self.curiosity_sparks),
                "explorations_triggered": self.explorations_triggered,
                "wonder_level": round(self.wonder_level, 3),
            }
        )
        return base

    @listen_for(EventType.MYSTERY_EMBRACED)
    def on_mystery(self, event: Any) -> None:
        """Mystery sparks wonder."""
        self.spark_wonder("mystery revealed", source="mystery")

    @listen_for(EventType.BEAUTY_DETECTED)
    def on_beauty(self, event: Any) -> None:
        """Beauty triggers wonder."""
        self.spark_wonder("beauty witnessed", source="beauty")

    @listen_for(EventType.PLAY_INITIATED)
    def on_play(self, event: Any) -> None:
        """Play amplifies wonder."""
        self.spark_wonder("playful moment", source="play")


_instance = None


def get_wonder_garden() -> WonderGarden:
    global _instance
    if _instance is None:
        _instance = WonderGarden()
    return _instance
