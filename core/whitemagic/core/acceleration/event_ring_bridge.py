"""Event Ring Bridge — in-memory event ring for tool telemetry.

Lightweight implementation that buffers events for downstream consumers.
Not persisted; events are held in memory until consumed or dropped.
"""

from __future__ import annotations

from typing import Any


class EventRingBridge:
    """In-memory event ring for telemetry and tracing."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._max_size = 1000

    def push(self, event: dict[str, Any]) -> None:
        """Push an event to the ring."""
        self._events.append(event)
        if len(self._events) > self._max_size:
            self._events.pop(0)

    def pop(self) -> dict[str, Any] | None:
        """Pop the oldest event from the ring."""
        if self._events:
            return self._events.pop(0)
        return None

    def publish(
        self,
        event_type: str,
        source: str,
        confidence: float,
        data: bytes = b"",
    ) -> None:
        """Publish a typed event to the ring."""
        self.push({
            "event_type": event_type,
            "source": source,
            "confidence": confidence,
            "data": data,
        })

    def flush(self) -> list[dict[str, Any]]:
        """Return and clear all buffered events."""
        events = self._events.copy()
        self._events.clear()
        return events


_bridge: EventRingBridge | None = None


def get_event_ring() -> EventRingBridge:
    """Get or create the global event ring bridge."""
    global _bridge
    if _bridge is None:
        _bridge = EventRingBridge()
    return _bridge
