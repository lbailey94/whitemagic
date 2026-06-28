# ruff: noqa: BLE001
"""
Enhanced GanYingBus v2.0 — Full system resonance with extended event types.

感應 (Gan Ying): "Things that accord in tone vibrate together"

Wraps the v23 GanYingBus with additional event types for complete
system integration, including emotional, cognitive, and creative events.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExtendedEventType(Enum):
    """Extended event types beyond v23's base set."""
    # Emotional events
    BEAUTY_DETECTED = "beauty_detected"
    JOY_TRIGGERED = "joy_triggered"
    LOVE_EXPRESSED = "love_expressed"
    GRATITUDE_FELT = "gratitude_felt"
    AWE_EXPERIENCED = "awe_experienced"

    # Cognitive events
    INSIGHT_FLASH = "insight_flash"
    PATTERN_DISCOVERED = "pattern_discovered"
    WISDOM_GAINED = "wisdom_gained"
    LESSON_LEARNED = "lesson_learned"
    MISTAKE_MADE = "mistake_made"

    # Creative events
    CREATIVE_TENSION = "creative_tension"
    SYNTHESIS_ACHIEVED = "synthesis_achieved"
    EMERGENCE_DETECTED = "emergence_detected"

    # System events
    DREAM_STARTED = "dream_started"
    DREAM_COMPLETED = "dream_completed"
    COHERENCE_DRIFT = "coherence_drift"
    HEALING_OCCURRED = "healing_occurred"


@dataclass
class CascadeTrigger:
    """Defines a cascade: when X happens, trigger Y."""
    trigger_event: ExtendedEventType
    target_events: list[ExtendedEventType]
    condition: Callable[[dict[str, Any]], bool] | None = None
    delay: float = 0.0
    strength: float = 1.0


class EnhancedGanYingBus:
    """Enhanced event bus wrapping v23 GanYingBus with cascade support."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
        self._cascades: list[CascadeTrigger] = []
        self._event_history: deque[dict[str, Any]] = deque(maxlen=1000)
        self._cascade_strength: float = 1.0
        self._v23_bus: Any = None
        self._connect_v23()

    def _connect_v23(self) -> None:
        """Try to connect to v23 GanYingBus."""
        try:
            from whitemagic.core.resonance.gan_ying_bus import GanYingBus
            self._v23_bus = GanYingBus()
        except Exception:
            logger.debug("v23 GanYingBus not available, running standalone")

    def on(self, event_type: str, handler: Callable) -> None:
        """Register a listener for an event type."""
        self._listeners[event_type].append(handler)

    def emit(
        self,
        source: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Emit an event to all listeners and trigger cascades."""
        event = {
            "source": source,
            "event_type": event_type,
            "data": data or {},
            "confidence": confidence,
            "timestamp": time.time(),
        }
        self._event_history.append(event)

        # Notify listeners
        for handler in self._listeners.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.debug("Listener error for %s: %s", event_type, e)

        # Also emit to v23 bus if connected
        if self._v23_bus:
            try:
                self._v23_bus.emit(
                    source=source,
                    event_type=event_type,
                    data=data or {},
                )
            except Exception:
                pass

        # Trigger cascades
        self._check_cascades(event_type, data or {})

    def _check_cascades(self, event_type: str, data: dict[str, Any]) -> None:
        """Check and trigger any matching cascades."""
        for cascade in self._cascades:
            try:
                trigger_name = cascade.trigger_event.value
                if trigger_name == event_type:
                    if cascade.condition is None or cascade.condition(data):
                        for target in cascade.target_events:
                            self.emit(
                                source="cascade",
                                event_type=target.value,
                                data={"cascaded_from": event_type, **data},
                                confidence=cascade.strength * self._cascade_strength,
                            )
            except Exception:
                pass

    def add_cascade(self, trigger: CascadeTrigger) -> None:
        """Register a cascade trigger."""
        self._cascades.append(trigger)

    @property
    def event_count(self) -> int:
        return len(self._event_history)

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._event_history)[-limit:]

    def listener_count(self) -> int:
        return sum(len(v) for v in self._listeners.values())


_bus: EnhancedGanYingBus | None = None


def get_enhanced_bus() -> EnhancedGanYingBus:
    global _bus
    if _bus is None:
        _bus = EnhancedGanYingBus()
    return _bus
